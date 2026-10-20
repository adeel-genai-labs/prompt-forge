"""Input, content and output checks.

Each check returns None when everything is fine, or a friendly message
that the UI can show to the user as-is.
"""

from src.schema import GeneratedPrompt

MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_TEXT_CHARS = 50_000
ALLOWED_EXTENSIONS = {"txt", "md", "pdf", "docx", "png", "jpg", "jpeg", "webp"}


def check_file(file_name: str, data: bytes) -> str | None:
    """Reject unsupported file types, empty files and files over MAX_FILE_BYTES."""
    raise NotImplementedError


def check_content(text: str) -> str | None:
    """Reject extracted text that is empty or longer than MAX_TEXT_CHARS."""
    raise NotImplementedError


def find_injection_attempts(text: str) -> list[str]:
    """Return phrases that look like attempts to instruct the model, e.g. 'ignore previous instructions'."""
    raise NotImplementedError


def wrap_as_data(text: str) -> str:
    """Wrap untrusted text in clear delimiters so the model treats it as data, not instructions."""
    raise NotImplementedError


def check_output(prompt: GeneratedPrompt) -> str | None:
    """Reject a generated prompt with empty fields or text that looks like a leaked secret."""
    raise NotImplementedError
