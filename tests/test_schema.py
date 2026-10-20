"""Tests for src/schema.py."""

import pytest
from pydantic import ValidationError

from src.schema import GeneratedPrompt


def valid_fields() -> dict:
    """Return the smallest set of fields that makes a valid GeneratedPrompt."""
    return {
        "target": "coding_agent",
        "title": "Add login rate limiting",
        "sections": {"Goal": "Limit failed logins.", "Context": "Flask app."},
        "final_prompt": "You are working in a Flask app...",
    }


def test_valid_prompt_uses_defaults_for_optional_fields():
    prompt = GeneratedPrompt(**valid_fields())
    assert prompt.assumptions == []
    assert prompt.negative_prompt == ""
    assert prompt.sections["Goal"] == "Limit failed logins."


def test_default_assumptions_are_not_shared_between_instances():
    first = GeneratedPrompt(**valid_fields())
    second = GeneratedPrompt(**valid_fields())
    first.assumptions.append("Python 3.11")
    assert second.assumptions == []


def test_all_fields_round_trip_through_json():
    prompt = GeneratedPrompt(
        **valid_fields(),
        assumptions=["Uses Redis for counters"],
        negative_prompt="blurry, watermark",
    )
    assert GeneratedPrompt.model_validate_json(prompt.model_dump_json()) == prompt


@pytest.mark.parametrize("missing", ["target", "title", "sections", "final_prompt"])
def test_missing_required_field_is_rejected(missing):
    fields = valid_fields()
    del fields[missing]
    with pytest.raises(ValidationError):
        GeneratedPrompt(**fields)


@pytest.mark.parametrize(
    "field, bad_value",
    [
        ("sections", ["Goal", "Context"]),
        ("sections", {"Goal": ["not", "a", "string"]}),
        ("assumptions", "not a list"),
    ],
)
def test_wrong_field_type_is_rejected(field, bad_value):
    with pytest.raises(ValidationError):
        GeneratedPrompt(**{**valid_fields(), field: bad_value})
