"""Tests for src/targets.py: the TARGETS data is complete and well-formed."""

import pytest

from src.targets import DEFAULT_TARGET, TARGETS

GUIDANCE = TARGETS["data_analytics"]["guidance"]


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


def test_guidance_is_a_concise_bulleted_checklist():
    lines = GUIDANCE.splitlines()
    assert all(line.startswith("- ") for line in lines)
    assert len(lines) >= 10
    # Target was under 2,000 characters; the two literal SQL examples (~170 chars) keep it slightly above.
    assert len(GUIDANCE) < 2200


# Each existing rule, in the checklist's wording.
@pytest.mark.parametrize(
    "phrase",
    [
        # dialect and starting point
        "Databricks SQL by default",
        "PySpark only if asked",
        "business question and the decision it supports",
        # names and schemas
        "Never invent table or column names",
        "use them exactly as supplied",
        "Unity Catalog names are exactly catalog.schema.table",
        "<catalog>.<schema>.<table_name>",
        "<revenue_column>",
        '"Schema not provided"',
        # grain and definitions
        "grain (one row per what)",
        "Define every metric",
        "gross vs net, refunds, discounts, currency",
        '"confirm with requester"',
        "never stated as fact",
        # time
        "Never assume a year or date range",
        "relative range as concrete SQL",
        "last 12 complete months: >= add_months(date_trunc('MONTH', current_date()), -12) AND < "
        "date_trunc('MONTH', current_date())",
        ">= start AND < next_period_start",
        "never BETWEEN on timestamps",
        "time zone",
        # periods and row counts
        "generate the series (sequence() + explode) and left join",
        "empty periods are omitted",
        "Stated row counts must match the range",
        # nulls and duplicates
        "nulls and duplicates explicitly",
        "Duplicate checks group by the record key (<transaction_id> if unknown), never timestamp",
        # writes and style
        "Read-only by default",
        "idempotent MERGE",
        "avoid SELECT *",
        "LIMIT while exploring",
        "partition pruning",
        "CTEs",
        # decisions
        "One decision per choice",
        "anything still unknown goes in assumptions",
        # output and validation
        "columns, ordering, grain, format",
        "row counts, null/duplicate checks",
        "reconciliation independent of the result",
        "re-aggregate from source with the same filters, units, currency",
        "known reported figure",
        "never validate the result against itself",
    ],
)
def test_guidance_keeps_every_existing_rule(phrase):
    assert phrase in GUIDANCE


# Rules added in Phase B.
@pytest.mark.parametrize(
    "phrase",
    [
        "Window functions always have PARTITION BY and ORDER BY",
        "ROW_NUMBER() OVER (PARTITION BY id ORDER BY ts DESC)",
        "Aggregate child tables (e.g. refunds) to the join key before joining",
        "fan-out double counting",
        'no hedging ("if X exists", "or alternatively")',
        "Use the schema and answers",
        "row count is then exact",
        "With a schema, use only its tables and columns (no placeholders for them)",
    ],
)
def test_guidance_has_phase_b_rules(phrase):
    assert phrase in GUIDANCE


def test_guidance_has_no_conflicting_older_rules():
    assert "explicit dates" not in GUIDANCE  # replaced by "never assume a date range"
    assert "whether boundaries are inclusive" not in GUIDANCE  # replaced by half-open ranges
    assert "as the alternative" not in GUIDANCE  # replaced by "one decision per choice"


@pytest.mark.parametrize(
    "topic",
    [
        "gross or net",
        "refund date or the original sale date",
        "Currency",
        "Time range",
        "Grain",
        "Time zone",
        "Empty periods",
        "Deduplication key",
        "test, cancelled or internal orders",
        "Audience and output format",
    ],
)
def test_clarify_topics_cover_phase_b_list(topic):
    assert any(topic in item for item in TARGETS["data_analytics"]["clarify_topics"])
