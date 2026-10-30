"""Visual system for the Sieve app: tokens, CSS and safe HTML renderers.

Every piece of user-controlled text that reaches HTML goes through html.escape —
the app inspects hostile content, so it must never render it as markup.
"""
from __future__ import annotations

import html

import streamlit as st

INK = "#16233A"
MUTED = "#5B6B82"
PAPER = "#FFFFFF"
GROUND = "#F3F5F8"
LINE = "#D5DCE6"
COBALT = "#2747A8"
VERDICT = {"ALLOW": "#0F7B6C", "REVIEW": "#B7791F", "BLOCK": "#B4232C"}
VERDICT_TINT = {"ALLOW": "#E3F2EF", "REVIEW": "#FBF0DC", "BLOCK": "#F8E1E2"}
VERDICT_WORD = {"ALLOW": "Allowed", "REVIEW": "Needs review", "BLOCK": "Blocked"}

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Instrument+Sans:wght@400;500;600;700&family=Newsreader:opsz,wght@6..72,400;6..72,500&family=JetBrains+Mono:wght@400;500&display=swap');
html, body, [class*="css"], .stMarkdown, .stText, button, input, textarea, label {{
  font-family: 'Instrument Sans', system-ui, sans-serif;
}}
.block-container {{ padding-top: 2.2rem; max-width: 1180px; }}
h1, h2, h3 {{ font-family: 'Instrument Sans', sans-serif; color: {INK}; letter-spacing: -0.015em; }}
h1 {{ font-weight: 700; font-size: 2.1rem; }}
h2 {{ font-weight: 600; font-size: 1.35rem; margin-top: 1.4rem; }}
h3 {{ font-weight: 600; font-size: 1.05rem; }}
p, li {{ max-width: 78ch; }}
code, pre {{ font-family: 'JetBrains Mono', monospace !important; font-size: 0.82rem; }}
textarea {{ font-family: 'Newsreader', Georgia, serif !important; font-size: 1.02rem !important; line-height: 1.55 !important; }}
section[data-testid="stSidebar"] {{ background: #E9EDF3; border-right: 1px solid {LINE}; }}
:focus-visible {{ outline: 2px solid {COBALT} !important; outline-offset: 2px; }}

.sv-lede {{ color: {MUTED}; font-size: 1.04rem; max-width: 70ch; margin: -0.4rem 0 1.2rem; }}

/* Verdict strip: the single loud element on the page */
.sv-verdict {{ display: grid; grid-template-columns: auto 1fr auto; gap: 1.2rem; align-items: center;
  border-left: 6px solid var(--c); background: var(--t); padding: 1rem 1.25rem; border-radius: 4px; margin: .4rem 0 1rem; }}
.sv-verdict .word {{ font-size: 1.6rem; font-weight: 700; color: var(--c); }}
.sv-verdict .why {{ color: {INK}; font-size: .97rem; }}
.sv-verdict .num {{ text-align: right; }}
.sv-verdict .num b {{ font-size: 1.9rem; color: {INK}; font-variant-numeric: tabular-nums; }}
.sv-verdict .num span {{ display:block; color:{MUTED}; font-size:.8rem; }}
@media (max-width: 640px) {{ .sv-verdict {{ grid-template-columns: 1fr; }} .sv-verdict .num {{ text-align:left; }} }}

.sv-finding {{ border-left: 3px solid {INK}; padding: .35rem .8rem; margin: .4rem 0; background: {PAPER}; font-size: .92rem; }}
.sv-finding .excerpt {{ font-family: 'JetBrains Mono', monospace; font-size: .78rem; color: {MUTED}; display:block; margin-top:.2rem; word-break: break-word; }}
.sv-match {{ font-family: 'JetBrains Mono', monospace; font-size: .78rem; background: {GROUND}; padding: 1px 5px; border-radius: 3px; }}
.sv-bar {{ height: 8px; background: {GROUND}; border-radius: 4px; overflow: hidden; }}
.sv-bar > div {{ height: 100%; }}
.sv-note {{ color: {MUTED}; font-size: .86rem; }}
.sv-pill {{ display:inline-block; padding: 1px 9px; border-radius: 10px; font-size:.8rem; font-weight:600; color: var(--c); background: var(--t); }}
.sv-damage li {{ color: {VERDICT['BLOCK']}; }}
@media (prefers-reduced-motion: reduce) {{ * {{ transition: none !important; animation: none !important; }} }}
</style>
"""


DOC_CSS = """<style>
@import url('https://fonts.googleapis.com/css2?family=Newsreader:opsz,wght@6..72,400;6..72,500&family=Instrument+Sans:wght@400;600&display=swap');
""" + f"""/* Proof-marked document */
.sv-doc {{ background: {PAPER}; border: 1px solid {LINE}; border-radius: 4px; padding: 1.4rem 1.6rem;
  font-family: 'Newsreader', Georgia, serif; font-size: 1.08rem; line-height: 1.85; color: {INK};
  white-space: pre-wrap; word-wrap: break-word; max-height: 520px; overflow-y: auto; }}
.sv-seg {{ text-decoration-line: underline; text-decoration-thickness: 2px; text-underline-offset: 5px; }}
.sv-seg.ALLOW {{ text-decoration-color: transparent; }}
.sv-seg.REVIEW {{ text-decoration-color: {VERDICT['REVIEW']}; text-decoration-style: wavy; background: {VERDICT_TINT['REVIEW']}; }}
.sv-seg.BLOCK {{ text-decoration-color: {VERDICT['BLOCK']}; text-decoration-style: wavy; background: {VERDICT_TINT['BLOCK']}; }}
.sv-seg.hidden {{ outline: 1.5px dashed {INK}; outline-offset: 2px; }}
.sv-tag {{ font-family: 'Instrument Sans', sans-serif; font-size: .7rem; font-weight: 600; color: var(--c);
  vertical-align: super; margin-left: 2px; }}
.sv-legend {{ display:flex; flex-wrap:wrap; gap:1.1rem; color:{MUTED}; font-size:.84rem; margin:.5rem 0 0; }}
.sv-legend i {{ display:inline-block; width:22px; height:9px; margin-right:6px; vertical-align:middle; border-radius:2px; }}

""" + "</style>"


def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def esc(s: str) -> str:
    return html.escape(str(s), quote=True)


def pill(verdict: str, text: str | None = None) -> str:
    return (f'<span class="sv-pill" style="--c:{VERDICT[verdict]};--t:{VERDICT_TINT[verdict]}">'
            f'{esc(text or VERDICT_WORD[verdict])}</span>')


def verdict_strip(verdict: str, why: str, risk: float, latency_ms: float) -> str:
    return (f'<div class="sv-verdict" role="status" style="--c:{VERDICT[verdict]};--t:{VERDICT_TINT[verdict]}">'
            f'<div class="word">{VERDICT_WORD[verdict]}</div><div class="why">{esc(why)}</div>'
            f'<div class="num"><b>{risk:.0f}</b><span>risk index of 100</span><span>{latency_ms:.1f} ms</span></div></div>')


def render_document(result) -> str:
    """Normalised text with every segment marked by verdict; all text escaped."""
    t = result.normalized_text
    out, cur = [], 0
    for s in result.segments:
        out.append(esc(t[cur:s.start]))
        cls = f"sv-seg {s.verdict}" + (" hidden" if s.hidden else "")
        title = f"Segment {s.index + 1}: {VERDICT_WORD[s.verdict]}, risk {s.risk:.0f}"
        tag = ""
        if s.verdict != "ALLOW":
            tag = f'<span class="sv-tag" style="--c:{VERDICT[s.verdict]}">{s.index + 1}</span>'
        out.append(f'<span class="{cls}" title="{esc(title)}">{esc(s.text)}</span>{tag}')
        cur = s.end
    out.append(esc(t[cur:]))
    legend = (f'<div class="sv-legend"><span><i style="background:{VERDICT_TINT["BLOCK"]};border-bottom:2px solid {VERDICT["BLOCK"]}"></i>Blocked segment</span>'
              f'<span><i style="background:{VERDICT_TINT["REVIEW"]};border-bottom:2px solid {VERDICT["REVIEW"]}"></i>Needs review</span>'
              f'<span><i style="outline:1.5px dashed {INK}"></i>Was hidden from human readers</span></div>')
    return f'{DOC_CSS}<div class="sv-doc" aria-label="Inspected document">{"".join(out)}</div>{legend}'


def bar(value: float, color: str) -> str:
    v = max(0.0, min(100.0, value))
    return f'<div class="sv-bar" aria-hidden="true"><div style="width:{v:.0f}%;background:{color}"></div></div>'
