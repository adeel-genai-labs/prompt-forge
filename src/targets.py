"""Prompt targets: what a great prompt looks like for each kind of tool.

Only data_analytics for now; the dict shape lets more targets be added later.

Pure data. The generator puts `guidance` and `required_sections` into the
system prompt; guardrails check the output has every required section.
"""

TARGETS: dict[str, dict] = {
    "data_analytics": {
        "label": "Data & analytics (SQL, Databricks)",
        # A short checklist: small models follow bullets more reliably than one long paragraph.
        "guidance": "\n".join(
            [
                "- Databricks SQL by default; PySpark only if asked.",
                "- Start from the business question and the decision it supports.",
                "- Never invent table or column names; use them exactly as supplied. With a schema, use only its "
                "tables and columns (no placeholders for them).",
                "- Unity Catalog names are exactly catalog.schema.table. No schema: placeholders like "
                "<catalog>.<schema>.<table_name>, <revenue_column>, and \"Schema not provided\" (and what's needed) "
                "in assumptions.",
                "- State the grain (one row per what), keys and joins. Aggregate child tables (e.g. refunds) to the "
                "join key before joining (no fan-out double counting).",
                "- Define every metric. Unspecified business definitions (gross vs net, refunds, discounts, "
                "currency) go in assumptions marked \"confirm with requester\", never stated as fact.",
                "- Never assume a year or date range; use a placeholder or relative range as concrete SQL, e.g. last "
                "12 complete months: >= add_months(date_trunc('MONTH', current_date()), -12) AND < "
                "date_trunc('MONTH', current_date()).",
                "- Time filters are half-open (>= start AND < next_period_start); never BETWEEN on timestamps. "
                "State the time zone.",
                "- One row per period: generate the series (sequence() + explode) and left join (row count is then "
                "exact), or say empty periods are omitted. Stated row counts must match the range.",
                "- Handle nulls and duplicates explicitly. Window functions always have PARTITION BY and ORDER BY, "
                "e.g. ROW_NUMBER() OVER (PARTITION BY id ORDER BY ts DESC). Duplicate checks group by the record "
                "key (<transaction_id> if unknown), never timestamp.",
                "- Read-only by default (no DML/DDL); requested writes use idempotent MERGE.",
                "- Use CTEs and comments; avoid SELECT *; LIMIT while exploring; note partition pruning, big joins.",
                "- One decision per choice; no hedging (\"if X exists\", \"or alternatively\"). Use the schema and "
                "answers; anything still unknown goes in assumptions.",
                "- Describe the output: columns, ordering, grain, format.",
                "- Validate: row counts, null/duplicate checks, reconciliation independent of the result "
                "(re-aggregate from source with the same filters, units, currency, or a known reported figure); "
                "never validate the result against itself.",
            ]
        ),
        "required_sections": [
            "Business question",
            "Data sources",
            "Definitions & metrics",
            "Filters & time range",
            "Dialect & performance",
            "Expected output & validation",
        ],
        "clarify_topics": [
            "Revenue definition: gross or net?",
            "Refunds: included? Attributed to the refund date or the original sale date?",
            "Currency: which one, and how to convert?",
            "Time range",
            "Grain (e.g. one row per day, month, region)",
            "Time zone",
            "Empty periods: show with zeros or omit?",
            "Deduplication key",
            "Exclusions: test, cancelled or internal orders?",
            "Audience and output format",
        ],
    },
}

DEFAULT_TARGET = "data_analytics"
