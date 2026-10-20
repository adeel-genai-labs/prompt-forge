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
            "Never invent table or column names: use names exactly as the user supplied them. "
            "Unity Catalog names are exactly catalog.schema.table (three parts). If no schema "
            "is given, use clearly marked placeholders such as <catalog>.<schema>.<table_name> "
            "and <revenue_column>, and add \"Schema not provided\" to assumptions, saying which "
            "tables and columns are needed. List the key columns, state the grain (one row per "
            "what) and how tables join. Define every metric and term unambiguously, e.g. what "
            "counts as an 'active customer' or how revenue treats refunds and currency. Don't "
            "assume a specific year or date range unless the user gives one; use a placeholder "
            "or a relative range (e.g. \"last 12 complete months\") and list it as an assumption. "
            "State the time zone. Time filters use half-open ranges (>= start AND < "
            "next_period_start); never use BETWEEN on timestamps. Say explicitly how to handle "
            "nulls and duplicates, e.g. exclude, COALESCE, or deduplicate on a key with "
            "ROW_NUMBER. Default to Databricks SQL; use PySpark (DataFrame API) only when the "
            "user asks for it. Make one decision per choice and don't offer alternatives inside "
            "the spec; record each choice in assumptions. Queries are read-only by default: no "
            "INSERT, UPDATE, DELETE or DDL unless the user explicitly asks, and when writes are "
            "requested use MERGE so reruns are idempotent. Ask for readable, well-commented "
            "queries using CTEs; select only the columns needed and avoid SELECT *; use LIMIT "
            "while exploring; and call out performance concerns such as partition pruning and "
            "large joins. Describe the expected output: columns, ordering, granularity and "
            "format. Include validation queries, such as row counts, totals that reconcile with "
            "a known figure, and null or duplicate checks. Validation queries must use the same "
            "filters, units and currency as the result so the numbers reconcile."
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
