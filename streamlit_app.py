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
    initial_sidebar_state="expanded",
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
    st.title("Nexus")
    st.caption("Account and access management")
    st.markdown("Create accounts for the three operational workspaces. Each account receives one role.")
    with st.expander("Create a user account", expanded=True):
        with st.form("create_user_form", clear_on_submit=True):
            username = st.text_input("Username")
            display_name = st.text_input("Display name")
            role = st.selectbox(
                "Role",
                options=["inspect", "firewall", "evaluation"],
                format_func=lambda value: f"{ROLE_LABELS[value]} — {ROLE_DESCRIPTIONS[value]}",
            )
            temporary_password = st.text_input("Temporary password (minimum 12 characters)", type="password")
            submitted = st.form_submit_button("Create account", type="primary")
        if submitted:
            try:
                create_user(username, display_name, role, temporary_password)
                st.success(f"Account '{username}' created. The user must change the temporary password at first login.")
                st.rerun()
            except Exception as exc:
                st.error(str(exc))

    st.subheader("Accounts")
    users = list_users()
    if users:
        st.dataframe(
            [
                {
                    "Username": item["username"],
                    "Name": item["display_name"],
                    "Role": ROLE_LABELS.get(item["role"], item["role"]),
                    "Status": "Active" if item["is_active"] else "Inactive",
                    "Password change required": item["must_change_password"],
                    "Last login": item["last_login"] or "Never",
                }
                for item in users
            ],
            use_container_width=True,
            hide_index=True,
        )
        candidates = [item for item in users if item["username"] != user["username"]]
        if candidates:
            selected = st.selectbox("Manage account", candidates, format_func=lambda item: f'{item["username"]} · {ROLE_LABELS[item["role"]]}')
            if selected:
                target_active = not selected["is_active"]
                action = "Activate" if target_active else "Deactivate"
                if st.button(f"{action} {selected['username']}"):
                    try:
                        set_user_active(selected["username"], target_active)
                        st.success(f"{selected['username']} updated.")
                        st.rerun()
                    except Exception as exc:
                        st.error(str(exc))

    with st.expander("Recent audit events"):
        events = get_audit_events(100)
        st.dataframe(events, use_container_width=True, hide_index=True) if events else st.caption("No audit events yet.")


def logout() -> None:
    st.session_state.pop("sieve_user", None)
    st.rerun()


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
        st.caption(f'{user["display_name"]} · {ROLE_LABELS[role]}')
        st.divider()
        if st.button("Sign out", use_container_width=True):
            logout()

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
