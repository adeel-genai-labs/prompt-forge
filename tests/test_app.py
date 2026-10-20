"""Smoke test for app.py using Streamlit's AppTest. The generator is mocked; no LLM is called."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

from src import generator
from src.schema import GeneratedPrompt
from src.targets import TARGETS

APP_PATH = str(Path(__file__).resolve().parent.parent / "app.py")


def test_app_generates_prompt_from_pasted_text(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    calls = []

    def fake_generate_prompt(content: str, goal: str = "", target: str = "coding_agent") -> GeneratedPrompt:
        calls.append({"content": content, "goal": goal, "target": target})
        return GeneratedPrompt(
            target=target,
            title="Rate-limit logins",
            sections={name: f"Text for {name}." for name in TARGETS[target]["required_sections"]},
            assumptions=["Flask 3"],
            final_prompt="You are working in a Flask app. Add rate limiting to /login.",
        )

    # app.py calls generator.generate_prompt through the module, so patching it here takes effect.
    monkeypatch.setattr(generator, "generate_prompt", fake_generate_prompt)

    at = AppTest.from_file(APP_PATH, default_timeout=30).run()
    assert not at.exception
    assert at.title[0].value == "PromptForge"

    at.text_input[0].input("Add login rate limiting")
    at.text_area[0].input("Meeting notes: users hammer /login. Contact ops@example.com.")
    at.form_submit_button[0].click().run()

    assert not at.exception
    assert not at.error
    assert at.code[0].value == "You are working in a Flask app. Add rate limiting to /login."
    assert at.subheader[0].value == "Rate-limit logins"
    assert calls == [
        {
            "content": "Meeting notes: users hammer /login. Contact [EMAIL].",
            "goal": "Add login rate limiting",
            "target": "coding_agent",
        }
    ]
