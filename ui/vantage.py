"""Vantage evaluation dashboard: layout and styling helpers (Stage 5 of the SIEVE UI redesign).

Presentation only. Every number, label and chart series shown here is read from the
evaluation report (reports/eval_results.json) or from the live test-case explorer. Nothing is
hard-coded and nothing illustrative is shown. Styles are scoped with ``:has(.sv-vantage)``,
so they apply only on the Vantage page. Every value is HTML-escaped before it is shown.
"""
from __future__ import annotations

import streamlit as st

from .theme import esc

LIME = "#B4D955"
SAGE = "#8CA196"
CREAM = "#F2EFE6"
CORAL = "#7D3B34"
CORAL_TXT = "#E8877B"
AMBER = "#E2B45A"
LINE = "#2B3A33"
PANEL = "#18231E"
GROUND = "#121B17"

# Chart colours, one per system, in the same order as before.
SYSTEM_COLOURS = {"sieve_flag": LIME, "sieve_block": "#8FB04A", "sieve_no_norm": "#6F8579",
                  "ml_only": "#56655D", "keyword_baseline": SAGE, "protectai_deberta": CREAM}

_VANTAGE_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

[data-testid="stApp"]:has(.sv-vantage) { background: #121B17; }
[data-testid="stApp"]:has(.sv-vantage) header[data-testid="stHeader"] { background: transparent; }
[data-testid="stApp"]:has(.sv-vantage) .block-container { max-width: none; padding-top: 2.5rem; }
[data-testid="stApp"]:has(.sv-vantage) h1,
[data-testid="stApp"]:has(.sv-vantage) h2,
[data-testid="stApp"]:has(.sv-vantage) h3,
[data-testid="stApp"]:has(.sv-vantage) h4,
[data-testid="stApp"]:has(.sv-vantage) p,
[data-testid="stApp"]:has(.sv-vantage) label,
[data-testid="stApp"]:has(.sv-vantage) li { font-family: 'Inter', system-ui, sans-serif; color: #F2EFE6; }
[data-testid="stApp"]:has(.sv-vantage) h3 { font-size: 16px !important; font-weight: 600 !important; margin: 0 0 .7rem !important; }
[data-testid="stApp"]:has(.sv-vantage) [data-testid="stCaptionContainer"] p,
[data-testid="stApp"]:has(.sv-vantage) .sv-note { color: #8CA196 !important; font-size: 13px; line-height: 1.5; }
[data-testid="stApp"]:has(.sv-vantage) code { background: #0F1713; color: #B4D955; border-radius: 6px; padding: 1px 6px; font-family: 'JetBrains Mono', monospace; }

/* Sidebar: same navigation and controls, dark to match the page */
[data-testid="stApp"]:has(.sv-vantage) section[data-testid="stSidebar"] { background: #18231E; border-right: 1px solid #2B3A33; }
[data-testid="stApp"]:has(.sv-vantage) section[data-testid="stSidebar"] h2,
[data-testid="stApp"]:has(.sv-vantage) section[data-testid="stSidebar"] h3,
[data-testid="stApp"]:has(.sv-vantage) section[data-testid="stSidebar"] p { color: #F2EFE6; }
[data-testid="stApp"]:has(.sv-vantage) section[data-testid="stSidebar"] button {
  background: #121B17 !important; color: #F2EFE6 !important; border: 1px solid #2B3A33 !important; border-radius: 999px !important; }
[data-testid="stApp"]:has(.sv-vantage) section[data-testid="stSidebar"] button p { color: #F2EFE6 !important; }

/* Header */
.sv-vantage-bar { display: flex; justify-content: space-between; align-items: center; gap: 1rem; flex-wrap: wrap;
  border-bottom: 1px solid #2B3A33; padding: 0 0 .9rem; margin-bottom: 1.4rem;
  font-family: 'JetBrains Mono', monospace; font-size: 13px; letter-spacing: .08em; color: #F2EFE6; }
.sv-vantage-brand { display: flex; align-items: center; gap: 10px; font-weight: 500; }
.sv-vantage-dot { width: 9px; height: 9px; border-radius: 50%; background: #B4D955; display: inline-block; }
.sv-vantage-user { color: #8CA196; font-size: 13px; }
.sv-vantage-h1 { font-size: 34px !important; font-weight: 600 !important; letter-spacing: -.02em !important; margin: 0 0 .35rem !important; }
.sv-lede { color: #8CA196 !important; font-size: 15px; line-height: 1.55; margin: 0 0 1.4rem !important; max-width: 80ch; }

/* Measured-results disclosure: real data, dated, never presented as a sample */
.sv-measured { display: flex; flex-wrap: wrap; gap: 6px 14px; align-items: center; border: 1px solid rgba(180, 217, 85, .45);
  background: rgba(180, 217, 85, .06); border-radius: 12px; padding: .7rem 1rem; margin: 0 0 1.4rem; }
.sv-measured-tag { font-family: 'JetBrains Mono', monospace; font-size: 12px; letter-spacing: .1em; color: #B4D955; font-weight: 500; }
.sv-measured-text { color: #F2EFE6; font-size: 14px; line-height: 1.5; flex: 1 1 360px; }

/* Panels */
[data-testid="stApp"]:has(.sv-vantage) [class*="st-key-sv-panel"] {
  background: #18231E !important; border: 1px solid #2B3A33 !important; border-radius: 18px !important; padding: 1.3rem 1.2rem !important; }
.sv-plabel { font-family: 'JetBrains Mono', monospace; font-size: 12px; letter-spacing: .14em; text-transform: uppercase;
  color: #8CA196; display: flex; align-items: center; gap: 10px; flex-wrap: wrap; margin-bottom: .9rem; }
.sv-pill { display: inline-flex; font-family: 'JetBrains Mono', monospace; font-size: 11px; letter-spacing: .08em; text-transform: uppercase;
  padding: 4px 10px; border-radius: 999px; border: 1px solid var(--c, #2B3A33); color: var(--c, #8CA196);
  background: var(--t, transparent); white-space: nowrap; }
.sv-pill-ok { color: #B4D955; border: 1px solid rgba(180, 217, 85, .5); background: rgba(180, 217, 85, .08);
  font-family: 'JetBrains Mono', monospace; font-size: 12px; padding: 5px 12px; border-radius: 999px; display: inline-block; }

/* Headline ring and KPI tiles */
.sv-hero { display: flex; flex-direction: column; align-items: center; gap: .9rem; text-align: center; padding: .4rem 0 .2rem; }
.sv-ring-wrap { position: relative; width: 170px; height: 170px; }
.sv-ring-wrap svg { width: 170px; height: 170px; transform: rotate(-90deg); }
.sv-ring-value { position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center;
  font-family: 'JetBrains Mono', monospace; font-size: 30px; font-weight: 500; color: #F2EFE6; }
.sv-ring-value span { font-family: 'Inter', sans-serif; font-size: 12px; color: #8CA196; letter-spacing: .04em; margin-top: 2px; }
.sv-hero-cap { color: #8CA196; font-size: 13px; line-height: 1.5; max-width: 34ch; }

.sv-kpis { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin: 0 0 1.4rem; }
.sv-kpi { border: 1px solid #2B3A33; border-radius: 14px; background: #18231E; padding: .9rem 1rem; }
.sv-kpi-label { font-family: 'JetBrains Mono', monospace; font-size: 11px; letter-spacing: .1em; text-transform: uppercase; color: #8CA196; line-height: 1.4; }
.sv-kpi-value { font-family: 'JetBrains Mono', monospace; font-size: 28px; font-weight: 500; color: #F2EFE6; margin-top: 6px; }
.sv-kpi-hint { font-size: 12.5px; color: #8CA196; margin-top: 4px; line-height: 1.45; }

/* Recall by family: bars from real values */
.sv-fam { margin-bottom: 14px; }
.sv-fam-head { display: flex; justify-content: space-between; align-items: baseline; gap: 10px; font-size: 14px; color: #F2EFE6; }
.sv-fam-head b { font-family: 'JetBrains Mono', monospace; font-weight: 500; color: #B4D955; font-size: 14px; }
.sv-fam-head b.mid { color: #E2B45A; }
.sv-fam-head b.low { color: #E8877B; }
.sv-track { height: 8px; background: #0F1713; border: 1px solid #2B3A33; border-radius: 6px; overflow: hidden; margin-top: 6px; }
.sv-track > div { height: 100%; border-radius: 6px; }

/* Tables */
.sv-table { width: 100%; border-collapse: collapse; font-size: 13px; color: #F2EFE6; }
.sv-table th { text-align: left; font-family: 'JetBrains Mono', monospace; font-size: 11px; letter-spacing: .1em; text-transform: uppercase;
  color: #8CA196; font-weight: 500; border-bottom: 1px solid #2B3A33; padding: 7px 8px; }
.sv-table td { border-bottom: 1px solid #2B3A33; padding: 8px; vertical-align: top; }
.sv-table td.n { font-family: 'JetBrains Mono', monospace; text-align: right; white-space: nowrap; }
.sv-table tr.lead td { color: #B4D955; font-weight: 600; }
.sv-scroll { overflow-x: auto; }

/* Struggle cards */
.sv-card { border: 1px solid #2B3A33; border-left: 3px solid var(--c, #8CA196); border-radius: 12px; background: #121B17;
  padding: .85rem 1rem; margin-bottom: .7rem; }
.sv-card b { color: #F2EFE6; font-weight: 600; }
.sv-card p { font-size: 14px; color: #F2EFE6; line-height: 1.55; margin: .3rem 0 0; }
.sv-card .fig { font-family: 'JetBrains Mono', monospace; font-size: 13px; color: #B4D955; }

/* Cleaning tiles reuse the KPI tiles */
.sv-caveat { font-size: 13px; color: #8CA196; line-height: 1.55; margin-top: .6rem; }

/* Test explorer: real documents, re-scanned live */
.sv-doc { background: #0F1713 !important; color: #F2EFE6 !important; border: 1px solid #2B3A33; border-radius: 12px; padding: 1rem;
  font-family: 'JetBrains Mono', monospace; font-size: 13.5px; line-height: 1.65; white-space: pre-wrap; word-break: break-word; }
.sv-legend { color: #8CA196; font-size: 13px; }
[data-testid="stApp"]:has(.sv-vantage) [data-testid="stWidgetLabel"] p {
  color: #8CA196 !important; font-family: 'JetBrains Mono', monospace !important; font-size: 12px !important;
  letter-spacing: .12em; text-transform: uppercase; }
[data-testid="stApp"]:has(.sv-vantage) [data-testid="stSelectbox"] div {
  background-color: #0F1713 !important; color: #F2EFE6 !important; }
[data-testid="stApp"]:has(.sv-vantage) [data-testid="stSelectbox"] input { background: transparent !important; color: #F2EFE6 !important; }
[data-testid="stApp"]:has(.sv-vantage) [data-testid="stSelectbox"] [data-baseweb="select"] > div {
  background: #0F1713 !important; border: 1px solid #2B3A33 !important; border-radius: 10px !important; color: #F2EFE6 !important; }
[data-testid="stApp"]:has(.sv-vantage) [data-testid="stSelectbox"] [data-baseweb="select"] span,
[data-testid="stApp"]:has(.sv-vantage) [data-testid="stSelectbox"] [data-baseweb="select"] svg { color: #F2EFE6 !important; fill: #F2EFE6 !important; }
[data-testid="stApp"]:has(.sv-vantage) [data-testid="stSlider"] [data-testid="stThumbValue"] { color: #B4D955 !important; }
[data-testid="stApp"]:has(.sv-vantage) [data-testid="stExpander"] details { background: #18231E; border: 1px solid #2B3A33; border-radius: 14px; }
[data-testid="stApp"]:has(.sv-vantage) [data-testid="stExpander"] summary { background: #18231E !important; color: #F2EFE6 !important; }
[data-testid="stApp"]:has(.sv-vantage) [data-testid="stExpander"] summary p { color: #F2EFE6 !important; font-family: 'Inter', sans-serif; }
[data-testid="stApp"]:has(.sv-vantage) [data-testid="stExpander"] summary svg { color: #F2EFE6 !important; fill: #F2EFE6 !important; }
[data-testid="stApp"]:has(.sv-vantage) [data-testid="stExpanderDetails"] { background: #18231E; }
[data-testid="stApp"]:has(.sv-vantage) [data-testid="stTooltipIcon"] svg,
[data-testid="stApp"]:has(.sv-vantage) [data-testid="stTooltipHoverTarget"] svg { color: #8CA196 !important; fill: #8CA196 !important; }

@media (max-width: 900px) { .sv-kpis { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 640px) {
  [data-testid="stApp"]:has(.sv-vantage) .block-container { padding-top: 1.25rem; }
  .sv-vantage-h1 { font-size: 28px !important; }
  .sv-kpis { grid-template-columns: 1fr; }
}
</style>
"""


def inject_vantage_css() -> None:
    """Add the Vantage styles. Call once at the top of the Vantage page."""
    st.markdown(_VANTAGE_CSS, unsafe_allow_html=True)


def vantage_header(display_name: str, username: str) -> None:
    """Top bar with the product and workspace name, plus the signed-in user (real session)."""
    st.markdown(
        '<div class="sv-vantage"></div>'
        '<div class="sv-vantage-bar">'
        '<span class="sv-vantage-brand"><span class="sv-vantage-dot"></span>SIEVE // VANTAGE EVALUATION</span>'
        f'<span class="sv-vantage-user">{esc(display_name)} · {esc(username)}</span>'
        "</div>",
        unsafe_allow_html=True,
    )


def measured_banner(generated_at: str, model_version: str) -> str:
    """Says plainly that these are measured results from a dated report, not samples."""
    return (f'<div class="sv-measured" role="note"><span class="sv-measured-tag">MEASURED RESULTS</span>'
            f'<span class="sv-measured-text">Every figure on this page comes from the saved evaluation report '
            f"(model {esc(model_version)}, generated {esc(generated_at)}). No figure is illustrative or sample data.</span></div>")


def ring(value: float, caption: str) -> str:
    """Headline recall ring. ``value`` is a fraction from the report."""
    radius = 74
    circumference = 2 * 3.141592653589793 * radius
    shown = max(0.0, min(1.0, value))
    dash = shown * circumference
    return (
        '<div class="sv-hero">'
        '<div class="sv-ring-wrap">'
        '<svg viewBox="0 0 170 170" aria-hidden="true">'
        f'<circle cx="85" cy="85" r="{radius}" fill="none" stroke="#2B3A33" stroke-width="12"></circle>'
        f'<circle cx="85" cy="85" r="{radius}" fill="none" stroke="{LIME}" stroke-width="12" stroke-linecap="round" '
        f'stroke-dasharray="{dash:.2f} {circumference:.2f}"></circle>'
        "</svg>"
        f'<div class="sv-ring-value">{shown:.1%}<span>recall</span></div>'
        "</div>"
        f'<div class="sv-hero-cap">{esc(caption)}</div>'
        "</div>"
    )


def kpi_grid(items: list[tuple[str, str, str]]) -> str:
    """Four real figures. Each item is (label, formatted value, hint); all are escaped."""
    cells = "".join(
        f'<div class="sv-kpi"><div class="sv-kpi-label">{esc(label)}</div>'
        f'<div class="sv-kpi-value">{esc(value)}</div>'
        f'<div class="sv-kpi-hint">{esc(hint)}</div></div>'
        for label, value, hint in items
    )
    return f'<div class="sv-kpis">{cells}</div>'


def family_bars(rows: list[tuple[str, float]]) -> str:
    """Recall by attack family. Values are measured recall fractions from the report."""
    out = []
    for label, value in rows:
        pct = max(0.0, min(100.0, value * 100))
        cls = "low" if value < 0.7 else "mid" if value < 0.9 else ""
        colour = CORAL_TXT if value < 0.7 else AMBER if value < 0.9 else LIME
        out.append(
            '<div class="sv-fam">'
            f'<div class="sv-fam-head"><span>{esc(label)}</span><b class="{cls}">{value:.1%}</b></div>'
            f'<div class="sv-track"><div style="width:{pct:.1f}%;background:{colour}"></div></div>'
            "</div>"
        )
    return "".join(out)


def html_table(headers: list[str], rows: list[list[str]], lead_row: int | None = None) -> str:
    """Table with escaped cells. ``lead_row`` highlights the headline system."""
    head = "".join(f"<th>{esc(h)}</th>" for h in headers)
    body = []
    for i, row in enumerate(rows):
        cls = ' class="lead"' if lead_row == i else ""
        cells = "".join(f'<td class="n">{esc(c)}</td>' if j else f"<td>{esc(c)}</td>" for j, c in enumerate(row))
        body.append(f"<tr{cls}>{cells}</tr>")
    return f'<div class="sv-scroll"><table class="sv-table"><thead><tr>{head}</tr></thead><tbody>{"".join(body)}</tbody></table></div>'


def struggle_card(title: str, body_html: str, colour: str) -> str:
    """One finding. ``body_html`` is built only from escaped report values and fixed text in this module."""
    return f'<div class="sv-card" style="--c:{colour}"><b>{esc(title)}</b><p>{body_html}</p></div>'


def style_figure(fig, height: int, legend_y: float = -0.2) -> None:
    """Dark, transparent chart styling used across the page. Series and values are unchanged."""
    fig.update_layout(
        height=height, margin=dict(l=10, r=10, t=10, b=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", color=CREAM, size=13),
        legend=dict(orientation="h", y=legend_y, font=dict(color=CREAM)),
    )
    fig.update_xaxes(gridcolor=LINE, linecolor=LINE, zerolinecolor=LINE, tickfont=dict(color=SAGE))
    fig.update_yaxes(gridcolor=LINE, linecolor=LINE, zerolinecolor=LINE, tickfont=dict(color=SAGE))


def panel_label(text: str, extra: str = "") -> str:
    return f'<div class="sv-plabel">{esc(text)}{extra}</div>'
