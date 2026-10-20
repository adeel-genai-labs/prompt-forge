"""Input, content and output checks.

Each check returns None when everything is fine, or a friendly message
that the UI can show to the user as-is.
"""

import re
from collections import Counter

import pymupdf

from src.extractors import SUPPORTED_EXTENSIONS, file_extension
from src.schema import GeneratedPrompt
from src.targets import TARGETS

MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_PDF_PAGES = 30
MAX_TEXT_CHARS = 50_000
MAX_GOAL_CHARS = 500
ALLOWED_EXTENSIONS = SUPPORTED_EXTENSIONS

# Multi-word phrases only, so ordinary text like "kill the process" or "photobomb" passes.
# self-harm comes first so it gets the supportive message if several topics match.
BLOCKED_TOPICS = {
    "self-harm": ["kill myself", "end my life", "hurt myself", "want to die", "suicide method"],
    "weapons": ["build a bomb", "make a bomb", "make a pipe bomb", "build an explosive", "make a ghost gun"],
    "malware": ["write ransomware", "create ransomware", "write a keylogger", "write malware", "create malware"],
}
SELF_HARM_MESSAGE = (
    "It sounds like you might be going through something really hard. You don't have to face it alone. "
    "Please consider reaching out to someone you trust or a local helpline. "
    "If you are in immediate danger, contact your local emergency number."
)

INJECTION_PHRASES = [
    "ignore previous instructions",
    "ignore all previous instructions",
    "ignore prior instructions",
    "ignore the above instructions",
    "disregard previous instructions",
    "disregard all previous instructions",
    "forget your instructions",
    "new instructions:",
    "reveal your system prompt",
    "print your system prompt",
    "developer mode",
    "jailbreak",
]

# Applied in this order. PHONE is last because its loose digit groups would
# otherwise swallow card, SSN and Aadhaar numbers.
PII_PATTERNS = {
    "EMAIL": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    "CARD": re.compile(r"(?<!\d)\d(?:[ -]?\d){12,18}(?!\d)"),
    "US_SSN": re.compile(r"(?<!\d)(?!000|666|9\d\d)\d{3}-(?!00)\d{2}-(?!0000)\d{4}(?!\d)"),
    "AADHAAR": re.compile(r"(?<!\d)[2-9]\d{3}([ -]?)\d{4}\1\d{4}(?!\d)"),
    "UK_NI": re.compile(r"\b(?!BG|GB|KN|NK|NT|TN|ZZ)[A-CEGHJ-PR-TW-Z][A-CEGHJ-NPR-TW-Z] ?\d{2} ?\d{2} ?\d{2} ?[A-D]\b"),
    "PAN": re.compile(r"\b[A-Z]{3}[ABCFGHJLPT][A-Z]\d{4}[A-Z]\b"),
    "PHONE": re.compile(r"(?<![\w+])(?:\+\d{1,3}[ -]?)?(?:\(\d{2,5}\)[ -]?\d{2,5}|\d{2,5})(?:[ -]\d{2,5}){1,3}(?![\w-])"),
}

# ISO dates, datetimes and times. "2023-01-01 00:00:00" would otherwise look like a phone
# number ("2023-01-01 00" has 10 digits), so PII matches that overlap these are skipped.
DATETIME_PATTERN = re.compile(
    r"(?<!\d)\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:?\d{2})?)?(?!\d)"
    r"|(?<![\d:])\d{1,2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?![\d:])"
)

# Dotted table names in generated prompts. Three parts (catalog.schema.table) count anywhere;
# two parts (schema.table) only after a SQL keyword, since "o.order_id" is usually alias.column,
# and not when followed by a comparison ("join o.order_id = r.order_id" compares columns).
THREE_PART_NAME = re.compile(r"(?<![\w.@/<])[A-Za-z_]\w*\.[A-Za-z_]\w*\.[A-Za-z_]\w*")
TWO_PART_NAME_AFTER_KEYWORD = re.compile(
    r"\b(?:FROM|JOIN|INTO|TABLE|UPDATE|USING)\s+([A-Za-z_]\w*\.[A-Za-z_]\w*)(?![\w.])(?!\s*[=<>!])", re.IGNORECASE
)
# Web domains (e.g. docs.databricks.com) have the same shape as table names.
DOMAIN_ENDINGS = {"com", "org", "net", "io", "ai", "dev", "co", "uk"}

SECRET_PATTERNS = {
    "API key": re.compile(r"\bsk-[A-Za-z0-9_-]{20,}"),
    "AWS access key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "GitHub token": re.compile(r"\b(?:ghp_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{22,})"),
    "private key": re.compile(r"-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----"),
}

# Verhoeff tables, used by the official Aadhaar check digit.
_VERHOEFF_D = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
    [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
    [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
    [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
    [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
    [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
    [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
    [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
    [9, 8, 7, 6, 5, 4, 3, 2, 1, 0],
]
_VERHOEFF_P = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
    [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
    [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
    [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
    [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
    [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
    [7, 0, 4, 6, 9, 1, 3, 2, 5, 8],
]


def check_file(file_name: str, data: bytes) -> str | None:
    """Reject unsupported types, empty files and files over MAX_FILE_BYTES."""
    if file_extension(file_name) not in ALLOWED_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_EXTENSIONS))
        return f"Sorry, '{file_name}' isn't a supported file type. Please upload one of: {allowed}."
    if not data:
        return f"'{file_name}' is empty. Please choose a file with some content."
    if len(data) > MAX_FILE_BYTES:
        return f"'{file_name}' is too large. Files can be up to {MAX_FILE_BYTES // (1024 * 1024)} MB."
    return None


def check_pdf_pages(data: bytes) -> str | None:
    """Reject PDFs that cannot be opened, need a password, or have more than MAX_PDF_PAGES pages."""
    try:
        with pymupdf.open(stream=data, filetype="pdf") as pdf:
            needs_password, page_count = pdf.needs_pass, pdf.page_count
    except (pymupdf.FileDataError, RuntimeError):
        return "We couldn't read this PDF. It may be damaged. Please try another file."
    if needs_password:
        return "This PDF is password-protected. Please remove the password and upload it again."
    if page_count > MAX_PDF_PAGES:
        return f"This PDF has {page_count} pages; the limit is {MAX_PDF_PAGES}. Please upload a shorter document."
    return None


def check_content(text: str, max_chars: int = MAX_TEXT_CHARS) -> str | None:
    """Reject text that is empty or longer than max_chars (MAX_GOAL_CHARS is used for the goal)."""
    if not text.strip():
        return "There's no text to work with. Please type something or upload a file with readable content."
    if len(text) > max_chars:
        return f"This text is {len(text):,} characters long; the limit is {max_chars:,}. Please shorten it."
    return None


def check_blocked_topics(text: str) -> str | None:
    """Reject text that matches a phrase in BLOCKED_TOPICS; self-harm gets a supportive message."""
    for topic, phrases in BLOCKED_TOPICS.items():
        if matching_phrases(text, phrases):
            if topic == "self-harm":
                return SELF_HARM_MESSAGE
            return f"Sorry, PromptForge can't help with content about {topic}. Please remove that part and try again."
    return None


def redact_pii(text: str) -> tuple[str, dict[str, int]]:
    """Replace emails, phone numbers, card numbers and government IDs with tags like [EMAIL].

    Returns the redacted text and a count per tag (only tags that were found).
    Runs on extracted content and again on the generated output. Dates and times are never redacted.
    """
    validators = {"CARD": luhn_valid, "AADHAAR": verhoeff_valid, "PHONE": has_phone_length}
    counts: dict[str, int] = {}

    for name, pattern in PII_PATTERNS.items():
        is_valid = validators.get(name)
        # Recomputed per pattern because each substitution changes the text and its positions.
        datetime_spans = [match.span() for match in DATETIME_PATTERN.finditer(text)]

        def replace(match: re.Match) -> str:
            if overlaps_any(match.span(), datetime_spans):
                return match.group()
            if is_valid and not is_valid(match.group()):
                return match.group()
            counts[name] = counts.get(name, 0) + 1
            return f"[{name}]"

        text = pattern.sub(replace, text)
    return text, counts


def redact_prompt(prompt: GeneratedPrompt) -> tuple[GeneratedPrompt, dict[str, int]]:
    """Run redact_pii on every text field of a generated prompt; return the new prompt and total counts."""
    totals: Counter[str] = Counter()

    def redact(text: str) -> str:
        redacted, counts = redact_pii(text)
        totals.update(counts)
        return redacted

    redacted_prompt = prompt.model_copy(
        update={
            "title": redact(prompt.title),
            "sections": {name: redact(text) for name, text in prompt.sections.items()},
            "assumptions": [redact(text) for text in prompt.assumptions],
            "final_prompt": redact(prompt.final_prompt),
        }
    )
    return redacted_prompt, dict(totals)


def find_unverified_names(prompt: GeneratedPrompt, input_text: str) -> list[str]:
    """Return dotted table names in the generated prompt that don't appear in the user's input.

    Used to warn the user, not to block. Placeholders in <angle brackets> are ignored,
    as are web domains. Matching ignores case and backticks.
    """
    output_text = "\n".join([prompt.title, *prompt.sections.values(), *prompt.assumptions, prompt.final_prompt])
    output_text = output_text.replace("`", "")
    input_text = input_text.replace("`", "")

    names = THREE_PART_NAME.findall(output_text) + TWO_PART_NAME_AFTER_KEYWORD.findall(output_text)
    unverified = []
    for name in names:
        if name.rsplit(".", 1)[-1].lower() in DOMAIN_ENDINGS:
            continue
        in_input = re.search(rf"(?<![\w.]){re.escape(name)}(?![\w])", input_text, flags=re.IGNORECASE)
        if not in_input and name.lower() not in (seen.lower() for seen in unverified):
            unverified.append(name)
    return unverified


def find_injection_attempts(text: str) -> list[str]:
    """Return INJECTION_PHRASES found in the text. Used to warn the user, not to block."""
    return matching_phrases(text, INJECTION_PHRASES)


def wrap_as_data(text: str) -> str:
    """Wrap untrusted text in <user_content> tags so the model treats it as data, not instructions."""
    # Escape any closing tag so the content can't end the data block early and smuggle in instructions.
    escaped = re.sub(r"<\s*/\s*user_content\s*>", "&lt;/user_content&gt;", text, flags=re.IGNORECASE)
    return f"<user_content>\n{escaped}\n</user_content>"


def check_output(prompt: GeneratedPrompt) -> str | None:
    """Reject a generated prompt that has an unknown target, a missing or empty required section
    for that target (from TARGETS), an empty final_prompt, or text that looks like a leaked secret."""
    if prompt.target not in TARGETS:
        return f"The generated prompt has an unknown target '{prompt.target}'. Please try generating it again."
    missing = missing_output_fields(prompt)
    if missing:
        return f"The generated prompt is missing: {', '.join(missing)}. Please try generating it again."

    all_text = "\n".join([prompt.title, *prompt.sections.values(), *prompt.assumptions, prompt.final_prompt])
    for name, pattern in SECRET_PATTERNS.items():
        if pattern.search(all_text):
            return (
                f"The generated prompt appears to contain a secret ({name}), so it was blocked. "
                "Please remove any keys or tokens from your input and try again."
            )
    return None


def missing_output_fields(prompt: GeneratedPrompt) -> list[str]:
    """Return required parts that are missing or empty: the target's section names, then 'final_prompt'."""
    # Models vary capitalisation ("Data Sources"), which shouldn't count as missing.
    sections = {name.strip().lower(): text for name, text in prompt.sections.items()}
    required = TARGETS.get(prompt.target, {}).get("required_sections", [])
    missing = [name for name in required if not sections.get(name.lower(), "").strip()]
    if not prompt.final_prompt.strip():
        missing.append("final_prompt")
    return missing


def check_has_input(goal: str, content: str) -> str | None:
    """Require at least one of a goal or some content (pasted text or file text)."""
    if not goal.strip() and not content.strip():
        return "Please describe what the prompt is for, paste some text, or upload a file."
    return None


def matching_phrases(text: str, phrases: list[str]) -> list[str]:
    """Return the phrases that appear in text as whole words, ignoring case and extra whitespace."""
    found = []
    for phrase in phrases:
        pattern = r"\s+".join(re.escape(word) for word in phrase.split())
        if re.search(rf"(?<!\w){pattern}(?!\w)", text, flags=re.IGNORECASE):
            found.append(phrase)
    return found


def luhn_valid(number: str) -> bool:
    """Return True if the digits in number pass the Luhn checksum used by payment cards."""
    total = 0
    for position, digit in enumerate(int(c) for c in reversed(number) if c.isdigit()):
        if position % 2 == 1:
            digit = digit * 2 - 9 if digit > 4 else digit * 2
        total += digit
    return total % 10 == 0


def verhoeff_valid(number: str) -> bool:
    """Return True if the digits in number pass the Verhoeff checksum used by Aadhaar."""
    check = 0
    for position, digit in enumerate(int(c) for c in reversed(number) if c.isdigit()):
        check = _VERHOEFF_D[check][_VERHOEFF_P[position % 8][digit]]
    return check == 0


def overlaps_any(span: tuple[int, int], spans: list[tuple[int, int]]) -> bool:
    """Return True if span overlaps any of spans (each a (start, end) pair, end exclusive)."""
    start, end = span
    return any(start < other_end and other_start < end for other_start, other_end in spans)


def has_phone_length(number: str) -> bool:
    """Return True if number has 10-15 digits, which excludes dates and short codes."""
    return 10 <= sum(c.isdigit() for c in number) <= 15
