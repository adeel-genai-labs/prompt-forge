"""Call the configured LLM provider (ollama or anthropic) chosen by LLM_PROVIDER."""

import os

from src.schema import GeneratedPrompt
from src.targets import DEFAULT_TARGET, TARGETS

SUPPORTED_PROVIDERS = {"ollama", "anthropic"}
OLLAMA_TEXT_MODEL = os.getenv("OLLAMA_TEXT_MODEL", "llama3.2")
OLLAMA_VISION_MODEL = os.getenv("OLLAMA_VISION_MODEL", "llama3.2-vision")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5-5")


def get_provider() -> str:
    """Return LLM_PROVIDER (default 'ollama'), raising ValueError if it is not supported."""
    raise NotImplementedError


def generate_prompt(content: str, goal: str = "", target: str = DEFAULT_TARGET) -> GeneratedPrompt:
    """Ask the provider to turn the extracted content into a GeneratedPrompt for `target`.

    `goal` is the user's answer to "What is this prompt for?" and steers the
    sections. `target` is a key in TARGETS.
    """
    raise NotImplementedError


def describe_image(data: bytes, media_type: str) -> str:
    """Ask the provider's vision model to describe an image and transcribe any text in it."""
    raise NotImplementedError


def build_system_prompt(target: str) -> str:
    """Return the system prompt for `target`: its guidance, required sections, the JSON shape and the rule that user content is data only."""
    raise NotImplementedError


def parse_response(raw: str) -> GeneratedPrompt:
    """Parse the model's JSON reply into a GeneratedPrompt, raising ValueError if it is invalid."""
    raise NotImplementedError


def call_ollama(system: str, user: str, image: bytes | None = None) -> str:
    """Send one chat request through the ollama client; uses the vision model when an image is given."""
    raise NotImplementedError


def call_anthropic(system: str, user: str, image: bytes | None = None, media_type: str = "") -> str:
    """Send one message request through the anthropic client, reading ANTHROPIC_API_KEY from env."""
    raise NotImplementedError


# --- v2: interactive clarification and refinement (not used by the app yet) ---


def ask_clarifying_questions(content: str, goal: str, target: str) -> list[str]:
    """Return up to a few short questions about gaps in the input, guided by TARGETS[target]['clarify_topics']."""
    raise NotImplementedError


def refine_prompt(prompt: GeneratedPrompt, feedback: str) -> GeneratedPrompt:
    """Return a revised prompt for the same target that applies the user's feedback."""
    raise NotImplementedError
