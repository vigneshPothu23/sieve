"""Sieve — explainable firewall for untrusted content entering LLM applications.

Run locally:  streamlit run streamlit_app.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

st.set_page_config(page_title="Sieve · untrusted content firewall", page_icon="🛡️", layout="wide",
                   initial_sidebar_state="auto")

# Streamlit secrets (optional) are mirrored into env vars so sieve.config sees them.
try:
    for k, v in st.secrets.items():
        if k.startswith("SIEVE_") and k not in os.environ:
            os.environ[k] = str(v)
except Exception:
    pass  # no secrets file — defaults are used

from ui import pages  # noqa: E402
from ui.theme import inject_css  # noqa: E402

inject_css()

nav = st.navigation([
    st.Page(pages.inspect_page, title="Inspect content", icon=":material/document_scanner:", url_path="inspect", default=True),
    st.Page(pages.agent_page, title="Agent firewall", icon=":material/shield:", url_path="agent"),
    st.Page(pages.evaluation_page, title="Evaluation", icon=":material/monitoring:", url_path="evaluation"),
    st.Page(pages.about_page, title="How it works", icon=":material/info:", url_path="about"),
])
pages.sidebar()
nav.run()
