"""Tests for src/targets.py: the TARGETS data is complete and well-formed."""

import pytest

from src.targets import DEFAULT_TARGET, TARGETS


def test_only_data_analytics_target_exists_and_is_default():
    assert set(TARGETS) == {"data_analytics"}
    assert DEFAULT_TARGET == "data_analytics"


@pytest.mark.parametrize("key", list(TARGETS))
def test_target_has_all_fields_filled_in(key):
    target = TARGETS[key]
    assert target["label"].strip()
    assert target["guidance"].strip()
    assert target["required_sections"] and all(s.strip() for s in target["required_sections"])
    assert target["clarify_topics"] and all(t.strip() for t in target["clarify_topics"])
    assert len(set(target["required_sections"])) == len(target["required_sections"])


@pytest.mark.parametrize(
    "phrase",
    [
        "Databricks SQL",
        "PySpark",
        "catalog.schema.table",
        "read-only by default",
        "MERGE",
        "idempotent",
        "avoid SELECT *",
        "LIMIT while exploring",
        "nulls and duplicates",
        "grain",
        "time zone",
        "row counts",
        "reconcile",
        # Rules added after the first live Groq review
        "Never invent table or column names",
        "exactly as the user supplied them",
        "exactly catalog.schema.table",
        "<catalog>.<schema>.<table_name>",
        "<revenue_column>",
        '"Schema not provided"',
        "Don't assume a specific year or date range",
        '"last 12 complete months"',
        ">= start AND < next_period_start",
        "never use BETWEEN on timestamps",
        "one decision per choice",
        "don't offer alternatives",
        "record each choice in assumptions",
        "same filters, units and currency",
    ],
)
def test_data_analytics_guidance_covers_key_practices(phrase):
    assert phrase in TARGETS["data_analytics"]["guidance"]


def test_data_analytics_guidance_has_no_conflicting_older_rules():
    guidance = TARGETS["data_analytics"]["guidance"]
    assert "explicit dates" not in guidance  # replaced by "don't assume a date range"
    assert "whether boundaries are inclusive" not in guidance  # replaced by half-open ranges
    assert "as the alternative" not in guidance  # replaced by "one decision per choice"
