# Claude Code work log

## 2026-10-20 — Project scaffold

**Goal:** Save the project spec as CLAUDE.md and scaffold PromptForge (signatures only, no logic).

**Files changed:**
- Added: CLAUDE.md, requirements.txt, .gitignore, .env.example, .env (copy of example, git-ignored)
- Added: app.py, src/__init__.py, src/extractors.py, src/guardrails.py, src/generator.py, src/schema.py
- Added: tests/__init__.py, tests/test_extractors.py, tests/test_guardrails.py, tests/test_generator.py, tests/test_schema.py (empty)
- Added: docs/claude-code-log.md
- Deleted: .venv.venv/ (stray folder holding only an empty Scripts/activate directory)

**Commands run:**
- `.venv\Scripts\python.exe -m pip install -r requirements.txt` — success
- Import smoke test of app and all src modules — success
- `.venv\Scripts\python.exe -m pytest -q` — "no tests ran" (exit 5, expected with empty test files)

**Result:** Scaffold complete. Only GeneratedPrompt (schema.py), `file_extension` and `show_error` contain real code; everything else raises NotImplementedError.

**Issues & fixes:**
- PyMuPDF 2.0 warns that `import fitz` is deprecated → new API name → use `import pymupdf` when implementing extract_pdf.
- pytest exits with code 5 when no tests are collected → test files are empty for now → resolves once tests are written.

**Decisions:**
- Guardrail checks return `str | None`: None means pass, a string is the friendly message shown to the user.
- extract_image calls the vision model (via generator.describe_image), not OCR.
- Model names are read from env with defaults: OLLAMA_TEXT_MODEL=llama3.2, OLLAMA_VISION_MODEL=llama3.2-vision, ANTHROPIC_MODEL=claude-sonnet-5-5.
- load_dotenv() runs in app.py so src/ modules only read os.environ.
- requirements.txt left unpinned, as requested.

**Next steps:**
- User reviews the planned function list.
- Implement schema tests, then extractors → guardrails → generator → app.py, with tests for each.

## 2026-10-20 — Design changes to stubs

**Goal:** Add PII redaction, blocked topics and PDF/image limits to guardrails; add a goal input; allow text and a file together; pin PyMuPDF below 2.0.

**Files changed:**
- src/guardrails.py: added MAX_IMAGE_BYTES (5 MB), MAX_PDF_PAGES (30), IMAGE_EXTENSIONS, BLOCKED_TOPICS; stubs `check_pdf_pages`, `check_blocked_topics`, `redact_pii`; `check_file` docstring now covers the image limit
- src/generator.py: `generate_prompt(content, goal="")`
- app.py: `render_input() -> tuple[str, str, UploadedFile | None]`; `main()` docstring lists the new pipeline order
- requirements.txt: `pymupdf` → `pymupdf<2`

**Commands run:**
- `.venv\Scripts\python.exe -m pip uninstall -y pymupdf4llm pymupdf-layout onnxruntime`: success
- `.venv\Scripts\python.exe -m pip install -r requirements.txt`: replaced pymupdf 2.0 with 1.28.2
- `import pymupdf` with FutureWarning treated as an error: OK (1.28.2)
- `pip check`: no broken requirements
- Import smoke test of app and src modules: OK

**Result:** Stubs updated; still no logic beyond schema, `file_extension` and `show_error`.

**Issues & fixes:**
- PyMuPDF 2.0 pulled in heavy extras (pymupdf4llm, pymupdf-layout, onnxruntime) → came with the 2.0 package → pinned `pymupdf<2` and uninstalled the extras.

**Decisions:**
- MAX_IMAGE_BYTES applies to both providers so behaviour does not depend on LLM_PROVIDER.
- BLOCKED_TOPICS maps topic → keyword phrases so the friendly message can name the topic. The starter phrases are placeholders and need review.
- Pipeline order (in the `main()` docstring): file checks → extract (images described first) → combine with pasted text → content checks, blocked topics, redact PII → generate → output check, redact PII.
- The goal text also goes through the content guardrails before reaching the model (to confirm at implementation).

**Next steps:**
- User reviews the updated function list.
- Implement with tests: schema → extractors → guardrails → generator → app.py.

## 2026-10-20 — Implement extractors + samples

**Goal:** Implement src/extractors.py with tests; add a samples/ folder for manual testing; record the guardrail decisions from the user's answers.

**Files changed:**
- src/extractors.py: implemented `extract_text`, `extract_pdf`, `extract_docx`, `extract_image`, `extract_file`; added TEXT_EXTENSIONS and IMAGE_MEDIA_TYPES
- tests/test_extractors.py: 10 test functions (13 cases with parametrize)
- Added samples/: sample.txt, sample.pdf, sample.docx, pii_sample.txt, injection_sample.txt, README.md

**Commands run:**
- `.venv\Scripts\python.exe -m pytest -v`: 13 passed
- One-off scratchpad script (not in repo) using PyMuPDF and python-docx to build sample.pdf and sample.docx
- Manual `extract_file` run on sample.txt, sample.pdf and sample.docx: output correct

**Result:** Extractors done and tested. Other modules are still stubs.

**Issues & fixes:**
- Em dash showed as `�` when printing extracted text → Windows console code page, not the extractor (file bytes are valid UTF-8) → nothing to change; set PYTHONIOENCODING=utf-8 when printing to the console.

**Decisions:**
- Extractors raise ValueError with a friendly message for unsupported types and for damaged PDF/DOCX files, so the UI can show it directly.
- `.txt`/`.md` decoded as `utf-8-sig` with `errors="replace"`, so a BOM is dropped and bad bytes don't crash.
- DOCX: all paragraphs first, then table rows as `cell | cell`. Simpler than walking the body in order; the relative position of tables is lost.
- PDF: each page normalised with `extract_text`, empty pages skipped, pages joined with a blank line.
- extract_image calls `generator.describe_image` through the module (`from src import generator`) so tests can monkeypatch it.
- Guardrail answers from the user (to implement in guardrails.py):
  - Government IDs: small dict of named, precise regex patterns: US SSN, UK NI number, Indian Aadhaar (4-4-4, spaces/hyphens optional), Indian PAN.
  - Blocked topics: short list of multi-word phrases only; self-harm gets a supportive message (reach out to someone you trust or a local helpline).
  - Goal field: blocked-topic check, PII redaction, 500-char limit. No data wrapping or injection check, because the goal is the user's own instruction.

**Next steps:**
- Implement guardrails.py with tests (use samples/pii_sample.txt and injection_sample.txt for manual checks).

## 2026-10-20 — Prompt targets design update

**Goal:** Support three prompt targets (coding agent, data & analytics, image generation): add TARGETS data, a new schema, and target-aware stubs.

**Files changed:**
- Added src/targets.py: `TARGETS` dict (label, guidance, required_sections, clarify_topics for each target) and `DEFAULT_TARGET = "coding_agent"`
- src/schema.py: GeneratedPrompt now has target, title, sections, assumptions, final_prompt, negative_prompt
- src/generator.py: `generate_prompt(content, goal="", target=DEFAULT_TARGET)`, `build_system_prompt(target)`; v2 stubs `ask_clarifying_questions`, `refine_prompt`
- src/guardrails.py: `IMAGE_BLOCKED_PHRASES`; stub `check_image_request`; `check_output` docstring now covers the target's required sections
- app.py: `render_input() -> (target, goal, pasted_text, uploaded_file)`; docstrings for `render_result` and `main` updated
- tests/test_schema.py: rewritten for the new schema (10 cases)
- Added tests/test_targets.py: structural checks on TARGETS (6 cases)

**Commands run:**
- Import smoke test of app and src modules: OK
- `.venv\Scripts\python.exe -m pytest -v`: 29 passed

**Result:** Design in place. extractors.py and schema.py are fully implemented; everything else is still stubs.

**Issues & fixes:** None.

**Decisions:**
- Added tests/test_targets.py, following the one-test-file-per-module rule.
- `assumptions` uses `Field(default_factory=list)`; same behaviour as `= []` in Pydantic, but clearer to readers.
- The schema does not check that `target` is a TARGETS key; `check_output` does, so the schema stays plain data.
- `IMAGE_BLOCKED_PHRASES` maps category → phrases so the message can name the category. Phrase lists can't recognise every real person or character; they are a first line of defence, backed by the "no copyrighted characters, logos or real people" line in the image guidance.
- `BLOCKED_TOPICS` still holds placeholder single words (e.g. "ransomware"); they will be replaced by multi-word phrases when guardrails.py is implemented, as agreed.

**Next steps:**
- Implement guardrails.py with tests.

## 2026-10-20 — Sharpen target guidance + implement guardrails

**Goal:** (1) Make the coding_agent and data_analytics guidance stricter. (2) Implement src/guardrails.py fully, with tests.

**Files changed:**
- src/targets.py: rewrote coding_agent guidance (environment, incremental work, "Do not" list, verification output, ask before ambiguous decisions) and data_analytics guidance (Unity Catalog names, read-only by default, MERGE for idempotent writes, avoid SELECT *, LIMIT while exploring, nulls/duplicates, grain and time zone, validation queries). Structure unchanged.
- src/guardrails.py: implemented every function; added MAX_GOAL_CHARS, SELF_HARM_MESSAGE, INJECTION_PHRASES, PII_PATTERNS, SECRET_PATTERNS, Verhoeff tables, plus helpers `matching_phrases`, `luhn_valid`, `verhoeff_valid`, `has_phone_length`. `check_content` now takes `max_chars`.
- tests/test_targets.py: phrase checks for the new guidance (23 cases)
- tests/test_guardrails.py: new (69 cases)
- samples/pii_sample.txt: UK NI `QQ…` → `AB 12 34 56 C`, PAN `ABCDE1234F` → `ABCPE1234F`, Aadhaar `2345 6789 0123` → `2345 6789 0124`
- samples/README.md: note that the fake IDs are well-formed

**Commands run:**
- `.venv\Scripts\python.exe -m pytest -v`: 122 passed
- redact_pii on samples/pii_sample.txt: all 8 items redacted (EMAIL 1, PHONE 2, CARD 1, US_SSN 1, UK_NI 1, AADHAAR 1, PAN 1); order number, date and total untouched
- find_injection_attempts on samples/injection_sample.txt: ['ignore previous instructions', 'reveal your system prompt']

**Result:** extractors, schema, targets and guardrails are done and tested. generator and app are still stubs.

**Issues & fixes:**
- "Ordinary 12-digit order number must not be flagged", but Aadhaar is 12 digits with optional separators → a regex alone can't tell them apart → validate with the Verhoeff checksum (the official Aadhaar check digit), just as cards use Luhn. A random 12-digit number still passes about 1 time in 10.
- The old sample IDs were not well-formed (QQ is not a valid NI prefix; the 4th PAN letter must be a holder type; the Aadhaar failed Verhoeff) → the precise patterns rightly ignored them → replaced with well-formed fake values.
- The Write tool refused guardrails.py because it had been edited with a script earlier → stale file state → re-read, then wrote.

**Decisions:**
- PII patterns run in a fixed order with PHONE last, so its loose digit groups don't swallow card, SSN or Aadhaar numbers.
- PHONE requires separators and 10–15 digits; `.` is not a separator, so IP addresses, versions and dates aren't redacted. Unformatted runs like `5550100199` are not caught; precision over recall, as agreed.
- US_SSN requires hyphens and excludes invalid ranges (000, 666, 9xx, 00, 0000). UK_NI and PAN use the official letter rules.
- One helper, `matching_phrases`, serves blocked topics, image requests and injection detection: whole words, case-insensitive, any whitespace between words.
- check_output compares section names case-insensitively, because models vary capitalisation.
- Secret messages name the kind of secret but never echo it. Test secrets are built from parts so secret scanners don't flag the test file.
- check_pdf_pages also rejects password-protected PDFs, since extraction would return nothing.
- check_output does not require a negative_prompt for image_generation (not requested; easy to add).

**Next steps:**
- Implement generator.py: get_provider, build_system_prompt(target), parse_response, call_ollama, call_anthropic, describe_image, generate_prompt, with mocked-client tests.
