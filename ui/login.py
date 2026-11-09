"""Login screen layout and styling (Stage 1 of the SIEVE UI redesign).

The styles are scoped with ``:has(.sv-login)``, so they apply only while the
login screen is on the page. The workspaces keep the existing theme.
Palette and typography follow the approved design brief.
"""
from __future__ import annotations

from pathlib import Path

import streamlit as st

HERO_PATH = Path(__file__).resolve().parent / "assets" / "sieve-login-hero.png"
HERO_ALT = "SIEVE: read everything, trust nothing blindly. Illustration of a person scanning a document."

LOGIN_HEADER = (
    '<div class="sv-login">'
    '<span class="sv-login-pill">STEP 01 // SIGN IN</span>'
    '<h1 class="sv-login-title">Welcome back</h1>'
    '<p class="sv-login-sub">Routes directly to your assigned workspace.</p>'
    "</div>"
)

_LOGIN_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

[data-testid="stApp"]:has(.sv-login) { background: #121B17; }
[data-testid="stApp"]:has(.sv-login) header[data-testid="stHeader"] { background: transparent; }
[data-testid="stApp"]:has(.sv-login) .block-container { max-width: 1280px; padding-top: 4rem; }
[data-testid="stApp"]:has(.sv-login) h1,
[data-testid="stApp"]:has(.sv-login) p,
[data-testid="stApp"]:has(.sv-login) label { font-family: 'Inter', system-ui, sans-serif; }

.sv-login-pill {
  display: inline-block; font-family: 'JetBrains Mono', monospace; font-size: 12px; letter-spacing: .16em;
  color: #B4D955; border: 1px solid rgba(180, 217, 85, .45); border-radius: 999px; padding: 6px 14px;
}
.sv-login-title { color: #F2EFE6 !important; font-size: 42px !important; font-weight: 600 !important;
  letter-spacing: -.02em !important; line-height: 1.1 !important; margin: 1.1rem 0 .5rem !important; }
.sv-login-sub { color: #8CA196 !important; font-size: 16px; line-height: 1.55; margin: 0 0 1.6rem; max-width: 38ch; }

[data-testid="stApp"]:has(.sv-login) [data-testid="stImage"] img { border-radius: 14px; border: 1px solid #2B3A33; }

[data-testid="stApp"]:has(.sv-login) [data-testid="stForm"] { border: none; padding: 0; background: transparent; }
[data-testid="stApp"]:has(.sv-login) [data-testid="stWidgetLabel"] p {
  color: #8CA196 !important; font-family: 'JetBrains Mono', monospace !important; font-size: 12px !important;
  letter-spacing: .14em; text-transform: uppercase; }
[data-testid="stApp"]:has(.sv-login) [data-testid="stTextInput"] [data-baseweb="input"],
[data-testid="stApp"]:has(.sv-login) [data-testid="stTextInput"] div:has(> input) {
  background-color: #0F1713 !important; border: 1px solid #2B3A33 !important; border-radius: 10px !important; }
[data-testid="stApp"]:has(.sv-login) [data-testid="stTextInput"] [data-baseweb="input"]:focus-within {
  border-color: #B4D955 !important; box-shadow: none !important; }
[data-testid="stApp"]:has(.sv-login) [data-testid="stTextInput"] input {
  color: #F2EFE6 !important; font-family: 'JetBrains Mono', monospace !important; font-size: 15px;
  -webkit-text-fill-color: #F2EFE6; background: transparent !important; height: 48px; }
[data-testid="stApp"]:has(.sv-login) [data-testid="stTextInput"] button { color: #8CA196; }
[data-testid="stApp"]:has(.sv-login) [data-testid="stFormSubmitButton"] button {
  background: #B4D955; color: #121B17; border: none; border-radius: 12px; height: 52px;
  font-weight: 600; font-size: 16px; box-shadow: 0 4px 0 #7E9C3A; margin-top: .6rem; }
[data-testid="stApp"]:has(.sv-login) [data-testid="stFormSubmitButton"] button:hover { background: #C3E36E; color: #121B17; }
[data-testid="stApp"]:has(.sv-login) [data-testid="stFormSubmitButton"] button:focus-visible { outline: 2px solid #B4D955; outline-offset: 3px; }

@media (max-width: 640px) {
  [data-testid="stApp"]:has(.sv-login) .block-container { padding-top: 1.25rem; }
  .sv-login-title { font-size: 34px !important; }
}
</style>
"""


def inject_login_css() -> None:
    """Add the login styles. Call once at the top of the login screen."""
    st.markdown(_LOGIN_CSS, unsafe_allow_html=True)


def login_hero() -> None:
    """Show the approved illustration. Streamlit stacks it above the form on narrow screens."""
    st.image(str(HERO_PATH), use_container_width=True, alt=HERO_ALT)
