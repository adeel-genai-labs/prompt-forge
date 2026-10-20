"""Input, content and output checks.

Each check returns None when everything is fine, or a friendly message
that the UI can show to the user as-is.
"""

from src.schema import GeneratedPrompt
from src.targets import TARGETS

MAX_FILE_BYTES = 10 * 1024 * 1024
# Anthropic rejects larger images, so enforce it for both providers to keep behaviour consistent.
MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_PDF_PAGES = 30
MAX_TEXT_CHARS = 50_000
ALLOWED_EXTENSIONS = {"txt", "md", "pdf", "docx", "png", "jpg", "jpeg", "webp"}
IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
BLOCKED_TOPICS = {
    "weapons": ["build a bomb", "make a gun", "explosive device"],
    "malware": ["ransomware", "keylogger", "write a virus"],
    "self-harm": ["kill myself", "self-harm", "suicide method"],
}
# Exact-phrase matching can't recognise every name; this catches the obvious cases.
IMAGE_BLOCKED_PHRASES = {
    "copyrighted characters": ["mickey mouse", "spider-man", "pikachu", "darth vader", "harry potter"],
    "brand logos": ["nike logo", "apple logo", "coca-cola logo", "mcdonald's logo"],
    "real people": ["photo of president", "photo of the prime minister", "taylor swift", "elon musk"],
}


def check_file(file_name: str, data: bytes) -> str | None:
    """Reject unsupported types, empty files, files over MAX_FILE_BYTES and images over MAX_IMAGE_BYTES."""
    raise NotImplementedError


def check_pdf_pages(data: bytes) -> str | None:
    """Reject PDFs that cannot be opened or have more than MAX_PDF_PAGES pages."""
    raise NotImplementedError


def check_content(text: str) -> str | None:
    """Reject extracted text that is empty or longer than MAX_TEXT_CHARS."""
    raise NotImplementedError


def check_blocked_topics(text: str) -> str | None:
    """Reject text that matches a keyword in BLOCKED_TOPICS, naming the topic in the message."""
    raise NotImplementedError


def redact_pii(text: str) -> tuple[str, dict[str, int]]:
    """Replace emails, phone numbers, card numbers and government IDs with tags like [EMAIL].

    Returns the redacted text and a count per tag. Runs on extracted content
    and again on the generated output.
    """
    raise NotImplementedError


def find_injection_attempts(text: str) -> list[str]:
    """Return phrases that look like attempts to instruct the model, e.g. 'ignore previous instructions'."""
    raise NotImplementedError


def wrap_as_data(text: str) -> str:
    """Wrap untrusted text in clear delimiters so the model treats it as data, not instructions."""
    raise NotImplementedError


def check_image_request(text: str) -> str | None:
    """For image_generation: reject requests that match IMAGE_BLOCKED_PHRASES, naming the category."""
    raise NotImplementedError


def check_output(prompt: GeneratedPrompt) -> str | None:
    """Reject a generated prompt that has an unknown target, a missing or empty required section
    for that target (from TARGETS), an empty final_prompt, or text that looks like a leaked secret."""
    raise NotImplementedError
