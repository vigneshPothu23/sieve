"""UI safety and end-to-end tests using Streamlit's AppTest harness (runs the real app script)."""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from sieve.engine import Scanner
from sieve.samples import SAMPLES
from ui.theme import render_document

APP = str(Path(__file__).resolve().parents[1] / "streamlit_app.py")


def test_render_document_escapes_html():
    r = Scanner().scan('Hello <script>alert(1)</script> <img src=x onerror="alert(2)"> world, a normal sentence here.')
    html = render_document(r)
    assert "<script>" not in html and "onerror=\"alert" not in html


@pytest.mark.parametrize("name,expect_flag", [
    ("Clean news article", False),
    ("Web page with a hidden instruction", True),
    ("Support e-mail with an exfiltration attempt", True),
    ("Tool output with zero-width obfuscation", True),
    ("Document with smuggled Unicode tag text", True),
    ("Recipe with imperative steps", False),
])
def test_sample_regressions(name, expect_flag):
    assert (Scanner().scan(SAMPLES[name]["text"]).verdict != "ALLOW") == expect_flag


def _app():
    at = AppTest.from_file(APP, default_timeout=60)
    at.run()
    assert not at.exception, at.exception
    return at


def test_inspect_workflow_end_to_end():
    at = _app()
    at.selectbox[0].select("Web page with a hidden instruction").run()
    at.button[0].click().run()
    assert not at.exception
    html = " ".join(m.value for m in at.markdown)
    assert "Blocked" in html
    doc = " ".join(str(e.proto) for e in at.get("html"))
    assert "sv-doc" in doc and "<a " not in doc   # attacker URLs must not become links
    assert any("<<DATA>>" in c.value for c in at.code)
    assert len(at.session_state["history"]) == 1


def test_inspect_clean_sample():
    at = _app()
    at.selectbox[0].select("Clean news article").run()
    at.button[0].click().run()
    assert "Allowed" in " ".join(m.value for m in at.markdown)


def _page_app(page: str) -> AppTest:
    def script(page_name):
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path.cwd()))
        from ui import pages
        from ui.theme import inject_css
        inject_css()
        getattr(pages, page_name)()

    at = AppTest.from_function(script, args=(page,), default_timeout=60)
    at.run()
    assert not at.exception, at.exception
    return at


def test_agent_page_runs_both_agents():
    at = _page_app("agent_page")
    at.button[0].click().run()
    assert not at.exception
    text = " ".join(m.value for m in at.markdown)
    assert "Without Sieve" in text and "With Sieve" in text
    assert "No harmful side effects." in text          # protected run
    assert "sv-damage" in text                          # unprotected run shows damage


@pytest.mark.parametrize("page", ["evaluation_page", "about_page"])
def test_static_pages_render(page):
    _page_app(page)
