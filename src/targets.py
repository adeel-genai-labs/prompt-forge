"""Prompt targets: what a great prompt looks like for each kind of tool.

Only data_analytics for now; the dict shape lets more targets be added later.

Pure data. The generator puts `guidance` and `required_sections` into the
system prompt; guardrails check the output has every required section.
"""

TARGETS: dict[str, dict] = {
    "data_analytics": {
        "label": "Data & analytics (SQL, Databricks)",
        "guidance": (
            "Write for an assistant that produces SQL or PySpark for analytics on Databricks. "
            "Start from the business question in plain language and the decision it supports. "
            "Name data sources with Unity Catalog three-level names (catalog.schema.table), "
            "list the key columns, state the grain (one row per what) and how tables join. "
            "Define every metric and term unambiguously, e.g. what counts as an 'active "
            "customer' or how revenue treats refunds and currency. State filters and the time "
            "range with explicit dates, the time zone, and whether boundaries are inclusive. "
            "Say explicitly how to handle nulls and duplicates, e.g. exclude, COALESCE, or "
            "deduplicate on a key with ROW_NUMBER. Default to Databricks SQL; mention PySpark "
            "(DataFrame API) as the alternative when transformation logic is complex or the "
            "user asks for it. Queries are read-only by default: no INSERT, UPDATE, DELETE or "
            "DDL unless the user explicitly asks, and when writes are requested use MERGE so "
            "reruns are idempotent. Ask for readable, well-commented queries using CTEs; "
            "select only the columns needed and avoid SELECT *; use LIMIT while exploring; "
            "and call out performance concerns such as partition pruning and large joins. "
            "Describe the expected output: columns, ordering, granularity and format. Include "
            "validation queries, such as row counts, totals that reconcile with a known "
            "figure, and null or duplicate checks. If schema details are missing, state "
            "assumptions clearly instead of inventing table or column names."
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
            "Which tables or views hold the data, and what is the grain of each?",
            "How are the key metrics defined (e.g. active user, revenue, churn)?",
            "What time range and time zone, and are the end dates inclusive?",
            "Databricks SQL or PySpark? Any Unity Catalog names to use?",
            "Roughly how large are the tables, and how are they partitioned?",
            "Is there a known figure the result should reconcile with?",
        ],
    },
}

DEFAULT_TARGET = "data_analytics"
