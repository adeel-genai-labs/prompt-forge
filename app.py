"""PromptForge Streamlit UI. Business logic lives in src/."""

import streamlit as st
from dotenv import load_dotenv
from streamlit.runtime.uploaded_file_manager import UploadedFile

from src.schema import GeneratedPrompt
from src.targets import TARGETS

load_dotenv()


def render_input() -> tuple[str, str, str, UploadedFile | None]:
    """Show the target selectbox (TARGETS labels), goal field, text box and file uploader.

    Returns (target_key, goal, pasted_text, uploaded_file). Text and a file may be
    given together; main() combines their content.
    """
    raise NotImplementedError


def render_result(prompt: GeneratedPrompt) -> None:
    """Show the title, each section, any assumptions, the final prompt in a copy-friendly
    code block, and the negative prompt when there is one."""
    raise NotImplementedError


def show_error(message: str) -> None:
    """Show a friendly guardrail or provider error."""
    st.error(message)


def main() -> None:
    """Wire the page together.

    input -> file checks -> extract (images described first) -> combine with pasted text
    -> content checks + blocked topics (+ image request check for image_generation) + redact PII
    -> generate for the chosen target -> output check (required sections) + redact PII -> result
    """
    raise NotImplementedError


if __name__ == "__main__":
    main()
