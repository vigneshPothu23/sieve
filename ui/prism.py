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

[data-testid="stApp"]:has(.sv-prism) { background: #121B17; }
[data-testid="stApp"]:has(.sv-prism) header[data-testid="stHeader"] { background: transparent; }
[data-testid="stApp"]:has(.sv-prism) .block-container { max-width: 1280px; padding-top: 2.5rem; }
[data-testid="stApp"]:has(.sv-prism) h1,
[data-testid="stApp"]:has(.sv-prism) h2,
[data-testid="stApp"]:has(.sv-prism) h3,
[data-testid="stApp"]:has(.sv-prism) h4,
[data-testid="stApp"]:has(.sv-prism) p,
[data-testid="stApp"]:has(.sv-prism) label { font-family: 'Inter', system-ui, sans-serif; color: #F2EFE6; }
[data-testid="stApp"]:has(.sv-prism) h4 { font-size: 15px !important; font-weight: 600 !important; margin: .2rem 0 .6rem !important; }
[data-testid="stApp"]:has(.sv-prism) [data-testid="stCaptionContainer"] p,
[data-testid="stApp"]:has(.sv-prism) .sv-note { color: #8CA196 !important; font-size: 13px; }

/* Sidebar: same navigation and controls, dark to match the page */
[data-testid="stApp"]:has(.sv-prism) section[data-testid="stSidebar"] { background: #18231E; border-right: 1px solid #2B3A33; }
[data-testid="stApp"]:has(.sv-prism) section[data-testid="stSidebar"] h2,
[data-testid="stApp"]:has(.sv-prism) section[data-testid="stSidebar"] h3,
[data-testid="stApp"]:has(.sv-prism) section[data-testid="stSidebar"] h4,
[data-testid="stApp"]:has(.sv-prism) section[data-testid="stSidebar"] p { color: #F2EFE6; }
[data-testid="stApp"]:has(.sv-prism) section[data-testid="stSidebar"] button {
  background: #121B17 !important; color: #F2EFE6 !important; border: 1px solid #2B3A33 !important; border-radius: 999px !important; }
[data-testid="stApp"]:has(.sv-prism) section[data-testid="stSidebar"] button p { color: #F2EFE6 !important; }
[data-testid="stApp"]:has(.sv-prism) section[data-testid="stSidebar"] button:hover { border-color: #B4D955 !important; }

/* Header bar and pipeline */
.sv-prism-bar { display: flex; justify-content: space-between; align-items: center; gap: 1rem; flex-wrap: wrap;
  border-bottom: 1px solid #2B3A33; padding: 0 0 .9rem; margin-bottom: 1.8rem;
  font-family: 'JetBrains Mono', monospace; font-size: 13px; letter-spacing: .08em; color: #F2EFE6; }
.sv-prism-brand { display: flex; align-items: center; gap: 10px; font-weight: 500; }
.sv-prism-dot { width: 9px; height: 9px; border-radius: 50%; background: #B4D955; display: inline-block; }
.sv-prism-user { color: #8CA196; font-size: 13px; }
.sv-prism-h1 { font-size: 34px !important; font-weight: 600 !important; letter-spacing: -.02em !important; margin: 0 0 .35rem !important; }
.sv-prism-sub { color: #8CA196 !important; font-size: 15px; margin: 0 0 1.4rem !important; max-width: 72ch; }

.sv-pipe { display: flex; flex-wrap: wrap; gap: 8px 14px; align-items: center; font-family: 'JetBrains Mono', monospace;
  font-size: 12px; letter-spacing: .08em; text-transform: uppercase; color: #8CA196; margin: 0 0 1.2rem; }
.sv-pipe .done { color: #F2EFE6; }
.sv-pipe .now { color: #B4D955; }
.sv-pipe .arrow { color: #2B3A33; }

/* Verdict: the single loud element, colour-coded per decision */
.sv-pv { display: grid; grid-template-columns: auto 1fr auto; gap: 1.2rem; align-items: center;
  border: 1px solid #2B3A33; border-left: 6px solid var(--c); background: var(--t); border-radius: 14px; padding: 1rem 1.25rem; margin: 0 0 1.4rem; }
.sv-pv-word { font-size: 1.7rem; font-weight: 700; color: var(--c); letter-spacing: -.01em; }
.sv-pv-why { color: #F2EFE6; font-size: 15px; line-height: 1.5; }
.sv-pv-num { text-align: right; font-family: 'JetBrains Mono', monospace; }
.sv-pv-num b { font-size: 1.9rem; color: #F2EFE6; font-weight: 500; }
.sv-pv-num span { display: block; color: #8CA196; font-size: 12px; }
.sv-pv.ALLOW { --c: #B4D955; --t: rgba(180, 217, 85, .07); }
.sv-pv.REVIEW { --c: #E2B45A; --t: rgba(226, 180, 90, .08); }
.sv-pv.BLOCK { --c: #E8877B; --t: rgba(125, 59, 52, .28); }
@media (max-width: 640px) { .sv-pv { grid-template-columns: 1fr; } .sv-pv-num { text-align: left; } }

/* Panels */
[data-testid="stApp"]:has(.sv-prism) [class*="st-key-sv-panel"] {
  background: #18231E !important; border: 1px solid #2B3A33 !important; border-radius: 18px !important; padding: 1.3rem 1.2rem !important; }
.sv-plabel { font-family: 'JetBrains Mono', monospace; font-size: 12px; letter-spacing: .14em; text-transform: uppercase;
  color: #8CA196; display: flex; align-items: center; gap: 10px; flex-wrap: wrap; margin-bottom: .9rem; }
.sv-pill { font-family: 'JetBrains Mono', monospace; font-size: 11px; letter-spacing: .12em; text-transform: uppercase;
  padding: 4px 10px; border-radius: 999px; border: 1px solid #2B3A33; color: #8CA196; white-space: nowrap; }
.sv-pill.ok { color: #B4D955; border-color: rgba(180, 217, 85, .5); background: rgba(180, 217, 85, .08); }
.sv-pill.warn { color: #F2EFE6; background: #7D3B34; border-color: #7D3B34; }

/* Segment cards (column 1) */
.sv-seglist { max-height: 620px; overflow-y: auto; padding-right: 4px; }
.sv-seg { border: 1px solid #2B3A33; border-left: 4px solid var(--c, #2B3A33); border-radius: 12px; background: #121B17;
  padding: .75rem .9rem; margin-bottom: .7rem; }
.sv-seg.REVIEW { --c: #E2B45A; background: rgba(226, 180, 90, .06); }
.sv-seg.BLOCK { --c: #E8877B; background: rgba(125, 59, 52, .22); }
.sv-seg.ALLOW { --c: #2B3A33; }
.sv-seg-head { display: flex; flex-wrap: wrap; gap: 6px 10px; align-items: center; font-family: 'JetBrains Mono', monospace;
  font-size: 12px; color: #8CA196; margin-bottom: .45rem; }
.sv-seg-head .id { color: var(--c, #8CA196); font-weight: 500; }
.sv-seg-head .hid { color: #F2EFE6; border: 1px dashed #8CA196; border-radius: 6px; padding: 0 6px; }
.sv-seg-text { font-family: 'JetBrains Mono', monospace; font-size: 13.5px; line-height: 1.6; color: #F2EFE6;
  white-space: pre-wrap; word-break: break-word; }
.sv-seg.BLOCK .sv-seg-text { color: #F3D9D4; }

/* Evidence (column 2) */
.sv-kv { display: grid; grid-template-columns: 1fr auto; gap: 6px 14px; font-size: 14px; color: #F2EFE6; margin: .3rem 0 .8rem; }
.sv-kv .n { font-family: 'JetBrains Mono', monospace; text-align: right; color: #8CA196; }
.sv-kv .n.pos { color: #E8877B; }
.sv-kv .n.neg { color: #B4D955; }
.sv-kv .base { color: #8CA196; border-top: 1px solid #2B3A33; padding-top: 6px; }
.sv-match { font-family: 'JetBrains Mono', monospace; font-size: 12px; background: #121B17; border: 1px solid #2B3A33;
  padding: 1px 6px; border-radius: 6px; color: #F2EFE6; word-break: break-word; }
.sv-rule { font-size: 14px; color: #F2EFE6; margin: .3rem 0; line-height: 1.5; }
.sv-finding { border-left: 3px solid #8CA196; padding: .4rem .8rem; margin: .5rem 0; font-size: 14px; color: #F2EFE6; }
.sv-finding .excerpt { font-family: 'JetBrains Mono', monospace; font-size: 12px; color: #8CA196; display: block; margin-top: 4px; word-break: break-word; }

.sv-bar { height: 8px; background: #0F1713; border: 1px solid #2B3A33; border-radius: 6px; overflow: hidden; margin: .4rem 0 .8rem; }
.sv-bar > div { height: 100%; }

/* History table, dark */
.sv-hist { width: 100%; border-collapse: collapse; font-size: 13px; color: #F2EFE6; }
.sv-hist th { text-align: left; font-family: 'JetBrains Mono', monospace; font-size: 11px; letter-spacing: .12em;
  text-transform: uppercase; color: #8CA196; font-weight: 500; border-bottom: 1px solid #2B3A33; padding: 6px 8px; }
.sv-hist td { border-bottom: 1px solid #2B3A33; padding: 8px; vertical-align: top; }
.sv-hist .prev { color: #8CA196; }
.sv-hist .mono { font-family: 'JetBrains Mono', monospace; }
.sv-hist .v { font-family: 'JetBrains Mono', monospace; font-weight: 500; }
.sv-hist .v.ALLOW { color: #B4D955; }
.sv-hist .v.REVIEW { color: #E2B45A; }
.sv-hist .v.BLOCK { color: #E8877B; }

/* Controls */
[data-testid="stApp"]:has(.sv-prism) [data-testid="stWidgetLabel"] p {
  color: #8CA196 !important; font-family: 'JetBrains Mono', monospace !important; font-size: 12px !important;
  letter-spacing: .12em; text-transform: uppercase; }
[data-testid="stApp"]:has(.sv-prism) [data-testid="stTextArea"] textarea,
[data-testid="stApp"]:has(.sv-prism) [data-testid="stTextInput"] input {
  background: #0F1713 !important; color: #F2EFE6 !important; border: 1px solid #2B3A33 !important; border-radius: 12px !important;
  font-family: 'JetBrains Mono', monospace !important; font-size: 14px !important; line-height: 1.55 !important; }
[data-testid="stApp"]:has(.sv-prism) [data-testid="stTextArea"] textarea:focus,
[data-testid="stApp"]:has(.sv-prism) [data-testid="stTextInput"] input:focus { border-color: #B4D955 !important; box-shadow: none !important; }
[data-testid="stApp"]:has(.sv-prism) [data-testid="stSelectbox"] div {
  background-color: #0F1713 !important; color: #F2EFE6 !important; }
[data-testid="stApp"]:has(.sv-prism) [data-testid="stSelectbox"] input { background: transparent !important; color: #F2EFE6 !important; }
[data-testid="stApp"]:has(.sv-prism) [data-testid="stSelectbox"] [data-baseweb="select"] > div {
  background: #0F1713 !important; border: 1px solid #2B3A33 !important; border-radius: 10px !important; color: #F2EFE6 !important; }
[data-testid="stApp"]:has(.sv-prism) [data-testid="stSelectbox"] [data-baseweb="select"] span,
[data-testid="stApp"]:has(.sv-prism) [data-testid="stSelectbox"] [data-baseweb="select"] svg { color: #F2EFE6 !important; fill: #F2EFE6 !important; }
[data-testid="stApp"]:has(.sv-prism) [data-testid="stFileUploader"] section {
  background: #0F1713 !important; border: 1px dashed #2B3A33 !important; border-radius: 12px !important; }
[data-testid="stApp"]:has(.sv-prism) [data-testid="stFileUploader"] button {
  background: transparent !important; color: #F2EFE6 !important; border: 1px solid #2B3A33 !important; border-radius: 999px !important; }
[data-testid="stApp"]:has(.sv-prism) [data-testid="stFileUploaderDeleteBtn"] button { border: none !important; }
[data-testid="stApp"]:has(.sv-prism) [data-testid="stFileUploaderDropzoneInstructions"] *,
[data-testid="stApp"]:has(.sv-prism) [data-testid="stFileUploaderDropzone"] small { color: #8CA196 !important; }
[data-testid="stApp"]:has(.sv-prism) [data-testid="stTooltipIcon"] svg,
[data-testid="stApp"]:has(.sv-prism) [data-testid="stTooltipHoverTarget"] svg { color: #8CA196 !important; fill: #8CA196 !important; }
[data-testid="stApp"]:has(.sv-prism) [data-testid="stRadio"] label p,
[data-testid="stApp"]:has(.sv-prism) [data-testid="stToggle"] label p { color: #F2EFE6 !important; text-transform: none; letter-spacing: 0; font-family: 'Inter', sans-serif !important; font-size: 14px !important; }
[data-testid="stApp"]:has(.sv-prism) [data-testid="stToggle"] [data-baseweb="checkbox"] > div { background: #2B3A33; }
[data-testid="stApp"]:has(.sv-prism) [data-testid="stToggle"] [aria-checked="true"] + div,
[data-testid="stApp"]:has(.sv-prism) [data-testid="stToggle"] input:checked + div { background: #B4D955 !important; }

/* Buttons: lime primary, outlined secondary, coral for Clear */
[data-testid="stApp"]:has(.sv-prism) button[kind="primary"],
[data-testid="stApp"]:has(.sv-prism) [data-testid="stBaseButton-primary"] {
  background: #B4D955 !important; color: #121B17 !important; border: none !important; border-radius: 12px !important;
  font-weight: 600 !important; box-shadow: 0 4px 0 #7E9C3A; min-height: 46px; }
[data-testid="stApp"]:has(.sv-prism) button[kind="primary"] p,
[data-testid="stApp"]:has(.sv-prism) [data-testid="stBaseButton-primary"] p { color: #121B17 !important; }
[data-testid="stApp"]:has(.sv-prism) button[kind="primary"]:hover { background: #C3E36E !important; }
[data-testid="stApp"]:has(.sv-prism) button[kind="primary"]:disabled { background: #2B3A33 !important; color: #8CA196 !important; box-shadow: none; }
[data-testid="stApp"]:has(.sv-prism) button[kind="secondary"],
[data-testid="stApp"]:has(.sv-prism) [data-testid="stBaseButton-secondary"] {
  background: transparent !important; color: #F2EFE6 !important; border: 1px solid #2B3A33 !important; border-radius: 12px !important; min-height: 46px; }
[data-testid="stApp"]:has(.sv-prism) button[kind="secondary"]:hover { border-color: #B4D955 !important; }
[data-testid="stApp"]:has(.sv-prism) [data-testid="stCodeBlock"], 
[data-testid="stApp"]:has(.sv-prism) [data-testid="stCode"] pre { background: #0F1713 !important; border: 1px solid #2B3A33 !important; border-radius: 12px !important; }
[data-testid="stApp"]:has(.sv-prism) [data-testid="stCode"] code { color: #B4D955 !important; font-family: 'JetBrains Mono', monospace !important; font-size: 13px !important; }
[data-testid="stApp"]:has(.sv-prism) [data-testid="stExpander"] details { background: #18231E; border: 1px solid #2B3A33; border-radius: 14px; }
[data-testid="stApp"]:has(.sv-prism) [data-testid="stExpander"] summary { background: #18231E !important; color: #F2EFE6 !important; }
[data-testid="stApp"]:has(.sv-prism) [data-testid="stExpander"] summary:hover { background: #1F2D27 !important; }
[data-testid="stApp"]:has(.sv-prism) [data-testid="stExpander"] summary svg { color: #F2EFE6 !important; fill: #F2EFE6 !important; }
[data-testid="stApp"]:has(.sv-prism) [data-testid="stExpander"] [data-testid="stExpanderDetails"] { background: #18231E; }
[data-testid="stApp"]:has(.sv-prism) .sv-finding { background: transparent !important; color: #F2EFE6 !important; border-left: 3px solid #8CA196; }
[data-testid="stApp"]:has(.sv-prism) .sv-finding b { color: #F2EFE6; }
[data-testid="stApp"]:has(.sv-prism) [data-testid="stToggle"] label,
[data-testid="stApp"]:has(.sv-prism) [data-testid="stToggle"] label * {
  text-transform: none !important; letter-spacing: 0 !important; font-family: 'Inter', sans-serif !important; }
[data-testid="stApp"]:has(.sv-prism) [data-testid="stToggle"] [data-testid="stWidgetLabel"] p { text-transform: none !important; letter-spacing: 0 !important; font-family: 'Inter', sans-serif !important; font-size: 14px !important; color: #F2EFE6 !important; }
[data-testid="stApp"]:has(.sv-prism) [data-testid="stExpander"] summary p { color: #F2EFE6 !important; font-family: 'Inter', sans-serif; }
[data-testid="stApp"]:has(.sv-prism) [data-testid="stAlert"] { background: #18231E; border: 1px solid #2B3A33; }

@media (max-width: 640px) {
  [data-testid="stApp"]:has(.sv-prism) .block-container { padding-top: 1.25rem; }
  .sv-prism-h1 { font-size: 28px !important; }
  .sv-seglist { max-height: none; }
}
</style>
"""


def inject_prism_css() -> None:
    """Add the Prism styles. Call once at the top of the Prism page."""
    st.markdown(_PRISM_CSS, unsafe_allow_html=True)


def prism_header(display_name: str, username: str) -> None:
    """Top bar with the product and workspace name, plus the signed-in analyst (real session data)."""
    st.markdown(
        '<div class="sv-prism"></div>'
        '<div class="sv-prism-bar">'
        '<span class="sv-prism-brand"><span class="sv-prism-dot"></span>SIEVE // PRISM INSPECT</span>'
        f'<span class="sv-prism-user">{esc(display_name)} · {esc(username)}</span>'
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
    colour = {"ALLOW": "#B4D955", "REVIEW": "#E2B45A", "BLOCK": "#E8877B"}[verdict]
    return f'<div class="sv-bar" aria-hidden="true"><div style="width:{v:.0f}%;background:{colour}"></div></div>'


def panel_label(text: str, extra: str = "") -> str:
    return f'<div class="sv-plabel">{esc(text)}{extra}</div>'
