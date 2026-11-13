"""Prism content-inspection workspace: layout and styling helpers (Stage 3 of the SIEVE UI redesign).

Presentation only. Every number, label and segment shown here comes from the scan result
or the model passed in; nothing is hard-coded. Styles are scoped with ``:has(.sv-prism)``,
so they apply only on the Prism page. Every value is HTML-escaped before it is shown.
"""
from __future__ import annotations

import streamlit as st

from sieve.engine import ScanResult

from .theme import esc

VERDICT_WORD = {"ALLOW": "Allowed", "REVIEW": "Needs review", "BLOCK": "Blocked"}

_PRISM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

/* Neutral charcoal palette: bg #111111, panels #1B1B1B, inputs #141414, borders #303030.
   Primary #C5E86C; ALLOW restrained lime #A7C957; REVIEW amber #E3A848; BLOCK muted coral #E8877B. */
[data-testid="stApp"]:has(.sv-prism) { background: #111111; }
[data-testid="stApp"]:has(.sv-prism) header[data-testid="stHeader"] { background: transparent; }
[data-testid="stApp"]:has(.sv-prism) .block-container { max-width: none; padding-top: 2rem; }
[data-testid="stApp"]:has(.sv-prism) h1,
[data-testid="stApp"]:has(.sv-prism) h2,
[data-testid="stApp"]:has(.sv-prism) h3,
[data-testid="stApp"]:has(.sv-prism) h4,
[data-testid="stApp"]:has(.sv-prism) p,
[data-testid="stApp"]:has(.sv-prism) label { font-family: 'Inter', system-ui, sans-serif; color: #EDEDED; }
[data-testid="stApp"]:has(.sv-prism) h4 { font-size: 15px !important; font-weight: 600 !important; margin: .2rem 0 .6rem !important; }
[data-testid="stApp"]:has(.sv-prism) [data-testid="stCaptionContainer"] p,
[data-testid="stApp"]:has(.sv-prism) .sv-note { color: #A0A0A0 !important; font-size: 13px; }

/* Header bar */
.sv-prism-bar { display: flex; justify-content: space-between; align-items: center; gap: 1rem; flex-wrap: wrap;
  border-bottom: 1px solid #303030; padding: 0 0 .8rem; margin-bottom: 1.6rem;
  font-family: 'JetBrains Mono', monospace; font-size: 13px; letter-spacing: .06em; color: #EDEDED; }
.sv-prism-brand { display: flex; align-items: center; gap: 10px; font-weight: 500; }
.sv-prism-dot { width: 9px; height: 9px; border-radius: 50%; background: #C5E86C; display: inline-block; }
.sv-prism-user { color: #A0A0A0; font-size: 13px; }
.sv-prism-h1 { font-size: 34px !important; font-weight: 650 !important; letter-spacing: -.02em !important; margin: 0 0 .4rem !important; }
.sv-prism-sub { color: #A0A0A0 !important; font-size: 16px; margin: 0 0 1.5rem !important; max-width: 60ch; }

/* Pipeline (kept, quieter) */
.sv-pipe { display: flex; flex-wrap: wrap; gap: 6px 14px; align-items: center; font-family: 'JetBrains Mono', monospace;
  font-size: 12px; color: #A0A0A0; margin: 0 0 1.3rem; }
.sv-pipe .done { color: #EDEDED; }
.sv-pipe .now { color: #C5E86C; }
.sv-pipe .arrow { color: #4A4A4A; }

/* Verdict: the one prominent element on the page */
.sv-pv { display: grid; grid-template-columns: auto 1fr auto; gap: 1.2rem; align-items: center;
  background: var(--t); border: 1px solid #303030; border-left: 6px solid var(--c); border-radius: 14px;
  padding: 1.1rem 1.3rem; margin: 0 0 1.4rem; }
.sv-pv-word { font-size: 1.8rem; font-weight: 650; color: var(--c); letter-spacing: -.01em; }
.sv-pv-why { color: #EDEDED; font-size: 15px; line-height: 1.5; }
.sv-pv-num { text-align: right; font-family: 'JetBrains Mono', monospace; }
.sv-pv-num b { font-size: 2rem; color: #EDEDED; font-weight: 500; }
.sv-pv-num span { display: block; color: #A0A0A0; font-size: 12px; }
.sv-pv.ALLOW { --c: #A7C957; --t: rgba(167, 201, 87, .06); }
.sv-pv.REVIEW { --c: #E3A848; --t: rgba(227, 168, 72, .07); }
.sv-pv.BLOCK { --c: #E8877B; --t: rgba(232, 135, 123, .09); }
@media (max-width: 640px) { .sv-pv { grid-template-columns: 1fr; } .sv-pv-num { text-align: left; } }

/* Panels: one level of containers only */
[data-testid="stApp"]:has(.sv-prism) [class*="st-key-sv-panel"] {
  background: #1B1B1B !important; border: 1px solid #303030 !important; border-radius: 16px !important; padding: 1.2rem 1.25rem !important; }
.sv-plabel { font-family: 'Inter', system-ui, sans-serif; font-size: 16px; font-weight: 600; color: #EDEDED;
  display: flex; align-items: center; gap: 10px; flex-wrap: wrap; margin-bottom: .9rem; }
.sv-pill { font-family: 'JetBrains Mono', monospace; font-size: 11px; font-weight: 400; padding: 3px 10px; border-radius: 999px;
  border: 1px solid #303030; color: #A0A0A0; white-space: nowrap; }

/* Segments: full-width list, no inner scroll */
.sv-seglist { display: flex; flex-direction: column; gap: .55rem; }
.sv-seg { border: 1px solid #303030; border-left: 4px solid var(--c, #303030); border-radius: 12px; background: #141414;
  padding: .7rem .95rem; }
.sv-seg.REVIEW { --c: #E3A848; background: rgba(227, 168, 72, .05); }
.sv-seg.BLOCK { --c: #E8877B; background: rgba(232, 135, 123, .07); }
.sv-seg.ALLOW { --c: #303030; }
.sv-seg-head { display: flex; flex-wrap: wrap; gap: 6px 10px; align-items: center; font-size: 12.5px; color: #A0A0A0; margin-bottom: .4rem; }
.sv-seg-head .id { color: var(--c, #A0A0A0); font-family: 'JetBrains Mono', monospace; font-weight: 500; }
.sv-seg-head .hid { color: #EDEDED; border: 1px dashed #6E6E6E; border-radius: 6px; padding: 0 6px; font-size: 12px; }
.sv-seg-text { font-family: 'JetBrains Mono', monospace; font-size: 13.5px; line-height: 1.6; color: #EDEDED;
  white-space: pre-wrap; word-break: break-word; }
.sv-seg.BLOCK .sv-seg-text { color: #F4DCD7; }

/* Evidence */
.sv-kv { display: grid; grid-template-columns: 1fr auto; gap: 6px 14px; font-size: 14px; color: #EDEDED; margin: .3rem 0 .8rem; }
.sv-kv .n { font-family: 'JetBrains Mono', monospace; text-align: right; color: #A0A0A0; }
.sv-kv .n.pos { color: #E8877B; }
.sv-kv .n.neg { color: #A7C957; }
.sv-kv .base { color: #A0A0A0; border-top: 1px solid #303030; padding-top: 6px; }
.sv-match { font-family: 'JetBrains Mono', monospace; font-size: 12px; background: #141414; border: 1px solid #303030;
  padding: 1px 6px; border-radius: 6px; color: #EDEDED; word-break: break-word; }
.sv-rule { font-size: 14px; color: #EDEDED; margin: .3rem 0; line-height: 1.5; }
[data-testid="stApp"]:has(.sv-prism) .sv-adv { margin: .7rem 0 0; border-top: 1px solid #303030; padding-top: .5rem; }
[data-testid="stApp"]:has(.sv-prism) .sv-adv summary { cursor: pointer; font-size: 13px; color: #A0A0A0; padding: 4px 0; }
[data-testid="stApp"]:has(.sv-prism) .sv-adv-h { font-size: 13px; font-weight: 600; color: #EDEDED; margin: .5rem 0 .2rem; }
.sv-finding { border-left: 3px solid #A0A0A0; padding: .4rem .8rem; margin: .5rem 0; font-size: 14px; color: #EDEDED; }
.sv-finding .excerpt { font-family: 'JetBrains Mono', monospace; font-size: 12px; color: #A0A0A0; display: block; margin-top: 4px; word-break: break-word; }
[data-testid="stApp"]:has(.sv-prism) .sv-finding { background: transparent !important; }
.sv-bar { height: 8px; background: #141414; border: 1px solid #303030; border-radius: 6px; overflow: hidden; margin: .4rem 0 .8rem; }
.sv-bar > div { height: 100%; }

/* Session history */
.sv-hist { width: 100%; border-collapse: collapse; font-size: 13.5px; color: #EDEDED; }
.sv-hist th { text-align: left; font-size: 12px; color: #A0A0A0; font-weight: 500; border-bottom: 1px solid #303030; padding: 6px 8px; }
.sv-hist td { border-bottom: 1px solid #303030; padding: 8px; vertical-align: top; }
.sv-hist .prev { color: #A0A0A0; }
.sv-hist .mono { font-family: 'JetBrains Mono', monospace; }
.sv-hist .v { font-family: 'JetBrains Mono', monospace; font-weight: 500; }
.sv-hist .v.ALLOW { color: #A7C957; }
.sv-hist .v.REVIEW { color: #E3A848; }
.sv-hist .v.BLOCK { color: #E8877B; }

/* Controls */
[data-testid="stApp"]:has(.sv-prism) [data-testid="stWidgetLabel"] p {
  color: #B5B5B5 !important; font-family: 'Inter', sans-serif !important; font-size: 14px !important; font-weight: 500 !important; }
[data-testid="stApp"]:has(.sv-prism) [data-testid="stTextArea"] textarea,
[data-testid="stApp"]:has(.sv-prism) [data-testid="stTextInput"] input {
  background: #141414 !important; color: #EDEDED !important; border: 1px solid #303030 !important; border-radius: 12px !important;
  font-family: 'JetBrains Mono', monospace !important; font-size: 14px !important; line-height: 1.55 !important; }
[data-testid="stApp"]:has(.sv-prism) [data-testid="stTextArea"] textarea:focus,
[data-testid="stApp"]:has(.sv-prism) [data-testid="stTextInput"] input:focus { border-color: #C5E86C !important; box-shadow: none !important; }
[data-testid="stApp"]:has(.sv-prism) [data-testid="stSelectbox"] div { background-color: #141414 !important; color: #EDEDED !important; }
[data-testid="stApp"]:has(.sv-prism) [data-testid="stSelectbox"] input { background: transparent !important; color: #EDEDED !important; }
[data-testid="stApp"]:has(.sv-prism) [data-testid="stSelectbox"] [data-baseweb="select"] > div {
  background: #141414 !important; border: 1px solid #303030 !important; border-radius: 10px !important; color: #EDEDED !important; }
[data-testid="stApp"]:has(.sv-prism) [data-testid="stSelectbox"] [data-baseweb="select"] span,
[data-testid="stApp"]:has(.sv-prism) [data-testid="stSelectbox"] [data-baseweb="select"] svg { color: #EDEDED !important; fill: #EDEDED !important; }
[data-testid="stApp"]:has(.sv-prism) [data-testid="stFileUploader"] section {
  background: #141414 !important; border: 1px dashed #303030 !important; border-radius: 12px !important; }
[data-testid="stApp"]:has(.sv-prism) [data-testid="stFileUploaderDropzoneInstructions"] *,
[data-testid="stApp"]:has(.sv-prism) [data-testid="stFileUploaderDropzone"] small { color: #A0A0A0 !important; }
[data-testid="stApp"]:has(.sv-prism) [data-testid="stTooltipIcon"] svg,
[data-testid="stApp"]:has(.sv-prism) [data-testid="stTooltipHoverTarget"] svg { color: #A0A0A0 !important; fill: #A0A0A0 !important; }
[data-testid="stApp"]:has(.sv-prism) [data-testid="stRadio"] label p,
[data-testid="stApp"]:has(.sv-prism) [data-testid="stToggle"] label p { color: #EDEDED !important; font-family: 'Inter', sans-serif !important; font-size: 14px !important; font-weight: 400 !important; text-transform: none !important; letter-spacing: 0 !important; }
[data-testid="stApp"]:has(.sv-prism) [data-testid="stToggle"] [data-baseweb="checkbox"] > div { background: #303030; }
[data-testid="stApp"]:has(.sv-prism) [data-testid="stToggle"] [aria-checked="true"] + div,
[data-testid="stApp"]:has(.sv-prism) [data-testid="stToggle"] input:checked + div { background: #C5E86C !important; }

/* Buttons: lime primary only for the main action; outlined secondary otherwise */
[data-testid="stApp"]:has(.sv-prism) button[kind="primary"],
[data-testid="stApp"]:has(.sv-prism) [data-testid="stBaseButton-primary"] {
  background: #C5E86C !important; color: #111111 !important; border: none !important; border-radius: 12px !important;
  font-weight: 600 !important; box-shadow: none !important; min-height: 46px; }
[data-testid="stApp"]:has(.sv-prism) button[kind="primary"] p,
[data-testid="stApp"]:has(.sv-prism) [data-testid="stBaseButton-primary"] p { color: #111111 !important; }
[data-testid="stApp"]:has(.sv-prism) button[kind="primary"]:hover { background: #D4F08A !important; }
[data-testid="stApp"]:has(.sv-prism) button[kind="primary"]:disabled { background: #2A2A2A !important; color: #7A7A7A !important; }
[data-testid="stApp"]:has(.sv-prism) button[kind="secondary"],
[data-testid="stApp"]:has(.sv-prism) [data-testid="stBaseButton-secondary"] {
  background: transparent !important; color: #EDEDED !important; border: 1px solid #303030 !important; border-radius: 12px !important; min-height: 46px; }
[data-testid="stApp"]:has(.sv-prism) button[kind="secondary"]:hover { border-color: #C5E86C !important; }
[data-testid="stApp"]:has(.sv-prism) [data-testid="stCodeBlock"],
[data-testid="stApp"]:has(.sv-prism) [data-testid="stCode"] pre { background: #141414 !important; border: 1px solid #303030 !important; border-radius: 12px !important; }
[data-testid="stApp"]:has(.sv-prism) [data-testid="stCode"] code { color: #E6E6E6 !important; font-family: 'JetBrains Mono', monospace !important; font-size: 13px !important; }
[data-testid="stApp"]:has(.sv-prism) [data-testid="stExpander"] details { background: #1B1B1B; border: 1px solid #303030; border-radius: 14px; }
[data-testid="stApp"]:has(.sv-prism) [data-testid="stExpander"] summary { background: #1B1B1B !important; color: #EDEDED !important; }
[data-testid="stApp"]:has(.sv-prism) [data-testid="stExpander"] summary:hover { background: #232323 !important; }
[data-testid="stApp"]:has(.sv-prism) [data-testid="stExpander"] summary svg { color: #EDEDED !important; fill: #EDEDED !important; }
[data-testid="stApp"]:has(.sv-prism) [data-testid="stExpander"] [data-testid="stExpanderDetails"] { background: #1B1B1B; }
[data-testid="stApp"]:has(.sv-prism) [data-testid="stExpander"] summary p { color: #EDEDED !important; font-family: 'Inter', sans-serif; }
[data-testid="stApp"]:has(.sv-prism) [data-testid="stAlert"] { background: #1B1B1B; border: 1px solid #303030; }

@media (max-width: 640px) {
  [data-testid="stApp"]:has(.sv-prism) .block-container { padding-top: 1.25rem; }
  .sv-prism-h1 { font-size: 28px !important; }
}
</style>
"""


def inject_prism_css() -> None:
    """Add the Prism styles. Call once at the top of the Prism page."""
    st.markdown(_PRISM_CSS, unsafe_allow_html=True)


def _identity(display_name: str, username: str) -> str:
    """Show the account once when the display name and username are the same."""
    if display_name and display_name != username:
        return f"{esc(display_name)} · {esc(username)}"
    return esc(display_name or username)


def prism_header(display_name: str, username: str) -> None:
    """Top bar with the product and workspace name, plus the signed-in analyst (real session data)."""
    st.markdown(
        '<div class="sv-prism"></div>'
        '<div class="sv-prism-bar">'
        '<span class="sv-prism-brand"><span class="sv-prism-dot"></span>SIEVE // PRISM INSPECT</span>'
        f'<span class="sv-prism-user">{_identity(display_name, username)}</span>'
        "</div>",
        unsafe_allow_html=True,
    )


def pipeline(result: ScanResult | None) -> str:
    """Four stages of the scan. Stages show as done only after a real scan has run."""
    if result is None:
        steps = ["1. Normalise", "2. Segment & score", "3. Decide", "4. Sanitise"]
        return '<div class="sv-pipe">' + '<span class="arrow">→</span>'.join(f"<span>{esc(s)}</span>" for s in steps) + "</div>"
    decide = f"3. Decide: {VERDICT_WORD[result.verdict]}"
    parts = [
        '<span class="done">1. Normalise ✓</span>',
        '<span class="done">2. Segment &amp; score ✓</span>',
        f'<span class="now">{esc(decide)}</span>',
        '<span class="done">4. Sanitise ✓</span>',
    ]
    return '<div class="sv-pipe">' + '<span class="arrow">→</span>'.join(parts) + "</div>"


def verdict_card(result: ScanResult, why: str) -> str:
    """The loud verdict strip. Colour is set per decision; the numbers come from the scan."""
    return (
        f'<div class="sv-pv {esc(result.verdict)}" role="status">'
        f'<div class="sv-pv-word">{esc(VERDICT_WORD[result.verdict])}</div>'
        f'<div class="sv-pv-why">{esc(why)}</div>'
        f'<div class="sv-pv-num"><b>{result.risk:.0f}</b><span>risk index of 100</span>'
        f'<span>{result.latency_ms:.1f} ms</span></div></div>'
    )


def segment_cards(result: ScanResult) -> str:
    """Every segment of the normalised text, in order, with its own verdict and risk. Text is escaped."""
    cards = []
    for s in result.segments:
        hidden = '<span class="hid">hidden from readers</span>' if s.hidden else ""
        cards.append(
            f'<div class="sv-seg {esc(s.verdict)}">'
            f'<div class="sv-seg-head"><span class="id">S{s.index + 1} · {s.risk:.0f}</span>'
            f'<span>{esc(VERDICT_WORD[s.verdict])}</span>{hidden}</div>'
            f'<div class="sv-seg-text">{esc(s.text)}</div></div>'
        )
    return f'<div class="sv-seglist">{"".join(cards)}</div>'


def hidden_finding(title: str, detail: str, excerpt: str) -> str:
    ex = f'<span class="excerpt">{esc(excerpt)}</span>' if excerpt else ""
    extra = f" — {esc(detail)}" if detail else ""
    return f'<div class="sv-finding"><b>{esc(title)}</b>{extra}{ex}</div>'


def fusion_table(rows: list[tuple[str, float]], intercept: float) -> str:
    """Contributions to the log-odds, largest first, with the baseline. Values are the model's own."""
    body = []
    for label, value in rows:
        cls = "pos" if value > 0 else "neg" if value < 0 else ""
        body.append(f'<span>{esc(label)}</span><span class="n {cls}">{value:+.2f}</span>')
    body.append(f'<span class="base">Baseline (intercept)</span><span class="n base">{intercept:+.2f}</span>')
    return f'<div class="sv-kv">{"".join(body)}</div>'


def history_table(rows: list[dict]) -> str:
    """This session's scans. Values come from the session history only."""
    head = "<tr><th>Time</th><th>Source</th><th>Verdict</th><th>Risk</th><th>Segments</th><th>Preview</th></tr>"
    body = []
    for r in rows:
        body.append(
            f'<tr><td class="mono">{esc(r["time"])}</td><td>{esc(r["source"])}</td>'
            f'<td class="v {esc(r["verdict"])}">{esc(VERDICT_WORD[r["verdict"]])}</td>'
            f'<td class="mono">{r["risk"]}</td>'
            f'<td class="mono">{r["flagged"]} of {r["segments"]} flagged</td>'
            f'<td class="prev">{esc(r["preview"])}</td></tr>'
        )
    return f'<table class="sv-hist"><thead>{head}</thead><tbody>{"".join(body)}</tbody></table>'


def risk_bar(risk: float, verdict: str) -> str:
    """Risk as a bar on the dark panel. The width is the scan's own risk index."""
    v = max(0.0, min(100.0, risk))
    colour = {"ALLOW": "#A7C957", "REVIEW": "#E3A848", "BLOCK": "#E8877B"}[verdict]
    return f'<div class="sv-bar" aria-hidden="true"><div style="width:{v:.0f}%;background:{colour}"></div></div>'


def panel_label(text: str, extra: str = "") -> str:
    return f'<div class="sv-plabel">{esc(text)}{extra}</div>'
