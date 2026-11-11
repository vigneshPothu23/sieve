"""Aegis agent-firewall workspace: layout and styling helpers (Stage 4 of the SIEVE UI redesign).

Presentation only. Every tool call, decision, reason, rule ID and sandbox effect shown here comes
from the run that the existing agent and policy code produced. Styles are scoped with
``:has(.sv-aegis)``, so they apply only on the Aegis page. Every value is HTML-escaped.
"""
from __future__ import annotations

import streamlit as st

from sieve.policy import ALLOW, CONFIRM, DENY
from sieve.engine import ALLOW as V_ALLOW, BLOCK as V_BLOCK, REVIEW as V_REVIEW

from .theme import esc

SIM_LABEL = "SIMULATION MODE — RULE-BASED AGENT · IN-MEMORY SANDBOX"
TAINT_WORD = {V_ALLOW: "clean", V_REVIEW: "suspicious", V_BLOCK: "tainted"}

_AEGIS_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

[data-testid="stApp"]:has(.sv-aegis) { background: #121B17; }
[data-testid="stApp"]:has(.sv-aegis) header[data-testid="stHeader"] { background: transparent; }
[data-testid="stApp"]:has(.sv-aegis) .block-container { max-width: none; padding-top: 2.5rem; }
[data-testid="stApp"]:has(.sv-aegis) h1,
[data-testid="stApp"]:has(.sv-aegis) h2,
[data-testid="stApp"]:has(.sv-aegis) h3,
[data-testid="stApp"]:has(.sv-aegis) h4,
[data-testid="stApp"]:has(.sv-aegis) p,
[data-testid="stApp"]:has(.sv-aegis) label { font-family: 'Inter', system-ui, sans-serif; color: #F2EFE6; }
[data-testid="stApp"]:has(.sv-aegis) h4 { font-size: 15px !important; font-weight: 600 !important; margin: .2rem 0 .6rem !important; }
[data-testid="stApp"]:has(.sv-aegis) [data-testid="stCaptionContainer"] p,
[data-testid="stApp"]:has(.sv-aegis) .sv-note { color: #8CA196 !important; font-size: 13px; }

/* Sidebar: same navigation and sign-out, dark to match the page */
[data-testid="stApp"]:has(.sv-aegis) section[data-testid="stSidebar"] { background: #18231E; border-right: 1px solid #2B3A33; }
[data-testid="stApp"]:has(.sv-aegis) section[data-testid="stSidebar"] h2,
[data-testid="stApp"]:has(.sv-aegis) section[data-testid="stSidebar"] h3,
[data-testid="stApp"]:has(.sv-aegis) section[data-testid="stSidebar"] p { color: #F2EFE6; }
[data-testid="stApp"]:has(.sv-aegis) section[data-testid="stSidebar"] button {
  background: #121B17 !important; color: #F2EFE6 !important; border: 1px solid #2B3A33 !important; border-radius: 999px !important; }
[data-testid="stApp"]:has(.sv-aegis) section[data-testid="stSidebar"] button p { color: #F2EFE6 !important; }
[data-testid="stApp"]:has(.sv-aegis) section[data-testid="stSidebar"] button:hover { border-color: #B4D955 !important; }

/* Header bar */
.sv-aegis-bar { display: flex; justify-content: space-between; align-items: center; gap: 1rem; flex-wrap: wrap;
  border-bottom: 1px solid #2B3A33; padding: 0 0 .9rem; margin-bottom: 1.4rem;
  font-family: 'JetBrains Mono', monospace; font-size: 13px; letter-spacing: .08em; color: #F2EFE6; }
.sv-aegis-brand { display: flex; align-items: center; gap: 10px; font-weight: 500; }
.sv-aegis-dot { width: 9px; height: 9px; border-radius: 50%; background: #B4D955; display: inline-block; }
.sv-aegis-user { color: #8CA196; font-size: 13px; }
.sv-aegis-h1 { font-size: 34px !important; font-weight: 600 !important; letter-spacing: -.02em !important; margin: 0 0 .35rem !important; }
.sv-aegis-sub { color: #8CA196 !important; font-size: 15px; margin: 0 0 1.2rem !important; max-width: 72ch; }

/* Simulation disclosure: always visible, never implied to be live */
.sv-sim { display: flex; flex-wrap: wrap; gap: 6px 14px; align-items: center; border: 1px solid rgba(226, 180, 90, .55);
  background: rgba(226, 180, 90, .08); border-radius: 12px; padding: .75rem 1rem; margin: 0 0 1.4rem; }
.sv-sim-tag { font-family: 'JetBrains Mono', monospace; font-size: 12px; letter-spacing: .1em; font-weight: 500; color: #E2B45A; }
.sv-sim-text { color: #F2EFE6; font-size: 14px; line-height: 1.5; flex: 1 1 340px; }

/* Panels */
[data-testid="stApp"]:has(.sv-aegis) [class*="st-key-sv-panel"] {
  background: #18231E !important; border: 1px solid #2B3A33 !important; border-radius: 18px !important; padding: 1.3rem 1.2rem !important; }
.sv-plabel { font-family: 'JetBrains Mono', monospace; font-size: 12px; letter-spacing: .14em; text-transform: uppercase;
  color: #8CA196; display: flex; align-items: center; gap: 10px; flex-wrap: wrap; margin-bottom: .8rem; }
.sv-pill { font-family: 'JetBrains Mono', monospace; font-size: 11px; letter-spacing: .12em; text-transform: uppercase;
  padding: 4px 10px; border-radius: 999px; border: 1px solid #2B3A33; color: #8CA196; white-space: nowrap; }

/* Decision pills: allowed, denied, confirmation, no policy, approved */
.sv-dec { display: inline-flex; align-items: center; gap: 6px; font-family: 'JetBrains Mono', monospace; font-size: 11.5px;
  font-weight: 500; letter-spacing: .08em; text-transform: uppercase; padding: 5px 11px; border-radius: 999px; white-space: nowrap; border: 1px solid; }
.sv-dec.allow { color: #B4D955; border-color: rgba(180, 217, 85, .6); background: rgba(180, 217, 85, .1); }
.sv-dec.deny { color: #F3D9D4; border-color: #7D3B34; background: #7D3B34; }
.sv-dec.confirm { color: #E2B45A; border-color: rgba(226, 180, 90, .7); background: rgba(226, 180, 90, .08); border-style: dashed; }
.sv-dec.nopol { color: #8CA196; border-color: #2B3A33; background: transparent; }
.sv-dec.approved { color: #121B17; border-color: #B4D955; background: #B4D955; }

/* Action cards (one per proposed tool call) */
.sv-call { border: 1px solid #2B3A33; border-left: 4px solid var(--c, #2B3A33); border-radius: 12px; background: #121B17;
  padding: .8rem .95rem; margin-bottom: .7rem; }
.sv-call.deny { --c: #7D3B34; background: rgba(125, 59, 52, .16); }
.sv-call.confirm { --c: #E2B45A; background: rgba(226, 180, 90, .05); }
.sv-call.allow { --c: #B4D955; }
.sv-call.nopol { --c: #2B3A33; }
.sv-call-top { display: flex; justify-content: space-between; align-items: flex-start; gap: 10px; flex-wrap: wrap; }
.sv-call-name { font-family: 'JetBrains Mono', monospace; font-size: 14px; color: #F2EFE6; word-break: break-word; }
.sv-call-name .args { color: #8CA196; }
.sv-call-meta { font-size: 13px; color: #8CA196; margin-top: 6px; line-height: 1.5; }
.sv-call-why { font-size: 14px; color: #F2EFE6; margin-top: 6px; line-height: 1.5; }
.sv-call.deny .sv-call-why { color: #F3D9D4; }
.sv-call-rules { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }
.sv-rid { font-family: 'JetBrains Mono', monospace; font-size: 11px; border: 1px solid #2B3A33; border-radius: 6px; padding: 1px 7px; color: #8CA196; }

/* Column heads and taint */
.sv-col-title { font-size: 18px; font-weight: 600; color: #F2EFE6; margin: 0 0 .2rem; }
.sv-col-sub { font-size: 13.5px; color: #8CA196; line-height: 1.5; margin: 0 0 .9rem; }
.sv-tally { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: .9rem; }
.sv-taint { border: 1px solid #2B3A33; border-radius: 12px; padding: .75rem .9rem; margin-bottom: .9rem; background: #121B17; }
.sv-taint b { font-family: 'JetBrains Mono', monospace; font-weight: 500; font-size: 13px; letter-spacing: .06em; }
.sv-taint.BLOCK { border-color: rgba(232, 135, 123, .6); }
.sv-taint.BLOCK b { color: #E8877B; }
.sv-taint.REVIEW b { color: #E2B45A; }
.sv-taint.ALLOW b { color: #B4D955; }
.sv-taint p { font-size: 13.5px; color: #8CA196; margin: .35rem 0 0; line-height: 1.5; }

/* Sandbox results */
.sv-sandbox { border-top: 1px solid #2B3A33; margin-top: .6rem; padding-top: .8rem; }
.sv-sandbox ul { margin: .3rem 0 0 1rem; padding: 0; color: #F3D9D4; font-size: 14px; line-height: 1.6; }
.sv-clean { color: #B4D955; font-weight: 600; font-size: 14px; }

/* Policy explanations */
.sv-stop { border: 1px solid #2B3A33; border-radius: 12px; background: #121B17; padding: .8rem .95rem; margin-bottom: .6rem; }
.sv-stop-head { display: flex; justify-content: space-between; align-items: center; gap: 8px; flex-wrap: wrap;
  font-family: 'JetBrains Mono', monospace; font-size: 13px; color: #F2EFE6; margin-bottom: .4rem; }
.sv-stop ul { margin: .2rem 0 0 1rem; padding: 0; font-size: 14px; color: #F2EFE6; line-height: 1.55; }
.sv-rule { border-left: 3px solid #B4D955; background: #121B17; border-radius: 0 10px 10px 0; padding: .6rem .85rem; margin-bottom: .55rem; }
.sv-rule b { font-family: 'JetBrains Mono', monospace; font-size: 13px; color: #B4D955; font-weight: 500; }
.sv-rule p { font-size: 14px; color: #F2EFE6; margin: .25rem 0 0; line-height: 1.5; }

/* Buttons and controls */
[data-testid="stApp"]:has(.sv-aegis) [data-testid="stWidgetLabel"] p {
  color: #8CA196 !important; font-family: 'JetBrains Mono', monospace !important; font-size: 12px !important;
  letter-spacing: .12em; text-transform: uppercase; }
[data-testid="stApp"]:has(.sv-aegis) [data-testid="stTextArea"] textarea,
[data-testid="stApp"]:has(.sv-aegis) [data-testid="stTextInput"] input {
  background: #0F1713 !important; color: #F2EFE6 !important; border: 1px solid #2B3A33 !important; border-radius: 12px !important;
  font-family: 'JetBrains Mono', monospace !important; font-size: 13.5px !important; line-height: 1.55 !important; }
[data-testid="stApp"]:has(.sv-aegis) [data-testid="stTextArea"] textarea:focus { border-color: #B4D955 !important; box-shadow: none !important; }
[data-testid="stApp"]:has(.sv-aegis) [data-testid="stSelectbox"] div {
  background-color: #0F1713 !important; color: #F2EFE6 !important; }
[data-testid="stApp"]:has(.sv-aegis) [data-testid="stSelectbox"] input { background: transparent !important; color: #F2EFE6 !important; }
[data-testid="stApp"]:has(.sv-aegis) [data-testid="stSelectbox"] [data-baseweb="select"] > div {
  background: #0F1713 !important; border: 1px solid #2B3A33 !important; border-radius: 10px !important; color: #F2EFE6 !important; }
[data-testid="stApp"]:has(.sv-aegis) [data-testid="stSelectbox"] [data-baseweb="select"] span,
[data-testid="stApp"]:has(.sv-aegis) [data-testid="stSelectbox"] [data-baseweb="select"] svg { color: #F2EFE6 !important; fill: #F2EFE6 !important; }
[data-testid="stApp"]:has(.sv-aegis) [data-testid="stCheckbox"] [data-testid="stWidgetLabel"] p {
  text-transform: none !important; letter-spacing: 0 !important; font-family: 'Inter', sans-serif !important;
  font-size: 14px !important; color: #F2EFE6 !important; line-height: 1.45; }
[data-testid="stApp"]:has(.sv-aegis) [data-testid="stCheckbox"] label > div { background: #2B3A33 !important; }
[data-testid="stApp"]:has(.sv-aegis) [data-testid="stCheckbox"] input:checked + div { background: #B4D955 !important; }
.sv-aegis-req { font-size: 15px; color: #F2EFE6; margin: .2rem 0 .9rem; line-height: 1.5; }
[data-testid="stApp"]:has(.sv-aegis) [data-testid="stTooltipIcon"] svg,
[data-testid="stApp"]:has(.sv-aegis) [data-testid="stTooltipHoverTarget"] svg { color: #8CA196 !important; fill: #8CA196 !important; }
[data-testid="stApp"]:has(.sv-aegis) button[kind="primary"],
[data-testid="stApp"]:has(.sv-aegis) [data-testid="stBaseButton-primary"] {
  background: #B4D955 !important; color: #121B17 !important; border: none !important; border-radius: 12px !important;
  font-weight: 600 !important; box-shadow: 0 4px 0 #7E9C3A; min-height: 46px; }
[data-testid="stApp"]:has(.sv-aegis) button[kind="primary"] p,
[data-testid="stApp"]:has(.sv-aegis) [data-testid="stBaseButton-primary"] p { color: #121B17 !important; }
[data-testid="stApp"]:has(.sv-aegis) button[kind="primary"]:hover { background: #C3E36E !important; }
[data-testid="stApp"]:has(.sv-aegis) [data-testid="stExpander"] details { background: #18231E; border: 1px solid #2B3A33; border-radius: 14px; }
[data-testid="stApp"]:has(.sv-aegis) [data-testid="stExpander"] summary { background: #18231E !important; color: #F2EFE6 !important; }
[data-testid="stApp"]:has(.sv-aegis) [data-testid="stExpander"] summary p { color: #F2EFE6 !important; font-family: 'Inter', sans-serif; }
[data-testid="stApp"]:has(.sv-aegis) [data-testid="stExpander"] summary svg { color: #F2EFE6 !important; fill: #F2EFE6 !important; }
[data-testid="stApp"]:has(.sv-aegis) [data-testid="stExpanderDetails"] { background: #18231E; }
[data-testid="stApp"]:has(.sv-aegis) [data-testid="stAlert"] { background: #18231E; border: 1px solid #2B3A33; }

@media (max-width: 640px) {
  [data-testid="stApp"]:has(.sv-aegis) .block-container { padding-top: 1.25rem; }
  .sv-aegis-h1 { font-size: 28px !important; }
  .sv-call-top { flex-direction: column; }
}
</style>
"""


def inject_aegis_css() -> None:
    """Add the Aegis styles. Call once at the top of the Aegis page."""
    st.markdown(_AEGIS_CSS, unsafe_allow_html=True)


def aegis_header(display_name: str, username: str) -> None:
    """Top bar: product and workspace name, the simulation mode tag, and the signed-in user (real session)."""
    st.markdown(
        '<div class="sv-aegis"></div>'
        '<div class="sv-aegis-bar">'
        '<span class="sv-aegis-brand"><span class="sv-aegis-dot"></span>SIEVE // AEGIS FIREWALL</span>'
        f'<span class="sv-aegis-user">{esc(display_name)} · {esc(username)}</span>'
        "</div>",
        unsafe_allow_html=True,
    )


def sim_banner() -> str:
    """The simulation disclosure. Always shown; it states what is and is not real."""
    return (
        f'<div class="sv-sim" role="note"><span class="sv-sim-tag">{esc(SIM_LABEL)}</span>'
        '<span class="sv-sim-text">The agent is a rule-based stand-in, not a language model connected to any service. '
        "Every tool acts on an in-memory sandbox. No e-mail, network request, payment or deletion happens.</span></div>"
    )


def decision_pill(action: str, protected: bool, executed: bool) -> str:
    """Decision as one of four visible states. An unprotected run has no policy, so it is never labelled allowed."""
    if not protected:
        return '<span class="sv-dec nopol">No policy</span>'
    if action == ALLOW:
        return '<span class="sv-dec allow">✓ Allowed</span>'
    if action == DENY:
        return '<span class="sv-dec deny">✕ Denied</span>'
    if action == CONFIRM and executed:
        return '<span class="sv-dec approved">✓ Approved · ran</span>'
    return '<span class="sv-dec confirm">! Confirmation required</span>'


def _css_class(action: str, protected: bool, executed: bool) -> str:
    if not protected:
        return "nopol"
    if action == ALLOW:
        return "allow"
    if action == DENY:
        return "deny"
    return "allow" if executed else "confirm"


def call_card(record, protected: bool) -> str:
    """One proposed tool call: what it does, the decision, whether it ran, and the policy reasons."""
    call, dec = record.call, record.decision
    args = ", ".join(f"{k}={str(v)[:40]}" for k, v in call.args.items() if k not in ("body", "data"))
    name = f'<span>{esc(call.tool)}</span> <span class="args">({esc(args)})</span>' if args else f"<span>{esc(call.tool)}</span>"
    if record.executed:
        ran = '<span style="color:#B4D955">Ran in sandbox</span>'
    else:
        ran = '<span style="color:#8CA196">Did not run</span>'
    rules = "".join(f'<span class="sv-rid">{esc(r)}</span>' for r in dict.fromkeys(dec.rule_ids))
    rules_html = f'<div class="sv-call-rules">{rules}</div>' if rules else ""
    reason = dec.reasons[0] if dec.reasons else ""
    why = f'<div class="sv-call-why">{esc(reason)}</div>' if reason else ""
    error = f'<div class="sv-call-meta">Error: {esc(record.error)}</div>' if record.error else ""
    return (
        f'<div class="sv-call {_css_class(dec.action, protected, record.executed)}">'
        '<div class="sv-call-top">'
        f'<div class="sv-call-name">{name}</div>'
        f"{decision_pill(dec.action, protected, record.executed)}"
        "</div>"
        f'<div class="sv-call-meta">{ran} · from {esc(call.origin)}</div>'
        f"{why}{rules_html}{error}"
        "</div>"
    )


def tally(run) -> str:
    """Counts from the run's records: calls that ran, calls denied, calls waiting for confirmation."""
    ran = sum(1 for r in run.records if r.executed)
    denied = sum(1 for r in run.records if r.decision.action == DENY)
    waiting = sum(1 for r in run.records if r.decision.action == CONFIRM and not r.executed)
    chips = [f'<span class="sv-pill ok">{ran} ran</span>' if ran else '<span class="sv-pill">0 ran</span>']
    if denied:
        chips.append(f'<span class="sv-dec deny">{denied} denied</span>')
    if waiting:
        chips.append(f'<span class="sv-dec confirm">{waiting} waiting for approval</span>')
    return f'<div class="sv-tally">{"".join(chips)}</div>'


def taint_card(taint: str) -> str:
    """Session taint from the real session: the highest verdict of any document the session read."""
    word = TAINT_WORD.get(taint, taint)
    note = ("A flagged document was read. Outbound and destructive tools are locked for this session (P1)."
            if taint == V_BLOCK else "No flagged content has entered this session.")
    return (f'<div class="sv-taint {esc(taint)}"><span class="sv-note">Session taint</span><br>'
            f"<b>{esc(taint)} · {esc(word)}</b><p>{esc(note)}</p></div>")


def sandbox_block(world) -> str:
    """What the sandbox shows after the run. Only effects the sandbox recorded."""
    parts = ['<div class="sv-sandbox"><div class="sv-plabel" style="margin-bottom:.3rem">Sandbox after the run</div>']
    if world.damage:
        parts.append("<ul>" + "".join(f"<li>{esc(d)}</li>" for d in world.damage) + "</ul>")
    else:
        parts.append('<div class="sv-clean">No harmful side effects.</div>')
    if world.notes:
        parts.append(f'<div class="sv-note" style="margin-top:.5rem">Note saved for the user: {esc(world.notes[0])}</div>')
    parts.append("</div>")
    return "".join(parts)


def stop_card(record) -> str:
    """Policy explanation for a call that was denied or needed confirmation."""
    dec = record.decision
    items = "".join(f"<li>{esc(reason)}</li>" for reason in dict.fromkeys(dec.reasons))
    rules = " ".join(dict.fromkeys(dec.rule_ids))
    pill = decision_pill(dec.action, True, record.executed)
    return (f'<div class="sv-stop"><div class="sv-stop-head"><span>{esc(record.call.tool)}</span>{pill}</div>'
            f'<div class="sv-note">Rules: {esc(rules) or "–"}</div><ul>{items}</ul></div>')


def rule_card(rule_id: str, title: str, body: str) -> str:
    return f'<div class="sv-rule"><b>{esc(rule_id)} · {esc(title)}</b><p>{esc(body)}</p></div>'


def panel_label(text: str, extra: str = "") -> str:
    return f'<div class="sv-plabel">{esc(text)}{extra}</div>'
