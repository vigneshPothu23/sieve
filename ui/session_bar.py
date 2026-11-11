"""Shared authenticated header: signed-in identity and one global Sign out action.

Rendered once by streamlit_app.py above every authenticated workspace (Nexus, Prism,
Aegis, Vantage), so Sign out is visible without opening the sidebar, on desktop and phones.
"""
from __future__ import annotations

import streamlit as st

from sieve.auth import ROLE_LABELS

SIGNOUT_KEY = "sv-signout"

# Selectors are scoped to a marker in this header and to kind="secondary" so they outrank the
# per-workspace button rules (Prism styles its secondary buttons with a scoped :has() selector).
_P = '[data-testid="stApp"]:has(.sv-signout-marker) .st-key-sv-signout button[kind="secondary"]'
_CSS = f"""
<style>
{_P} {{
    background-color: #A65B50 !important;
    border: 1px solid #C98B80 !important;
    border-radius: 8px !important;
    min-height: 44px;
    padding: 8px 16px !important;
    font-weight: 600 !important;
    box-shadow: none !important;
}}
{_P}, {_P} * {{
    color: #FFFFFF !important;
}}
{_P} svg {{
    fill: #FFFFFF !important;
}}
{_P}:hover {{
    background-color: #B56A5E !important;
    border-color: #DDA69C !important;
}}
{_P}:active {{
    background-color: #8C4A41 !important;
    border-color: #A8665B !important;
}}
{_P}:focus-visible {{
    outline: 3px solid #F2C4BA !important;
    outline-offset: 2px !important;
}}
</style>
<span class="sv-signout-marker"></span>
"""


def sign_out() -> None:
    """Clear the authenticated session and return to the sign-in screen.

    Removes the signed-in user and every other session value (Prism history and last result,
    Nexus flash messages, Aegis session state), so nothing from one account remains for the next.
    """
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()


def session_bar(user: dict) -> None:
    """Render the signed-in identity and the single Sign out button for the current workspace."""
    st.markdown(_CSS, unsafe_allow_html=True)
    left, right = st.columns([4, 1.2], vertical_alignment="center")
    with left:
        st.caption(f'Signed in as {user["display_name"]} · {ROLE_LABELS[user["role"]]}')
    with right:
        if st.button("Sign out", key=SIGNOUT_KEY, icon=":material/logout:", use_container_width=True):
            sign_out()
