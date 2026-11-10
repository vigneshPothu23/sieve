"""Nexus administrator workspace: layout and styling helpers (Stage 2 of the SIEVE UI redesign).

Styles are scoped with ``:has(.sv-nexus)``, so they apply only on the Nexus page.
Prism, Aegis and Vantage keep the existing theme. Every value from the database
is HTML-escaped before it is shown.
"""
from __future__ import annotations

import streamlit as st

from sieve.auth import ROLE_DESCRIPTIONS, ROLE_LABELS
from .theme import esc

_NEXUS_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

[data-testid="stApp"]:has(.sv-nexus) { background: #121B17; }
[data-testid="stApp"]:has(.sv-nexus) header[data-testid="stHeader"] { background: transparent; }
[data-testid="stApp"]:has(.sv-nexus) .block-container { max-width: 1280px; padding-top: 2.5rem; }
[data-testid="stApp"]:has(.sv-nexus) h1,
[data-testid="stApp"]:has(.sv-nexus) h2,
[data-testid="stApp"]:has(.sv-nexus) h3,
[data-testid="stApp"]:has(.sv-nexus) p,
[data-testid="stApp"]:has(.sv-nexus) label { font-family: 'Inter', system-ui, sans-serif; color: #F2EFE6; }
[data-testid="stApp"]:has(.sv-nexus) [data-testid="stCaptionContainer"] p { color: #8CA196 !important; }

/* Sidebar: same navigation and sign-out, dark to match the page */
[data-testid="stApp"]:has(.sv-nexus) section[data-testid="stSidebar"] { background: #18231E; border-right: 1px solid #2B3A33; }
[data-testid="stApp"]:has(.sv-nexus) section[data-testid="stSidebar"] h2,
[data-testid="stApp"]:has(.sv-nexus) section[data-testid="stSidebar"] h3,
[data-testid="stApp"]:has(.sv-nexus) section[data-testid="stSidebar"] p { color: #F2EFE6; }

/* Header bar */
.sv-nexus-bar { display: flex; justify-content: space-between; align-items: center; gap: 1rem; flex-wrap: wrap;
  border-bottom: 1px solid #2B3A33; padding: 0 0 .9rem; margin-bottom: 1.8rem;
  font-family: 'JetBrains Mono', monospace; font-size: 13px; letter-spacing: .08em; color: #F2EFE6; }
.sv-nexus-brand { display: flex; align-items: center; gap: 10px; font-weight: 500; }
.sv-nexus-dot { width: 9px; height: 9px; border-radius: 50%; background: #B4D955; display: inline-block; }
.sv-nexus-user { color: #8CA196; font-size: 13px; }

.sv-nexus-h1 { font-size: 34px !important; font-weight: 600 !important; letter-spacing: -.02em !important;
  margin: 0 0 .35rem !important; color: #F2EFE6 !important; }
.sv-nexus-sub { color: #8CA196 !important; font-size: 15px; margin: 0 0 1.4rem !important; }

/* Panels and account cards (keyed containers from the page) */
[data-testid="stApp"]:has(.sv-nexus) [class*="st-key-sv-panel"] {
  background: #18231E !important; border: 1px solid #2B3A33 !important; border-radius: 18px !important; padding: 1.4rem 1.3rem !important; }
[data-testid="stApp"]:has(.sv-nexus) [class*="st-key-sv-card"] {
  background: #121B17 !important; border: 1px solid #2B3A33 !important; border-radius: 14px !important; margin-bottom: .8rem; }

/* Sidebar sign-out: readable on the dark sidebar */
[data-testid="stApp"]:has(.sv-nexus) section[data-testid="stSidebar"] button {
  background: #121B17 !important; color: #F2EFE6 !important; border: 1px solid #2B3A33 !important; border-radius: 999px !important; }
[data-testid="stApp"]:has(.sv-nexus) section[data-testid="stSidebar"] button p { color: #F2EFE6 !important; }
[data-testid="stApp"]:has(.sv-nexus) section[data-testid="stSidebar"] button:hover { border-color: #B4D955 !important; }

/* Role dropdown: dark, to match the text fields */
[data-testid="stApp"]:has(.sv-nexus) [data-testid="stSelectbox"] div {
  background-color: #0F1713 !important; color: #F2EFE6 !important; border-color: #2B3A33 !important; }
[data-testid="stApp"]:has(.sv-nexus) [data-testid="stSelectbox"] [data-baseweb="select"] {
  border: 1px solid #2B3A33 !important; border-radius: 10px !important; }
[data-testid="stApp"]:has(.sv-nexus) [data-testid="stSelectbox"] input { background: transparent !important; color: #F2EFE6 !important; }
[data-testid="stApp"]:has(.sv-nexus) [data-testid="stSelectbox"] [data-baseweb="select"] span,
[data-testid="stApp"]:has(.sv-nexus) [data-testid="stSelectbox"] [data-baseweb="select"] svg { color: #F2EFE6 !important; fill: #F2EFE6 !important; }

.sv-nexus-label { font-family: 'JetBrains Mono', monospace; font-size: 12px; letter-spacing: .14em; text-transform: uppercase;
  color: #8CA196; display: flex; align-items: center; gap: 10px; flex-wrap: wrap; margin-bottom: .6rem; }

.sv-acct-name { font-size: 17px; font-weight: 600; color: #F2EFE6; }
.sv-acct-user { font-family: 'JetBrains Mono', monospace; font-size: 13px; color: #8CA196; margin-top: 2px; }
.sv-acct-meta { font-size: 14px; color: #8CA196; margin-top: 6px; line-height: 1.5; }
.sv-acct-meta b { color: #F2EFE6; font-weight: 600; }
.sv-pills { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 10px; }
.sv-pill { font-family: 'JetBrains Mono', monospace; font-size: 11px; letter-spacing: .12em; text-transform: uppercase;
  padding: 4px 10px; border-radius: 999px; border: 1px solid #2B3A33; color: #8CA196; white-space: nowrap; }
.sv-pill.ok { color: #B4D955; border-color: rgba(180, 217, 85, .5); background: rgba(180, 217, 85, .08); }
.sv-pill.warn { color: #F2EFE6; background: #7D3B34; border-color: #7D3B34; }

.sv-audit { font-family: 'JetBrains Mono', monospace; font-size: 12.5px; color: #8CA196; line-height: 1.7;
  margin-top: .4rem; word-break: break-word; }
.sv-audit b { color: #F2EFE6; font-weight: 500; }

/* Account actions: Deactivate in coral, Activate in lime outline */
[data-testid="stApp"]:has(.sv-nexus) [class*="st-key-deact-"] button {
  background: #7D3B34 !important; color: #F2EFE6 !important; border: none !important; border-radius: 999px !important; font-weight: 600; }
[data-testid="stApp"]:has(.sv-nexus) [class*="st-key-act-"] button {
  background: transparent !important; color: #B4D955 !important; border: 1px solid #B4D955 !important;
  border-radius: 999px !important; font-weight: 600; }

/* Form fields and buttons: same treatment as the login screen */
[data-testid="stApp"]:has(.sv-nexus) [data-testid="stForm"] { border: none; padding: 0; background: transparent; }
[data-testid="stApp"]:has(.sv-nexus) [data-testid="stWidgetLabel"] p {
  color: #8CA196 !important; font-family: 'JetBrains Mono', monospace !important; font-size: 12px !important;
  letter-spacing: .14em; text-transform: uppercase; }
[data-testid="stApp"]:has(.sv-nexus) [data-testid="stTextInput"] [data-baseweb="input"],
[data-testid="stApp"]:has(.sv-nexus) [data-testid="stTextInput"] div:has(> input) {
  background-color: #0F1713 !important; border: 1px solid #2B3A33 !important; border-radius: 10px !important; }
[data-testid="stApp"]:has(.sv-nexus) [data-testid="stTextInput"] [data-baseweb="input"]:focus-within {
  border-color: #B4D955 !important; box-shadow: none !important; }
[data-testid="stApp"]:has(.sv-nexus) [data-testid="stTextInput"] input {
  color: #F2EFE6 !important; font-family: 'JetBrains Mono', monospace !important; font-size: 15px;
  -webkit-text-fill-color: #F2EFE6; background: transparent !important; }
[data-testid="stApp"]:has(.sv-nexus) [data-testid="stTextInput"] button { color: #8CA196; }
[data-testid="stApp"]:has(.sv-nexus) [data-testid="stSelectbox"] [data-baseweb="select"] > div {
  background: #0F1713 !important; border: 1px solid #2B3A33 !important; border-radius: 10px !important; color: #F2EFE6 !important; }
[data-testid="stApp"]:has(.sv-nexus) [data-testid="stFormSubmitButton"] button {
  background: #B4D955; color: #121B17; border: none; border-radius: 12px; height: 50px;
  font-weight: 600; font-size: 16px; box-shadow: 0 4px 0 #7E9C3A; width: 100%; }
[data-testid="stApp"]:has(.sv-nexus) [data-testid="stFormSubmitButton"] button:hover { background: #C3E36E; color: #121B17; }

[data-testid="stApp"]:has(.sv-nexus) [data-testid="stExpander"] details {
  background: #18231E; border: 1px solid #2B3A33; border-radius: 14px; }
[data-testid="stApp"]:has(.sv-nexus) [data-testid="stExpander"] summary p { color: #F2EFE6 !important; }

@media (max-width: 640px) {
  [data-testid="stApp"]:has(.sv-nexus) .block-container { padding-top: 1.25rem; }
  .sv-nexus-h1 { font-size: 28px !important; }
}
</style>
"""


def inject_nexus_css() -> None:
    """Add the Nexus styles. Call once at the top of the Nexus page."""
    st.markdown(_NEXUS_CSS, unsafe_allow_html=True)


def nexus_header(display_name: str, username: str) -> None:
    """Top bar: product and workspace name, plus the signed-in administrator (real session data)."""
    st.markdown(
        '<div class="sv-nexus"></div>'
        '<div class="sv-nexus-bar">'
        '<span class="sv-nexus-brand"><span class="sv-nexus-dot"></span>SIEVE // NEXUS ADMINISTRATOR</span>'
        f'<span class="sv-nexus-user">{esc(display_name)} · {esc(username)}</span>'
        "</div>",
        unsafe_allow_html=True,
    )


def panel_label(text: str, extra: str = "") -> str:
    """Uppercase mono label used at the top of each panel. ``extra`` is trusted HTML from this module only."""
    return f'<div class="sv-nexus-label">{esc(text)}{extra}</div>'


def account_card(item: dict) -> str:
    """Summary of one operational account, built only from the stored record."""
    role = item["role"]
    label = esc(ROLE_LABELS.get(role, role))
    description = esc(ROLE_DESCRIPTIONS.get(role, ""))
    status = '<span class="sv-pill ok">Active</span>' if item["is_active"] else '<span class="sv-pill">Inactive</span>'
    reset = '<span class="sv-pill warn">Password change due</span>' if item["must_change_password"] else ""
    last_login = esc(item["last_login"] or "Never")
    return (
        "<div>"
        f'<div class="sv-acct-name">{esc(item["display_name"])}</div>'
        f'<div class="sv-acct-user">{esc(item["username"])}</div>'
        f'<div class="sv-acct-meta">Workspace: <b>{label}</b> ({description})<br>Last login: {last_login}</div>'
        f'<div class="sv-pills">{status}{reset}</div>'
        "</div>"
    )


def audit_strip(events: list[dict]) -> str:
    """The latest audit events, read from the audit table."""
    rows = "".join(
        f'<div><b>{esc(e["created_at"])}</b> · {esc(e["event"])} · {esc(e["username"] or "—")}'
        + (f' — {esc(e["details"])}' if e.get("details") else "")
        + "</div>"
        for e in events
    )
    return panel_label("Recent local audit") + f'<div class="sv-audit">{rows}</div>'
