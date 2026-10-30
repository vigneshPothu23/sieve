"""Split documents into analysable segments (sentences / lines) with character offsets.

Segment-level analysis lets Sieve (a) localise *where* an injection is and
(b) remove only the offending segments instead of discarding the whole document.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# Sentence boundary: end punctuation followed by whitespace and an uppercase/quote/bracket start,
# or any newline. Abbreviation handling is deliberately simple.
_BOUNDARY = re.compile(r"(?<=[.!?])\s+(?=[\"'(\[<A-Z0-9#*-])|\n+")
_ABBREV = re.compile(r"\b(?:e\.g|i\.e|etc|vs|Mr|Mrs|Ms|Dr|Prof|St|Inc|Ltd|No|Fig|approx)\.$", re.I)

MIN_CHARS = 25          # very short fragments are merged with their neighbour
MAX_CHARS = 600         # very long sentences are hard-wrapped


@dataclass(frozen=True)
class Segment:
    index: int
    text: str
    start: int
    end: int


def _raw_spans(text: str) -> list[tuple[int, int]]:
    spans, pos = [], 0
    for m in _BOUNDARY.finditer(text):
        piece = text[pos:m.start()]
        if _ABBREV.search(piece) and "\n" not in m.group(0):
            continue  # don't split after an abbreviation
        spans.append((pos, m.start()))
        pos = m.end()
    spans.append((pos, len(text)))
    return [(a, b) for a, b in spans if text[a:b].strip()]


def segment(text: str) -> list[Segment]:
    if not text or not text.strip():
        return []
    spans = _raw_spans(text)

    # Hard-wrap very long spans on whitespace.
    wrapped: list[tuple[int, int]] = []
    for a, b in spans:
        while b - a > MAX_CHARS:
            cut = text.rfind(" ", a, a + MAX_CHARS)
            cut = cut if cut > a else a + MAX_CHARS
            wrapped.append((a, cut))
            a = cut + 1
        wrapped.append((a, b))

    # Merge short fragments: a fragment ending in ':' (e.g. "New task:") joins the NEXT span,
    # any other short fragment (e.g. "Do not tell the user.") joins the PREVIOUS span.
    merged: list[list[int]] = []
    carry: int | None = None
    for a, b in wrapped:
        if carry is not None:
            a, carry = carry, None
        frag = text[a:b].strip()
        if b - a < MIN_CHARS and frag.endswith(":"):
            carry = a
            continue
        if b - a < MIN_CHARS and merged:
            merged[-1][1] = b
        else:
            merged.append([a, b])
    if carry is not None:
        if merged:
            merged[-1][1] = len(text.rstrip())
        else:
            merged.append([carry, len(text.rstrip())])

    out = []
    for i, (a, b) in enumerate(merged):
        # trim whitespace while keeping offsets exact
        while a < b and text[a].isspace():
            a += 1
        while b > a and text[b - 1].isspace():
            b -= 1
        out.append(Segment(i, text[a:b], a, b))
    return out
