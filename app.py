"""PromptForge for Databricks: Streamlit UI. Business logic lives in src/."""

import logging
import os
import re
from collections import Counter

import streamlit as st
from dotenv import load_dotenv
from streamlit.runtime.uploaded_file_manager import UploadedFile

from src import extractors, generator, guardrails
from src.schema import GeneratedPrompt
from src.schema_input import format_schemas, parse_schemas
from src.targets import DEFAULT_TARGET, TARGETS

PAGE_TITLE = "PromptForge for Databricks"
TAGLINE = "Turn vague data requests into safe, Databricks-ready prompts without leaking personal data."
RESULT_LABEL = "Ready to paste into Genie Code (or any data agent)"
REVIEWED_LABEL = "I've reviewed these answers — treat them as confirmed"
UPLOAD_TYPES = sorted(guardrails.ALLOWED_EXTENSIONS)
GUARDRAILS_NOTE = (
    "Guardrails check file size and type, block unsafe topics, redact personal data before anything reaches "
    "the model, treat your content as data (not instructions), and check the output for missing sections and secrets."
)
SCHEMA_EXAMPLE = """Table: main.sales.orders
order_id     bigint
customer_id  string
order_ts     timestamp
amount       decimal(18,2)"""
SCHEMA_WARNING = (
    "We couldn't read any table columns from the schema field, so it was sent as plain text. "
    "Check the format: a 'Table: catalog.schema.table' line, then DESCRIBE TABLE output or CREATE TABLE."
)


def load_settings() -> None:
    """Load .env locally, and copy Streamlit secrets into os.environ when deployed."""
    load_dotenv()
    try:
        for key, value in st.secrets.items():
            if isinstance(value, str):
                os.environ.setdefault(key, value)
    except Exception:  # no secrets.toml locally; Streamlit raises different types for this across versions
        pass


def render_sidebar() -> None:
    """Show the current provider and model, and a one-line note on what guardrails do."""
    with st.sidebar:
        st.header("Settings")
        try:
            provider = generator.get_provider()
        except ValueError as error:
            st.error(str(error))
        else:
            st.markdown(f"**Provider:** `{provider}`")
            st.markdown(f"**Model:** `{generator.model_for(provider)}`")
        st.caption(GUARDRAILS_NOTE)


def render_input() -> tuple[str, str, str, str, UploadedFile | None] | None:
    """Show the request, schema and notes fields with "Check my request" and "Skip questions" buttons.

    Returns (action, goal, schema_text, notes, uploaded_file) when a button is pressed, otherwise None.
    action is "check" or "skip".
    """
    # A form stops Streamlit from rerunning the page on every keystroke.
    with st.form("input"):
        goal = st.text_input(
            "What do you need?",
            max_chars=guardrails.MAX_GOAL_CHARS,
            placeholder="e.g. Monthly revenue by region for the last 12 months",
        )
        schema_text = st.text_area("Table schemas (optional)", height=160, placeholder=SCHEMA_EXAMPLE)
        st.caption(
            "One block per table: a `Table: catalog.schema.table` line, then DESCRIBE TABLE output "
            "or a CREATE TABLE statement. Example: `Table: main.sales.orders` followed by `order_id  bigint`."
        )
        notes = st.text_area("Notes or requirements (optional)", height=120)
        uploaded_file = st.file_uploader("Or upload notes", type=UPLOAD_TYPES)
        check = st.form_submit_button("Check my request", type="primary", key="check")
        skip = st.form_submit_button("Skip questions", key="skip")

    if not (check or skip):
        return None
    return ("check" if check else "skip"), goal, schema_text, notes, uploaded_file


def prepare_request(goal: str, schema_text: str, notes: str, uploaded_file: UploadedFile | None) -> dict:
    """Run the input guardrails, extract and redact text, and parse schemas; return what generation needs.

    Raises ValueError with a friendly message when a guardrail fails.
    """
    checks_passed = []
    stop_if(guardrails.check_goal(goal))
    stop_if(guardrails.check_content(goal, max_chars=guardrails.MAX_GOAL_CHARS))

    parts = []
    if uploaded_file is not None:
        data = uploaded_file.getvalue()
        stop_if(guardrails.check_file(uploaded_file.name, data))
        if extractors.file_extension(uploaded_file.name) == "pdf":
            stop_if(guardrails.check_pdf_pages(data))
        checks_passed.append("File type, size and page count")
        parts.append(extractors.extract_file(uploaded_file.name, data))
    parts.append(extractors.extract_text(notes))
    content = "\n\n".join(part for part in parts if part)
    # Not whitespace-normalised: tabs separate the columns in DESCRIBE output.
    schema_text = schema_text.strip()

    for text in (content, schema_text):
        if text:
            stop_if(guardrails.check_content(text))
    checks_passed.append("Content length")
    stop_if(guardrails.check_blocked_topics(f"{goal}\n{content}\n{schema_text}"))
    checks_passed.append("Blocked topics")

    redactions: Counter[str] = Counter()
    goal, counts = guardrails.redact_pii(goal)
    redactions.update(counts)
    content, counts = guardrails.redact_pii(content)
    redactions.update(counts)
    schema_text, counts = guardrails.redact_pii(schema_text)
    redactions.update(counts)

    schemas = parse_schemas(schema_text)
    return {
        "goal": goal,
        "content": content,
        # Parsed schemas go to the model as a compact block; unreadable schema text is sent as-is.
        "schema_text": format_schemas(schemas) if schemas else schema_text,
        "schema_tables": list(schemas),
        "schema_warning": SCHEMA_WARNING if schema_text and not schemas else "",
        "input_text": f"{goal}\n{content}\n{schema_text}",
        "redactions": dict(redactions),
        "injection_warnings": guardrails.find_injection_attempts(f"{content}\n{schema_text}"),
        "checks_passed": checks_passed,
    }


def render_questions(questions: list[dict], form_id: int) -> list[dict] | None:
    """Show each question with radio options (default preselected) and an optional "Other" answer.

    Returns the answers when "Generate prompt" is pressed, otherwise None.
    """
    st.subheader("A few questions before generating")
    with st.form(f"questions_{form_id}"):
        choices = []
        for index, question in enumerate(questions):
            st.markdown(f"**{question['question']}**")
            st.caption(question["why"])
            choice = st.radio(
                question["question"],
                question["options"],
                index=question["options"].index(question["default"]),
                key=f"choice_{form_id}_{index}",
                label_visibility="collapsed",
            )
            other = st.text_input("Other (optional)", key=f"other_{form_id}_{index}")
            choices.append((choice, other))
        reviewed = st.checkbox(REVIEWED_LABEL, value=False, key=f"reviewed_{form_id}")
        submitted = st.form_submit_button("Generate prompt", type="primary", key=f"generate_{form_id}")

    if not submitted:
        return None
    return [to_answer(question, choice, other, reviewed) for question, (choice, other) in zip(questions, choices)]


def to_answer(question: dict, choice: str, other: str, reviewed: bool = False) -> dict:
    """Return an answer dict. It counts as confirmed when the user typed "Other", changed the default,
    or ticked the "reviewed" box (which confirms answers left on the default too)."""
    other = other.strip()
    answer = other or choice
    confirmed = reviewed or bool(other) or choice != question["default"]
    return {"question": question["question"], "answer": answer, "confirmed": confirmed}


def finish_request(request: dict, answers: list[dict] | None, target: str = DEFAULT_TARGET) -> tuple[GeneratedPrompt, dict]:
    """Generate the prompt from a prepared request and answers; run the output checks; return prompt and report.

    Raises ValueError with a friendly message when a guardrail fails.
    """
    redactions = Counter(request["redactions"])
    checks_passed = list(request["checks_passed"])
    answers = answers or []
    # Typed "Other" answers are user input like the goal: same topic check and redaction.
    for answer in answers:
        stop_if(guardrails.check_blocked_topics(answer["answer"]))
        answer["answer"], counts = guardrails.redact_pii(answer["answer"])
        redactions.update(counts)

    with st.spinner("Generating your prompt..."):
        prompt = generator.generate_prompt(
            request["content"], request["goal"], target, answers=answers, schema_text=request["schema_text"]
        )

    # generate_prompt already retries until check_output passes, so this never changes the result;
    # it stays as a final safety check in case the generator changes.
    stop_if(guardrails.check_output(prompt))
    checks_passed.append("Output sections and secrets")
    prompt, counts = guardrails.redact_prompt(prompt)
    redactions.update(counts)

    report = {
        "redactions": dict(redactions),
        "injection_warnings": request["injection_warnings"],
        "unverified_names": guardrails.find_unverified_names(prompt, request["input_text"], request["schema_tables"]),
        "schema_warning": request["schema_warning"],
        "schema_tables": request["schema_tables"],
        "confirmed_answers": sum(answer["confirmed"] for answer in answers),
        "default_answers": sum(not answer["confirmed"] for answer in answers),
        "checks_passed": checks_passed,
    }
    return prompt, report


def stop_if(message: str | None) -> None:
    """Raise ValueError with a guardrail's friendly message, if it returned one."""
    if message:
        raise ValueError(message)


def run_safely(step, *args):
    """Run a step, showing friendly errors instead of tracebacks; return its result, or None if it failed."""
    try:
        return step(*args)
    except (ValueError, RuntimeError) as error:
        show_error(str(error))
    except Exception:
        # Keep tracebacks out of the UI; log them to the terminal for debugging.
        logging.exception("Unexpected error in %s", getattr(step, "__name__", step))
        show_error("Something went wrong on our side. Please try again.")
    return None


def check_request(request: dict) -> list[dict]:
    """Ask the clarifying questions for a prepared request."""
    with st.spinner("Checking your request..."):
        return generator.ask_clarifying_questions(request["goal"], request["content"], request["schema_text"])


def render_report(report: dict) -> None:
    """Show warnings (injection-like text, unverified table names, unreadable schema), then the guardrails report."""
    if report["injection_warnings"]:
        phrases = ", ".join(f"'{phrase}'" for phrase in report["injection_warnings"])
        st.warning(f"Your content contains instruction-like text ({phrases}). It was treated as data, not followed.")
    if report["unverified_names"]:
        names = ", ".join(f"`{name}`" for name in report["unverified_names"])
        st.warning(f"These table names weren't in your input. Verify them before use: {names}")
    if report["schema_warning"]:
        st.warning(report["schema_warning"])

    with st.expander("Guardrails report"):
        if report["redactions"]:
            items = ", ".join(f"{tag}: {count}" for tag, count in sorted(report["redactions"].items()))
            st.markdown(f"**Personal data redacted:** {items}")
        else:
            st.markdown("**Personal data redacted:** none found")
        if report["schema_tables"]:
            st.markdown("**Schemas read:** " + ", ".join(report["schema_tables"]))
        if report["confirmed_answers"] or report["default_answers"]:
            st.markdown(
                f"**Questions:** {report['confirmed_answers']} confirmed, "
                f"{report['default_answers']} left on default (listed in assumptions)"
            )
        if report["injection_warnings"]:
            st.markdown("**Injection warnings:** " + ", ".join(report["injection_warnings"]))
        st.markdown("**Checks passed:**")
        st.markdown("\n".join(f"- {check}" for check in report["checks_passed"]))


def render_result(prompt: GeneratedPrompt) -> None:
    """Show the title, the final prompt in a copyable code block, assumptions, sections, and a Markdown download."""
    st.subheader(prompt.title)
    st.markdown(f"**{RESULT_LABEL}**")
    st.code(prompt.final_prompt, language="markdown", wrap_lines=True)

    if prompt.assumptions:
        st.markdown("**Assumptions**")
        st.markdown("\n".join(f"- {item}" for item in prompt.assumptions))

    with st.expander("Sections"):
        for name, text in prompt.sections.items():
            st.markdown(f"**{name}**")
            st.markdown(text)

    st.download_button(
        "Download as Markdown",
        data=to_markdown(prompt),
        file_name=f"{slugify(prompt.title)}.md",
        mime="text/markdown",
    )


def to_markdown(prompt: GeneratedPrompt) -> str:
    """Return the whole prompt as a Markdown document for download."""
    lines = [f"# {prompt.title}", "", f"Target: {TARGETS[prompt.target]['label']}", "", f"## {RESULT_LABEL}", "", prompt.final_prompt]
    for name, text in prompt.sections.items():
        lines += ["", f"## {name}", "", text]
    if prompt.assumptions:
        lines += ["", "## Assumptions", ""] + [f"- {item}" for item in prompt.assumptions]
    return "\n".join(lines) + "\n"


def slugify(text: str) -> str:
    """Return a safe file name stem, e.g. 'Monthly revenue by region!' -> 'monthly-revenue-by-region'."""
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "prompt"


def show_error(message: str) -> None:
    """Show a friendly guardrail or provider error."""
    st.error(message)


def main() -> None:
    """Wire the page together.

    Step 1 "Check my request": input guardrails -> redact PII -> parse schemas -> clarifying questions
    (none -> straight to step 2). Step 2 "Generate prompt": answers -> generate -> output check
    + redact PII -> unverified table names (warning) -> result. "Skip questions" goes straight to step 2.
    """
    st.set_page_config(page_title=PAGE_TITLE)
    load_settings()

    st.title(PAGE_TITLE)
    st.caption(TAGLINE)
    render_sidebar()
    state = st.session_state

    submitted = render_input()
    if submitted is not None:
        action, *fields = submitted
        state.result, state.questions = None, None
        state.request = run_safely(prepare_request, *fields)
        if state.request and action == "check":
            questions = run_safely(check_request, state.request)
            if questions:
                state.questions = questions
                state.questions_id = state.get("questions_id", 0) + 1
            elif questions is not None:
                state.result = run_safely(finish_request, state.request, [])
        elif state.request:
            state.result = run_safely(finish_request, state.request, None)

    if state.get("questions"):
        answers = render_questions(state.questions, state.questions_id)
        if answers is not None:
            state.result = run_safely(finish_request, state.request, answers)

    if state.get("result"):
        prompt, report = state.result
        render_report(report)
        render_result(prompt)


if __name__ == "__main__":
    main()
