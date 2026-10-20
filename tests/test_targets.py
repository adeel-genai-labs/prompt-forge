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


def test_data_analytics_defaults_to_databricks_sql_and_mentions_pyspark():
    guidance = TARGETS["data_analytics"]["guidance"]
    assert "Databricks SQL" in guidance
    assert "PySpark" in guidance


def test_image_generation_guidance_asks_for_negative_prompt():
    assert "negative prompt" in TARGETS["image_generation"]["guidance"]
