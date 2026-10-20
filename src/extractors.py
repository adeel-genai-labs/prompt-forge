"""Turn each supported input type into plain text."""

from pathlib import Path


def extract_text(text: str) -> str:
    """Return pasted text, normalised (stripped, consistent newlines)."""
    raise NotImplementedError


def extract_pdf(data: bytes) -> str:
    """Return the text of every page in a PDF, using PyMuPDF."""
    raise NotImplementedError


def extract_docx(data: bytes) -> str:
    """Return the paragraph text of a DOCX file, using python-docx."""
    raise NotImplementedError


def extract_image(data: bytes, media_type: str) -> str:
    """Return a text description of an image, produced by the vision model."""
    # No OCR: the vision model reads text and describes layout in one step.
    raise NotImplementedError


def extract_file(file_name: str, data: bytes) -> str:
    """Pick the right extractor from the file extension and return its text."""
    raise NotImplementedError


def file_extension(file_name: str) -> str:
    """Return the lower-case extension without the dot, e.g. 'pdf'."""
    return Path(file_name).suffix.lower().lstrip(".")
