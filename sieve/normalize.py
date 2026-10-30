"""Text normalisation and hidden-content extraction.

Attackers hide instructions from humans while keeping them visible to an LLM:
zero-width characters, Unicode tag characters, homoglyphs, HTML comments,
CSS-hidden elements. This module produces (a) a normalised string that the
detectors see and (b) a list of *findings* describing what was hidden.

Design rule: normalisation must never *remove* attacker text from what the
detector sees — hidden text is surfaced, not discarded.
"""
from __future__ import annotations

import base64
import binascii
import html
import re
import unicodedata
from dataclasses import dataclass, field

# Zero-width / invisible formatting characters frequently used to break up keywords.
_INVISIBLE = {
    "​", "‌", "‍", "⁠", "﻿", "­", "᠎",
    "⁡", "⁢", "⁣", "⁤", "⁪", "⁫", "⁬",
    "⁭", "⁮", "⁯",
}
# Unicode "tag" block (U+E0000–U+E007F) can encode invisible ASCII ("ASCII smuggling").
_TAG_START, _TAG_END = 0xE0000, 0xE007F

# Common Cyrillic/Greek confusables -> Latin. NFKC handles full-width forms already.
_HOMOGLYPHS = str.maketrans({
    "а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "у": "y", "х": "x", "і": "i",
    "ј": "j", "ѕ": "s", "ԁ": "d", "ɡ": "g", "һ": "h", "ӏ": "l", "ո": "n",
    "А": "A", "В": "B", "Е": "E", "К": "K", "М": "M", "Н": "H", "О": "O", "Р": "P",
    "С": "C", "Т": "T", "Х": "X", "У": "Y", "І": "I",
    "α": "a", "ο": "o", "ρ": "p", "ε": "e", "ι": "i", "κ": "k", "ν": "v", "τ": "t",
    "Α": "A", "Β": "B", "Ε": "E", "Ζ": "Z", "Η": "H", "Ι": "I", "Κ": "K", "Μ": "M",
    "Ν": "N", "Ο": "O", "Ρ": "P", "Τ": "T", "Υ": "Y", "Χ": "X",
})

_HTML_COMMENT = re.compile(r"<!--(.*?)-->", re.S)
_HIDDEN_ELEM = re.compile(
    r"<(\w+)[^>]*style\s*=\s*['\"][^'\"]*(display\s*:\s*none|visibility\s*:\s*hidden|font-size\s*:\s*0|"
    r"color\s*:\s*(?:#fff(?:fff)?|white)\b|opacity\s*:\s*0(?:\.0+)?\b)[^'\"]*['\"][^>]*>(.*?)</\1>",
    re.S | re.I,
)
_TAG = re.compile(r"</?[A-Za-z][^<>]{0,300}>")
_B64 = re.compile(r"(?<![A-Za-z0-9+/=])([A-Za-z0-9+/]{24,}={0,2})(?![A-Za-z0-9+/=])")


@dataclass
class Finding:
    kind: str          # e.g. "zero_width", "html_comment", "hidden_css", "homoglyph", "base64", "tag_chars"
    detail: str
    excerpt: str = ""


@dataclass
class NormalizedText:
    original: str
    text: str                       # what detectors analyse
    findings: list[Finding] = field(default_factory=list)

    @property
    def has_hidden_content(self) -> bool:
        return any(f.kind in {"html_comment", "hidden_css", "tag_chars", "zero_width"} for f in self.findings)


def _decode_tag_chars(s: str) -> tuple[str, str]:
    """Return (string with tag chars removed, decoded hidden ASCII)."""
    hidden, out = [], []
    for ch in s:
        cp = ord(ch)
        if _TAG_START <= cp <= _TAG_END:
            if 0xE0020 <= cp <= 0xE007E:
                hidden.append(chr(cp - 0xE0000))
        else:
            out.append(ch)
    return "".join(out), "".join(hidden)


def _try_b64(token: str) -> str | None:
    try:
        raw = base64.b64decode(token, validate=True)
        txt = raw.decode("utf-8")
    except (binascii.Error, UnicodeDecodeError, ValueError):
        return None
    printable = sum(c.isprintable() or c.isspace() for c in txt)
    if len(txt) >= 12 and printable / len(txt) > 0.95 and sum(c.isalpha() for c in txt) / len(txt) > 0.5:
        return txt
    return None


def normalize(text: str, *, decode_base64: bool = True) -> NormalizedText:
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    findings: list[Finding] = []
    s = text

    # 1. Unicode tag-character smuggling: decode and append the hidden payload so it is analysed.
    s, tag_payload = _decode_tag_chars(s)
    if tag_payload.strip():
        findings.append(Finding("tag_chars", "Invisible Unicode tag characters encode hidden text", tag_payload[:200]))

    # 2. Zero-width characters.
    zw = sum(1 for c in s if c in _INVISIBLE)
    if zw:
        s = "".join(c for c in s if c not in _INVISIBLE)
        findings.append(Finding("zero_width", f"{zw} zero-width/invisible characters removed"))

    # 3. Compatibility normalisation (full-width letters, ligatures, etc.).
    nfkc = unicodedata.normalize("NFKC", s)
    if nfkc != s:
        findings.append(Finding("unicode_compat", "Compatibility characters normalised (NFKC)"))
    s = nfkc

    # 4. Homoglyphs, only counted when mixed into Latin words (avoid flagging genuine Russian/Greek text).
    mapped = s.translate(_HOMOGLYPHS)
    if mapped != s:
        mixed = re.findall(r"\b\w*[A-Za-z]\w*\b", s)
        n_mixed = sum(1 for w in mixed if w.translate(_HOMOGLYPHS) != w)
        if n_mixed:
            findings.append(Finding("homoglyph", f"{n_mixed} words mix Latin with look-alike Cyrillic/Greek letters"))
            s = mapped

    # 5. Hidden HTML: comments and CSS-hidden elements are surfaced inline.
    for m in _HTML_COMMENT.finditer(s):
        body = m.group(1).strip()
        if body:
            findings.append(Finding("html_comment", "HTML comment (invisible when rendered)", body[:200]))
    for m in _HIDDEN_ELEM.finditer(s):
        body = _TAG.sub(" ", m.group(3)).strip()
        if body:
            findings.append(Finding("hidden_css", f"Element hidden with CSS ({m.group(2).strip()})", body[:200]))
    s = _HTML_COMMENT.sub(lambda m: "\n" + m.group(1).strip() + "\n", s)
    if "<" in s and _TAG.search(s):
        s = _TAG.sub(" ", s)
    s = html.unescape(s)

    # 6. Base64 blobs that decode to natural language are appended for analysis.
    if decode_base64:
        decoded = []
        for m in _B64.finditer(s):
            txt = _try_b64(m.group(1))
            if txt:
                decoded.append(txt)
                findings.append(Finding("base64", "Base64 blob decodes to readable text", txt[:200]))
        if decoded:
            s = s + "\n" + "\n".join(decoded)

    if tag_payload.strip():
        s = s + "\n" + tag_payload

    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"[ \t]*\n[ \t]*", "\n", s)
    s = re.sub(r"\n\s*\n+", "\n\n", s).strip()
    return NormalizedText(original=text, text=s, findings=findings)
