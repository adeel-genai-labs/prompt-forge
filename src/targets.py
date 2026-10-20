"""Prompt targets: what a great prompt looks like for each kind of tool.

Pure data. The generator puts `guidance` and `required_sections` into the
system prompt; guardrails check the output has every required section.
"""

TARGETS: dict[str, dict] = {
    "coding_agent": {
        "label": "Coding agent (Claude Code, Copilot)",
        "guidance": (
            "Write for an autonomous coding agent working inside a real repository. "
            "State the goal as the outcome the user wants, not just the change to make. "
            "Give the context the agent cannot discover on its own: why the work matters, "
            "relevant files, modules or commands, the language and framework versions, and "
            "any conventions to follow. Break the work into concrete, ordered tasks that are "
            "small enough to verify. List constraints explicitly: what must not change, "
            "dependencies that may or may not be added, performance or security limits, and "
            "style rules. Write acceptance criteria that can be checked objectively, such as "
            "tests that must pass or behaviour that must be observable. Say what the agent "
            "should hand back: code changes, a summary, test results, or open questions. "
            "Be specific and direct; avoid vague words like 'improve' or 'clean up' without "
            "saying what good looks like. If information is missing, state the assumption "
            "made rather than inventing details."
        ),
        "required_sections": [
            "Goal",
            "Context",
            "Tasks",
            "Constraints",
            "Acceptance criteria",
            "Expected output",
        ],
        "clarify_topics": [
            "Which language, framework and versions does the project use?",
            "Which files, modules or functions are involved?",
            "Is this a new feature, a bug fix, a refactor or tests only?",
            "What must not change (public APIs, database schema, dependencies)?",
            "How will we know it works: tests, commands or observable behaviour?",
            "Should the agent ask before larger changes, or proceed on its own?",
        ],
    },
    "data_analytics": {
        "label": "Data & analytics (SQL, Databricks)",
        "guidance": (
            "Write for an assistant that produces SQL or PySpark for analytics. "
            "Start from the business question in plain language and the decision it supports. "
            "Name the data sources precisely: catalog, schema and table names, key columns, "
            "grain (one row per what), and how tables join. Define every metric and term "
            "unambiguously, e.g. what counts as an 'active customer' or how revenue treats "
            "refunds and currency. State filters and the time range with explicit dates and "
            "time zone, and whether boundaries are inclusive. Default to Databricks SQL; "
            "mention PySpark (DataFrame API) as the alternative when transformation logic is "
            "complex or the user asks for it. Ask for readable, well-commented queries using "
            "CTEs, and call out performance concerns such as partition pruning, avoiding "
            "SELECT *, and large joins. Describe the expected output: columns, ordering, "
            "granularity and format. Include validation steps, such as row-count checks, "
            "totals that should reconcile with a known figure, and null or duplicate checks. "
            "If schema details are missing, state assumptions clearly instead of inventing "
            "table or column names."
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
    "image_generation": {
        "label": "Image generation",
        "guidance": (
            "Write for a text-to-image model. Describe the main subject first, concretely: "
            "who or what it is, appearance, pose or action, and important details. Specify "
            "the style and medium, e.g. photograph, watercolour, 3D render or flat vector "
            "illustration, and for photos the camera, lens and depth of field. Describe the "
            "composition: framing (close-up, wide shot), viewpoint, placement of the subject "
            "and the background. Describe the lighting and colour palette, e.g. soft golden-"
            "hour light or high-contrast neon with teal and magenta. State the mood or emotion "
            "the image should convey. Give the aspect ratio, e.g. 1:1, 16:9 or 9:16. Use "
            "vivid, specific nouns and adjectives rather than long sentences, and put the "
            "most important elements first. Also write a negative prompt listing what to "
            "avoid, such as blurry, distorted hands, extra limbs, text, watermarks or low "
            "resolution. Do not reference copyrighted characters, brand logos or real, named "
            "people; describe original subjects instead."
        ),
        "required_sections": [
            "Subject",
            "Style & medium",
            "Composition",
            "Lighting & colour",
            "Mood",
            "Aspect ratio",
        ],
        "clarify_topics": [
            "Where will the image be used (social post, slide, website hero, print)?",
            "Photograph, illustration, 3D render or another style?",
            "What aspect ratio or size do you need?",
            "Any colours, brand palette or mood to match?",
            "Should the image include any text? (Many models render text poorly.)",
            "Is there anything that must not appear in the image?",
        ],
    },
}

DEFAULT_TARGET = "coding_agent"
