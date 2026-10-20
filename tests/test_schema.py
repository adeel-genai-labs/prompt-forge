"""Tests for src/schema.py."""

import pytest
from pydantic import ValidationError

from src.schema import MAX_QUESTIONS, ClarifyingQuestion, GeneratedPrompt


def valid_fields() -> dict:
    """Return the smallest set of fields that makes a valid GeneratedPrompt."""
    return {
        "target": "data_analytics",
        "title": "Monthly revenue by region",
        "sections": {"Business question": "Revenue by region per month.", "Data sources": "main.sales.orders"},
        "final_prompt": "Write a Databricks SQL query...",
    }


def test_valid_prompt_uses_defaults_for_optional_fields():
    prompt = GeneratedPrompt(**valid_fields())
    assert prompt.assumptions == []
    assert prompt.sections["Data sources"] == "main.sales.orders"


def test_default_assumptions_are_not_shared_between_instances():
    first = GeneratedPrompt(**valid_fields())
    second = GeneratedPrompt(**valid_fields())
    first.assumptions.append("UTC months")
    assert second.assumptions == []


def test_all_fields_round_trip_through_json():
    prompt = GeneratedPrompt(**valid_fields(), assumptions=["Revenue excludes refunds"])
    assert GeneratedPrompt.model_validate_json(prompt.model_dump_json()) == prompt


def test_image_only_negative_prompt_field_is_gone():
    assert "negative_prompt" not in GeneratedPrompt.model_fields


@pytest.mark.parametrize("missing", ["target", "title", "sections", "final_prompt"])
def test_missing_required_field_is_rejected(missing):
    fields = valid_fields()
    del fields[missing]
    with pytest.raises(ValidationError):
        GeneratedPrompt(**fields)


@pytest.mark.parametrize(
    "field, bad_value",
    [
        ("sections", ["Business question", "Data sources"]),
        ("sections", {"Data sources": ["not", "a", "string"]}),
        ("assumptions", "not a list"),
    ],
)
def test_wrong_field_type_is_rejected(field, bad_value):
    with pytest.raises(ValidationError):
        GeneratedPrompt(**{**valid_fields(), field: bad_value})


# --- ClarifyingQuestion ---


def valid_question() -> dict:
    return {"question": "Revenue: gross or net?", "why": "Changes the metric.", "options": ["Gross", "Net"], "default": "Net"}


def test_clarifying_question_accepts_valid_data():
    assert ClarifyingQuestion(**valid_question()).model_dump() == valid_question()


@pytest.mark.parametrize("options", [["Only one"], ["a", "b", "c", "d", "e"], []])
def test_clarifying_question_needs_two_to_four_options(options):
    with pytest.raises(ValidationError):
        ClarifyingQuestion(**{**valid_question(), "options": options})


@pytest.mark.parametrize("missing", ["question", "why", "options", "default"])
def test_clarifying_question_requires_every_field(missing):
    data = valid_question()
    del data[missing]
    with pytest.raises(ValidationError):
        ClarifyingQuestion(**data)


def test_clarifying_question_default_falls_back_to_first_option():
    assert ClarifyingQuestion(**{**valid_question(), "default": "Net revenue"}).default == "Gross"


def test_max_questions_is_four():
    assert MAX_QUESTIONS == 4
