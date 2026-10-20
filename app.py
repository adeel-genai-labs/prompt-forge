"""PromptForge Streamlit UI. Business logic lives in src/."""

import streamlit as st
from dotenv import load_dotenv

from src.schema import GeneratedPrompt

load_dotenv()


def render_input() -> tuple[str, bytes] | str | None:
    """Show the text box and file uploader; return pasted text, (file_name, data), or None."""
    raise NotImplementedError


def render_result(prompt: GeneratedPrompt) -> None:
    """Show each prompt section and the final prompt with a copy-friendly code block."""
    raise NotImplementedError


def show_error(message: str) -> None:
    """Show a friendly guardrail or provider error."""
    st.error(message)


def main() -> None:
    """Wire the page together: input -> guardrails -> extract -> generate -> output check -> result."""
    raise NotImplementedError


if __name__ == "__main__":
    main()
