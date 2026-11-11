"""Sieve — authenticated, role-restricted Streamlit entry point."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

st.set_page_config(
    page_title="Sieve · Secure Workspace",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="auto",  # expanded on desktop; collapsed on phones so the header Sign out is not covered
)

# Read optional Streamlit secrets and expose SIEVE_* settings to existing modules.
try:
    for key, value in st.secrets.items():
        if key.startswith("SIEVE_") and key not in os.environ:
            os.environ[key] = str(value)
except Exception:
    pass

from sieve.auth import (  # noqa: E402
    ROLE_DESCRIPTIONS,
    ROLE_LABELS,
    authenticate,
    change_password,
    create_user,
    get_audit_events,
    has_module_access,
    init_db,
    list_users,
    seed_users_from_secrets,
    set_user_active,
)
from ui.login import LOGIN_HEADER, inject_login_css, login_hero  # noqa: E402
from ui.nexus import account_card, audit_strip, inject_nexus_css, nexus_header, panel_label  # noqa: E402
from ui.session_bar import session_bar  # noqa: E402
from ui.theme import inject_css  # noqa: E402

inject_css()
init_db()

# Seed initial accounts only when the local database is empty.
try:
    seed_users_from_secrets(st.secrets.get("SIEVE_USERS", []))
except Exception as exc:
    st.error(f"Account setup needs attention: {exc}")
    st.stop()


def login_screen() -> None:
    inject_login_css()
    # Split layout: illustration left, sign-in form right. Streamlit stacks them on phones.
    hero_col, form_col = st.columns([1.6, 1], gap="large", vertical_alignment="center")
    with hero_col:
        login_hero()
    with form_col:
        st.markdown(LOGIN_HEADER, unsafe_allow_html=True)
        # Both fields start empty. Nothing about any account is shown before sign-in.
        with st.form("login_form", clear_on_submit=False, border=False):
            username = st.text_input("Username", autocomplete="username")
            password = st.text_input("Password", type="password", autocomplete="current-password")
            submitted = st.form_submit_button("Sign in", type="primary", use_container_width=True)
        if submitted:
            if not username.strip() or not password:
                st.error("Enter your username and password to continue.")
            else:
                user = authenticate(username, password)
                if user is None:
                    st.error("Incorrect username or password, or this account is inactive.")
                else:
                    st.session_state["sieve_user"] = user
                    st.rerun()


def password_change_screen(user: dict) -> None:
    st.title("Set your new password")
    st.info("For account security, you must replace your temporary password before continuing.")
    with st.form("first_password_change"):
        new_password = st.text_input("New password", type="password")
        confirm = st.text_input("Confirm new password", type="password")
        submitted = st.form_submit_button("Update password", type="primary")
    if submitted:
        if new_password != confirm:
            st.error("The passwords do not match.")
        else:
            try:
                change_password(user["username"], new_password)
                user["must_change_password"] = False
                st.session_state["sieve_user"] = user
                st.success("Password updated.")
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))


def admin_page() -> None:
    user = st.session_state["sieve_user"]
    inject_nexus_css()
    nexus_header(user["display_name"], user["username"])
    # Messages from the previous action survive the rerun that follows it.
    flash = st.session_state.pop("nexus_flash", None)
    if flash:
        st.success(flash)
    st.markdown(
        '<h1 class="sv-nexus-h1">Nexus</h1>'
        '<p class="sv-nexus-sub">Create accounts for the three operational workspaces. Each account receives one role.</p>',
        unsafe_allow_html=True,
    )

    # Nexus manages operational accounts only; the signed-in administrator is shown in the header.
    users = list_users()
    operational = [item for item in users if item["role"] != "admin"]

    left, right = st.columns([1.15, 1], gap="large")
    with left:
        with st.container(border=True, key="sv-panel-accounts"):
            st.markdown(
                panel_label("Operational accounts & assigned workspaces", '<span class="sv-pill">1 role / account</span>'),
                unsafe_allow_html=True,
            )
            if not operational:
                st.caption("No operational accounts yet. Create one on the right.")
            for item in operational:
                with st.container(border=True, key=f"sv-card-{item['id']}"):
                    info, action = st.columns([3, 1.6], vertical_alignment="center")
                    with info:
                        st.markdown(account_card(item), unsafe_allow_html=True)
                    with action:
                        target_active = not item["is_active"]
                        label = "Activate" if target_active else "Deactivate"
                        key_prefix = "act" if target_active else "deact"
                        if st.button(label, key=f"{key_prefix}-{item['id']}", width="stretch"):
                            try:
                                set_user_active(item["username"], target_active)
                                st.session_state["nexus_flash"] = f"{item['username']} updated."
                                st.rerun()
                            except Exception as exc:
                                st.error(str(exc))

            events = get_audit_events(2)
            if events:
                st.markdown(audit_strip(events), unsafe_allow_html=True)
            with st.expander("All audit events"):
                all_events = get_audit_events(100)
                st.dataframe(all_events, width="stretch", hide_index=True) if all_events else st.caption("No audit events yet.")

    with right:
        with st.container(border=True, key="sv-panel-create"):
            st.markdown(panel_label("Create operational account"), unsafe_allow_html=True)
            with st.form("create_user_form", clear_on_submit=True, border=False):
                username = st.text_input("New username")
                display_name = st.text_input("Display name")
                role = st.selectbox(
                    "Assign workspace role",
                    options=["inspect", "firewall", "evaluation"],
                    format_func=lambda value: f"{ROLE_LABELS[value]} — {ROLE_DESCRIPTIONS[value]}",
                )
                temporary_password = st.text_input("Temporary password (minimum 12 characters)", type="password")
                submitted = st.form_submit_button("+ Create account", type="primary", width="stretch")
            st.caption("The user must change the temporary password at first sign-in.")
            if submitted:
                try:
                    create_user(username, display_name, role, temporary_password)
                    st.session_state["nexus_flash"] = f"Account '{username}' created. The user must change the temporary password at first login."
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))


def main() -> None:
    user = st.session_state.get("sieve_user")
    if not user:
        login_screen()
        return

    if user.get("must_change_password"):
        password_change_screen(user)
        return

    role = user["role"]
    with st.sidebar:
        st.markdown("## SIEVE")

    # One global header for every authenticated workspace: identity + Sign out, visible without the sidebar.
    session_bar(user)

    if has_module_access(role, "user_management"):
        admin_page()
        return

    from ui import pages

    module_pages = []
    if has_module_access(role, "inspect"):
        module_pages.append(
            st.Page(pages.inspect_page, title="Prism", icon=":material/document_scanner:", url_path="inspect", default=True)
        )
    if has_module_access(role, "firewall"):
        module_pages.append(
            st.Page(pages.agent_page, title="Aegis", icon=":material/shield:", url_path="agent", default=True)
        )
    if has_module_access(role, "evaluation"):
        module_pages.append(
            st.Page(pages.evaluation_page, title="Vantage", icon=":material/monitoring:", url_path="evaluation", default=True)
        )

    if not module_pages:
        st.error("No workspace is assigned to this account. Contact the administrator.")
        return

    pages.sidebar()
    navigation = st.navigation(module_pages)
    navigation.run()


main()
