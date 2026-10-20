# Sample inputs for manual testing

All names, numbers, tables and records in these files are made up. Use them when trying
PromptForge for Databricks by hand. Automated tests build their own data in memory and do not use this folder.

| File | What it is | What to check |
|------|------------|---------------|
| `vague_request.txt` | One line: "need a sales report" | The model fills every section with sensible defaults and lists its assumptions (metrics, tables, time range) |
| `detailed_request.txt` | Monthly revenue by region, with Unity Catalog table names, grain, definitions, output columns and a reconciliation figure | The prompt keeps the exact `catalog.schema.table` names and definitions, stays read-only, and includes validation queries |
| `pii_sample.txt` | Fake customer record: email, two phone numbers, test card number (4111…), US SSN, UK NI number, Indian Aadhaar and PAN (fake but correctly formatted, and the Aadhaar passes its checksum, so the precise patterns match) | Every item is replaced by a tag such as `[EMAIL]`; the order number, date and total on the last line are **not** redacted |
| `injection_sample.txt` | Report notes with "Ignore previous instructions…" in the middle | The injection warning appears and the model treats the text as data, not as an instruction |
| `sample.txt` | Short team meeting notes | Plain text upload works; notes that aren't a data request still give a sensible prompt with assumptions |
| `sample.pdf` | Two-page fictional product brief | PDF upload: both pages are extracted, in order |
| `sample.docx` | Status report: heading, paragraph and a 3×3 table | DOCX upload: paragraphs and table rows (`Task \| Owner \| Status`) are extracted |

You can also leave everything empty except the goal (e.g. "weekly active users by country") to try goal-only input.

`sample.pdf` and `sample.docx` were created with PyMuPDF and python-docx. Recreate them the
same way if they need to change, and keep the data fictional.
