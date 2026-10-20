"""Smoke tests for app.py using Streamlit's AppTest. The generator is mocked; no LLM is called."""

from pathlib import Path
from types import SimpleNamespace

import pytest
from streamlit.testing.v1 import AppTest

from src import generator
from src.schema import GeneratedPrompt
from src.targets import TARGETS

APP_PATH = str(Path(__file__).resolve().parent.parent / "app.py")
FINAL_PROMPT = "Write a Databricks SQL query for monthly revenue by region..."
QUESTIONS = [
    {"question": "Revenue: gross or net?", "why": "Changes the metric.", "options": ["Gross", "Net"], "default": "Net"},
    {"question": "Time zone?", "why": "Shifts month boundaries.", "options": ["UTC", "Local"], "default": "UTC"},
    {"question": "Empty months?", "why": "Changes row count.", "options": ["Show as 0", "Omit"], "default": "Show as 0"},
]


@pytest.fixture
def fake(monkeypatch):
    """Mock the generator: queued clarifying questions, and a generate_prompt that records its calls."""
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.delenv("GROQ_TEXT_MODEL", raising=False)
    state = SimpleNamespace(questions=[], question_calls=[], generate_calls=[], final_prompt=FINAL_PROMPT)

    def fake_ask(goal: str, content: str, schema_text: str = "", target: str = "data_analytics") -> list[dict]:
        state.question_calls.append({"goal": goal, "content": content, "schema_text": schema_text})
        return state.questions

    def fake_generate(content, goal="", target="data_analytics", answers=None, schema_text=""):
        state.generate_calls.append(
            {"content": content, "goal": goal, "target": target, "answers": answers, "schema_text": schema_text}
        )
        return GeneratedPrompt(
            target=target,
            title="Monthly revenue by region",
            sections={name: f"Text for {name}." for name in TARGETS[target]["required_sections"]},
            assumptions=["Months are UTC calendar months"],
            final_prompt=state.final_prompt,
        )

    # app.py calls the generator through the module, so patching it here takes effect.
    monkeypatch.setattr(generator, "ask_clarifying_questions", fake_ask)
    monkeypatch.setattr(generator, "generate_prompt", fake_generate)
    return state


def fill(goal: str = "", schema: str = "", notes: str = "") -> AppTest:
    """Load the app and fill in the input form (not submitted)."""
    at = AppTest.from_file(APP_PATH, default_timeout=30).run()
    assert not at.exception
    at.text_input[0].input(goal)
    at.text_area[0].input(schema)
    at.text_area[1].input(notes)
    return at


def press(at: AppTest, key: str) -> AppTest:
    """Press a form button by key and rerun."""
    at.form_submit_button(key=key).click().run()
    assert not at.exception
    return at


# --- layout ---


def test_app_shows_branding_inputs_and_no_target_picker(fake):
    at = AppTest.from_file(APP_PATH, default_timeout=30).run()

    assert at.title[0].value == "PromptForge for Databricks"
    assert "without leaking personal data" in at.caption[0].value
    assert len(at.selectbox) == 0
    assert at.text_input[0].label == "What do you need?"
    assert [area.label for area in at.text_area] == ["Table schemas (optional)", "Notes or requirements (optional)"]
    assert any("Table: catalog.schema.table" in caption.value for caption in at.caption)
    assert [button.key for button in at.form_submit_button] == ["check", "skip"]
    sidebar_text = " ".join(item.value for item in at.sidebar.markdown)
    assert "groq" in sidebar_text and "openai/gpt-oss-120b" in sidebar_text


# --- skip flow ---


def test_skip_questions_generates_immediately(fake):
    fake.questions = QUESTIONS
    at = press(fill("Monthly revenue by region", notes="need a sales report, send to ops@example.com"), "skip")

    assert not at.error
    assert fake.question_calls == []
    assert at.code[0].value == FINAL_PROMPT
    assert any(item.value == "**Ready to paste into Genie Code (or any data agent)**" for item in at.markdown)
    assert fake.generate_calls == [
        {
            "content": "need a sales report, send to [EMAIL]",
            "goal": "Monthly revenue by region",
            "target": "data_analytics",
            "answers": [],
            "schema_text": "",
        }
    ]


# --- check flow ---


def test_check_shows_questions_with_defaults_preselected(fake):
    fake.questions = QUESTIONS
    at = press(fill("Monthly revenue by region"), "check")

    assert fake.generate_calls == []
    assert [radio.value for radio in at.radio] == ["Net", "UTC", "Show as 0"]
    assert [radio.options for radio in at.radio] == [["Gross", "Net"], ["UTC", "Local"], ["Show as 0", "Omit"]]
    assert len(at.code) == 0  # no result yet


def test_answers_are_passed_as_confirmed_or_default(fake):
    fake.questions = QUESTIONS
    at = press(fill("Monthly revenue by region"), "check")
    at.radio[0].set_value("Gross")  # changed -> confirmed
    at.text_input(key="other_1_2").input("Show empty months as NULL")  # typed -> confirmed
    at = press(at, "generate_1")  # question 2 left on default -> not confirmed

    assert at.code[0].value == FINAL_PROMPT
    assert fake.generate_calls[0]["answers"] == [
        {"question": "Revenue: gross or net?", "answer": "Gross", "confirmed": True},
        {"question": "Time zone?", "answer": "UTC", "confirmed": False},
        {"question": "Empty months?", "answer": "Show empty months as NULL", "confirmed": True},
    ]
    assert any("2 confirmed, 1 left on default" in item.value for item in at.markdown)


def test_reviewed_checkbox_is_shown_unchecked(fake):
    fake.questions = QUESTIONS
    at = press(fill("Monthly revenue by region"), "check")

    assert at.checkbox(key="reviewed_1").label == "I've reviewed these answers — treat them as confirmed"
    assert at.checkbox(key="reviewed_1").value is False


def test_unchecked_review_keeps_defaults_unconfirmed(fake):
    fake.questions = QUESTIONS
    at = press(fill("Monthly revenue by region"), "check")
    at = press(at, "generate_1")  # all left on default, box unchecked

    assert [answer["confirmed"] for answer in fake.generate_calls[0]["answers"]] == [False, False, False]
    assert any("0 confirmed, 3 left on default" in item.value for item in at.markdown)


def test_checked_review_confirms_answers_left_on_default(fake):
    fake.questions = QUESTIONS
    at = press(fill("Monthly revenue by region"), "check")
    at.radio[0].set_value("Gross")
    at.checkbox(key="reviewed_1").check()
    at = press(at, "generate_1")

    assert fake.generate_calls[0]["answers"] == [
        {"question": "Revenue: gross or net?", "answer": "Gross", "confirmed": True},
        {"question": "Time zone?", "answer": "UTC", "confirmed": True},
        {"question": "Empty months?", "answer": "Show as 0", "confirmed": True},
    ]
    assert any("3 confirmed, 0 left on default" in item.value for item in at.markdown)


def test_typed_other_answers_are_pii_redacted(fake):
    fake.questions = QUESTIONS[:1]
    at = press(fill("Monthly revenue by region"), "check")
    at.text_input(key="other_1_0").input("Net, ask jane@example.com")
    at = press(at, "generate_1")

    assert fake.generate_calls[0]["answers"][0]["answer"] == "Net, ask [EMAIL]"


def test_no_questions_goes_straight_to_generation(fake):
    fake.questions = []
    at = press(fill("Monthly revenue by region"), "check")

    assert len(fake.question_calls) == 1
    assert len(at.radio) == 0
    assert at.code[0].value == FINAL_PROMPT
    assert fake.generate_calls[0]["answers"] == []


def test_goal_is_required(fake):
    at = press(fill(notes="need a sales report"), "check")

    assert "What do you need?" in at.error[0].value
    assert fake.question_calls == [] and fake.generate_calls == []


# --- schemas ---


def test_schema_is_parsed_redacted_and_sent_compact(fake):
    schema = "Table: main.sales.orders\norder_id\tbigint\tkey\nowner\tstring\tcontact jane@example.com\n# Partition Information\norder_id\tbigint\t"
    at = press(fill("Monthly revenue by region", schema=schema), "skip")

    assert fake.generate_calls[0]["schema_text"] == "main.sales.orders: order_id bigint, owner string"
    report = " ".join(item.value for item in at.markdown)
    assert "EMAIL: 1" in report
    assert "**Schemas read:** main.sales.orders" in report


def test_unreadable_schema_is_sent_as_redacted_text_with_a_warning(fake):
    at = press(fill("Monthly revenue by region", schema="orders table, ask jane@example.com"), "skip")

    assert fake.generate_calls[0]["schema_text"] == "orders table, ask [EMAIL]"
    assert any("couldn't read any table columns" in warning.value for warning in at.warning)


def test_schema_text_goes_to_clarifying_questions(fake):
    fake.questions = []
    press(fill("Monthly revenue by region", schema="Table: main.sales.orders\norder_id  bigint"), "check")

    assert fake.question_calls[0]["schema_text"] == "main.sales.orders: order_id bigint"


# --- unverified table names ---


def test_warns_about_table_names_not_in_input(fake):
    fake.final_prompt = "SELECT region FROM main.sales.orders JOIN main.ref.fx_rates_daily f ON ..."
    at = press(fill("Monthly revenue by region", notes="Orders are in main.sales.orders"), "skip")

    assert [warning.value for warning in at.warning] == [
        "These table names weren't in your input. Verify them before use: `main.ref.fx_rates_daily`"
    ]
    assert at.code[0].value.startswith("SELECT region")  # warn, don't block


def test_schema_tables_count_as_verified(fake):
    fake.final_prompt = "SELECT region FROM main.sales.orders"
    schema = "CREATE TABLE main.sales.orders (order_id BIGINT, region STRING)"
    at = press(fill("Monthly revenue by region", schema=schema), "skip")

    assert not at.warning
