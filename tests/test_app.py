"""Smoke tests for app.py using Streamlit's AppTest. The generator is mocked; no LLM is called."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from src import generator
from src.schema import GeneratedPrompt
from src.targets import TARGETS

APP_PATH = str(Path(__file__).resolve().parent.parent / "app.py")
FINAL_PROMPT = "Write a Databricks SQL query for monthly revenue by region..."


@pytest.fixture
def generate_calls(monkeypatch):
    """Mock generator.generate_prompt and return the list of calls it receives."""
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.delenv("GROQ_TEXT_MODEL", raising=False)
    calls = []

    def fake_generate_prompt(content: str, goal: str = "", target: str = "data_analytics") -> GeneratedPrompt:
        calls.append({"content": content, "goal": goal, "target": target})
        return GeneratedPrompt(
            target=target,
            title="Monthly revenue by region",
            sections={name: f"Text for {name}." for name in TARGETS[target]["required_sections"]},
            assumptions=["Months are UTC calendar months"],
            final_prompt=FINAL_PROMPT,
        )

    # app.py calls generator.generate_prompt through the module, so patching it here takes effect.
    monkeypatch.setattr(generator, "generate_prompt", fake_generate_prompt)
    return calls


def submit(goal: str = "", pasted_text: str = "") -> AppTest:
    """Load the app, fill in the form and press Generate."""
    at = AppTest.from_file(APP_PATH, default_timeout=30).run()
    assert not at.exception
    at.text_input[0].input(goal)
    at.text_area[0].input(pasted_text)
    at.form_submit_button[0].click().run()
    assert not at.exception
    return at


def test_app_shows_databricks_branding_and_no_target_picker(generate_calls):
    at = AppTest.from_file(APP_PATH, default_timeout=30).run()

    assert at.title[0].value == "PromptForge for Databricks"
    assert "without leaking personal data" in at.caption[0].value
    assert len(at.selectbox) == 0
    sidebar_text = " ".join(item.value for item in at.sidebar.markdown)
    assert "groq" in sidebar_text and "llama-3.3-70b-versatile" in sidebar_text


def test_app_generates_prompt_from_pasted_text(generate_calls):
    at = submit("Monthly revenue by region", "need a sales report, send to ops@example.com")

    assert not at.error
    assert at.code[0].value == FINAL_PROMPT
    assert at.subheader[0].value == "Monthly revenue by region"
    assert generate_calls == [
        {
            "content": "need a sales report, send to [EMAIL]",
            "goal": "Monthly revenue by region",
            "target": "data_analytics",
        }
    ]


def test_app_generates_prompt_from_goal_only(generate_calls):
    at = submit(goal="Weekly active users by country")

    assert not at.error
    assert at.subheader[0].value == "Monthly revenue by region"
    assert generate_calls == [{"content": "", "goal": "Weekly active users by country", "target": "data_analytics"}]


def test_app_asks_for_input_when_everything_is_empty(generate_calls):
    at = submit()

    assert "describe what the prompt is for" in at.error[0].value
    assert generate_calls == []
