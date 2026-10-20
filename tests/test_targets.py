"""Tests for src/targets.py: the TARGETS data is complete and well-formed."""

import pytest

from src.targets import DEFAULT_TARGET, TARGETS


def test_expected_targets_exist():
    assert set(TARGETS) == {"coding_agent", "data_analytics", "image_generation"}
    assert DEFAULT_TARGET in TARGETS


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
        "operating system, shell",
        "language and framework versions",
        "work incrementally",
        "one module at a time",
        "'Do not' list",
        "do not run git commands",
        "do not add new dependencies without asking",
        "do not modify unrelated files",
        "run the tests, show the results and list every file changed",
        "stop and ask before making ambiguous",
    ],
)
def test_coding_agent_guidance_covers_key_practices(phrase):
    assert phrase in TARGETS["coding_agent"]["guidance"]


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
    ],
)
def test_data_analytics_guidance_covers_key_practices(phrase):
    assert phrase in TARGETS["data_analytics"]["guidance"]


def test_image_generation_guidance_asks_for_negative_prompt():
    assert "negative prompt" in TARGETS["image_generation"]["guidance"]
