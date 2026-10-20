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
from src.targets import DEFAULT_TARGET, TARGETS

PAGE_TITLE = "PromptForge for Databricks"
TAGLINE = "Turn vague data requests into safe, Databricks-ready prompts without leaking personal data."
UPLOAD_TYPES = sorted(guardrails.ALLOWED_EXTENSIONS)
GUARDRAILS_NOTE = (
    "Guardrails check file size and type, block unsafe topics, redact personal data before anything reaches "
    "the model, treat your content as data (not instructions), and check the output for missing sections and secrets."
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


def render_input() -> tuple[str, str, UploadedFile | None] | None:
    """Show the goal field, text box, file uploader and Generate button.

    Returns (goal, pasted_text, uploaded_file) when Generate is pressed, otherwise None.
    Any one of the three is enough; main() combines text and file content.
    """
    # A form stops Streamlit from rerunning the page on every keystroke.
    with st.form("input"):
        goal = st.text_input(
            "What is this prompt for?",
            max_chars=guardrails.MAX_GOAL_CHARS,
            placeholder="e.g. Monthly revenue by region for 2026",
        )
        pasted_text = st.text_area("Paste the data request or notes (optional)", height=200)
        uploaded_file = st.file_uploader("Or upload a file", type=UPLOAD_TYPES)
        submitted = st.form_submit_button("Generate", type="primary")

    if not submitted:
        return None
    return goal, pasted_text, uploaded_file


def run_pipeline(
    goal: str, pasted_text: str, uploaded_file: UploadedFile | None, target: str = DEFAULT_TARGET
) -> tuple[GeneratedPrompt, dict]:
    """Run the guardrails, extraction and generation steps; return the prompt and a guardrails report.

    Raises ValueError with a friendly message when a guardrail fails.
    """
    checks_passed = []
    parts = []

    if uploaded_file is not None:
        data = uploaded_file.getvalue()
        stop_if(guardrails.check_file(uploaded_file.name, data))
        if extractors.file_extension(uploaded_file.name) == "pdf":
            stop_if(guardrails.check_pdf_pages(data))
        checks_passed.append("File type, size and page count")
        parts.append(extractors.extract_file(uploaded_file.name, data))
    parts.append(extractors.extract_text(pasted_text))
    content = "\n\n".join(part for part in parts if part)

    # Goal-only input is allowed: the model then works from the goal and lists its assumptions.
    stop_if(guardrails.check_has_input(goal, content))
    if content:
        stop_if(guardrails.check_content(content))
    if goal.strip():
        stop_if(guardrails.check_content(goal, max_chars=guardrails.MAX_GOAL_CHARS))
    checks_passed.append("Content length")

    stop_if(guardrails.check_blocked_topics(f"{goal}\n{content}"))
    checks_passed.append("Blocked topics")

    redactions: Counter[str] = Counter()
    content, counts = guardrails.redact_pii(content)
    redactions.update(counts)
    goal, counts = guardrails.redact_pii(goal)
    redactions.update(counts)
    injection_warnings = guardrails.find_injection_attempts(content)

    with st.spinner("Generating your prompt..."):
        prompt = generator.generate_prompt(content, goal, target)

    # generate_prompt already retries until check_output passes, so this never changes the result;
    # it stays as a final safety check in case the generator changes.
    stop_if(guardrails.check_output(prompt))
    checks_passed.append("Output sections and secrets")
    prompt, counts = guardrails.redact_prompt(prompt)
    redactions.update(counts)

    report = {
        "redactions": dict(redactions),
        "injection_warnings": injection_warnings,
        "checks_passed": checks_passed,
    }
    return prompt, report


def stop_if(message: str | None) -> None:
    """Raise ValueError with a guardrail's friendly message, if it returned one."""
    if message:
        raise ValueError(message)


def render_report(report: dict) -> None:
    """Show redaction counts, injection warnings and passed checks in an expander."""
    if report["injection_warnings"]:
        phrases = ", ".join(f"'{phrase}'" for phrase in report["injection_warnings"])
        st.warning(f"Your content contains instruction-like text ({phrases}). It was treated as data, not followed.")

    with st.expander("Guardrails report"):
        if report["redactions"]:
            items = ", ".join(f"{tag}: {count}" for tag, count in sorted(report["redactions"].items()))
            st.markdown(f"**Personal data redacted:** {items}")
        else:
            st.markdown("**Personal data redacted:** none found")
        if report["injection_warnings"]:
            st.markdown("**Injection warnings:** " + ", ".join(report["injection_warnings"]))
        st.markdown("**Checks passed:**")
        st.markdown("\n".join(f"- {check}" for check in report["checks_passed"]))


def render_result(prompt: GeneratedPrompt) -> None:
    """Show the title, the final prompt in a copyable code block, assumptions, sections, and a Markdown download."""
    st.subheader(prompt.title)
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
    lines = [f"# {prompt.title}", "", f"Target: {TARGETS[prompt.target]['label']}", "", "## Final prompt", "", prompt.final_prompt]
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

    input -> file checks -> pdf pages -> extract -> combine with pasted text
    -> at least one of goal / content -> content checks (goal max 500) + blocked topics
    -> redact PII -> injection warnings -> generate
    -> output check (required sections, secrets) + redact PII -> result
    """
    st.set_page_config(page_title=PAGE_TITLE)
    load_settings()

    st.title(PAGE_TITLE)
    st.caption(TAGLINE)
    render_sidebar()

    request = render_input()
    if request is not None:
        try:
            st.session_state.result = run_pipeline(*request)
        except (ValueError, RuntimeError) as error:
            st.session_state.result = None
            show_error(str(error))
        except Exception:
            # Keep tracebacks out of the UI; log them to the terminal for debugging.
            logging.exception("Unexpected error while generating a prompt")
            st.session_state.result = None
            show_error("Something went wrong on our side. Please try again.")

    result = st.session_state.get("result")
    if result:
        prompt, report = result
        render_report(report)
        render_result(prompt)


if __name__ == "__main__":
    main()
