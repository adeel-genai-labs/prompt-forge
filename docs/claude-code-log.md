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

## 2026-10-20 — Implement generator + negative_prompt check

**Goal:** Require a negative_prompt for image prompts in check_output; implement src/generator.py (v2 functions stay as stubs).

**Files changed:**
- src/guardrails.py: check_output rejects image_generation prompts with an empty negative_prompt; `check_file` now gets the file extension with `Path` itself instead of importing `extractors.file_extension` (see issues)
- src/generator.py: implemented get_provider, generate_prompt (one retry), describe_image, build_system_prompt, parse_response, call_ollama, call_anthropic; added helpers `build_user_message` and `call_model`, plus constants TEMPERATURE=0.2, ANTHROPIC_MAX_TOKENS=4096, JSON_REMINDER, IMAGE_SYSTEM_PROMPT and IMAGE_USER_PROMPT
- .env.example: added OLLAMA_TEXT_MODEL, OLLAMA_VISION_MODEL, ANTHROPIC_MODEL
- tests/test_generator.py: new (31 cases, all mocked, no network)
- tests/test_guardrails.py: make_prompt gives image prompts a negative_prompt; 3 new cases

**Commands run:**
- Import smoke test of app and src modules: OK
- `.venv\Scripts\python.exe -m pytest -v`: first run 1 failed, 155 passed; after fix 156 passed

**Result:** All src modules are implemented except the v2 stubs. app.py is still a stub. Not yet tried against a live Ollama or the Anthropic API.

**Issues & fixes:**
- Circular import (guardrails → extractors → generator → guardrails) → generator now needs `wrap_as_data` from guardrails → guardrails computes the file extension with `Path` instead of importing from extractors.
- An unknown LLM_PROVIDER was reported as "didn't return a usable prompt" → `generate_prompt`'s `except ValueError` wrapped `call_model`, so get_provider's ValueError was swallowed and retried → only `parse_response` sits inside the try blocks now. Found by test_unknown_provider_gives_friendly_error.

**Decisions:**
- Error types: ValueError for bad settings or unusable model output, RuntimeError when the provider can't be reached or rejects the request. app.py will catch both and show the message.
- `call_model` routes to call_ollama or call_anthropic, so generate_prompt and describe_image don't repeat the provider switch.
- The system prompt includes an example JSON shape with the target's exact section keys; negative_prompt is required for image_generation and set to "" for other targets.
- The goal goes in the user message as the user's own instruction, before the `<user_content>` block, and is never wrapped as data.
- A missing ANTHROPIC_API_KEY, or the placeholder "your-key-here", is caught before any network call.
- Ollama `format="json"` is not used yet, to keep the agreed signatures. It would make small local models much more reliable at returning JSON (candidate for later).
- Local .env was not changed (it may hold the user's key); the new model variables have code defaults, so it still works.

**Next steps:**
- Implement app.py: the Streamlit flow wiring guardrails, extractors and generator, with friendly errors.
- Run a live check with Ollama (`ollama pull llama3.2` and `ollama pull llama3.2-vision`) and with Anthropic.

## 2026-10-20 — Ollama structured outputs + implement app.py

**Goal:** (1) Use Ollama structured outputs (JSON schema) for prompt generation. (2) Implement the Streamlit app with a smoke test.

**Files changed:**
- src/generator.py: `call_ollama(..., json_schema=None)` passes it as `format=`; `call_model` forwards json_schema to Ollama only; `generate_prompt` passes `GeneratedPrompt.model_json_schema()` on both attempts; describe_image sends no schema. Model-name constants replaced by DEFAULT_* plus `model_for(provider, image=False)`, which reads env at call time.
- src/guardrails.py: new `redact_prompt(prompt)`, which redacts PII in every output field and totals the counts
- app.py: fully implemented (load_settings, render_sidebar, render_input, run_pipeline, stop_if, render_report, render_result, to_markdown, slugify, show_error, main)
- tests/test_generator.py: fake call_ollama records json_schema; new tests for the schema on first and retry attempts, no schema for images, `format=` passed to ollama.chat, and model_for defaults and env override
- tests/test_guardrails.py: test for redact_prompt
- Added tests/test_app.py: AppTest smoke test with generate_prompt mocked

**Commands run:**
- `.venv\Scripts\python.exe -m pytest -v`: 163 passed
- `.venv\Scripts\python.exe -m streamlit run app.py --server.headless true --server.port 8599`: health check OK, then stopped

**Result:** The whole app is implemented. Not yet tested end to end with a real Ollama or Anthropic model.

**Issues & fixes:**
- Model names were read at import time, before app.py loads .env / st.secrets → values set in .env would be ignored → `model_for()` reads env when each call is made.
- A multi-edit script failed halfway (one search string didn't match, because of an earlier edit) → each edit writes on its own, so the earlier ones had applied → checked the file and applied the rest.

**Decisions:**
- render_input uses `st.form` (no rerun on every keystroke) and returns None until Generate is pressed, so its return type is `tuple | None`.
- The pipeline order lives in `run_pipeline` in app.py, as requested; guardrail failures raise ValueError through `stop_if`, so main has one place to catch errors.
- The blocked-topic and image checks run on the goal and the content together; PII is redacted from both. Injection detection runs only on the content, since the goal is the user's own instruction.
- Output PII redaction lives in guardrails.redact_prompt, not app.py, to keep business logic out of the UI.
- main() also catches any other Exception, logs the traceback to the terminal and shows a generic friendly message, so users never see a raw traceback.
- st.secrets are copied with `os.environ.setdefault`, so real environment variables win; only string values are copied.
- The app test calls generator.generate_prompt through the module, so monkeypatch takes effect inside AppTest.

**Next steps:**
- Live run: `ollama pull llama3.2` and `ollama pull llama3.2-vision`, then `streamlit run app.py`; try each samples/ file and each target.
- Check that claude-sonnet-5-5 accepts `temperature`.
- v2: ask_clarifying_questions, refine_prompt.

## 2026-10-20 — Strict Ollama schema, output retry, goal-only input

**Goal:** Fix a live-test failure (Ollama/llama3.2 returned an image prompt with no negative_prompt, which check_output rejected) and allow goal-only input.

**Files changed:**
- src/generator.py: new `build_json_schema(target)` (the target's exact section names required as non-empty strings, `additionalProperties: false`, target fixed with an enum, non-empty final_prompt, negative_prompt required and non-empty for image_generation), used instead of the generic schema. `generate_prompt` now runs check_output after parsing and retries once with a follow-up from the new `build_output_retry_message`; at most 3 calls (first attempt + one JSON retry + one output retry). `build_user_message` allows goal-only input (no `<user_content>` block; adds NO_CONTENT_NOTE) and rejects empty input. New constants NO_CONTENT_NOTE and UNUSABLE_REPLY_MESSAGE.
- src/guardrails.py: new `missing_output_fields(prompt)` (shared by check_output and the retry message) and `check_has_input(goal, content)`. check_output's missing-parts messages are now one format: "missing: Tasks, final_prompt, negative_prompt".
- app.py: requires at least one of goal / pasted text / file, and checks content length only when there is content; comment explains why the final check_output is kept; text area label is now "Paste text (optional)".
- tests/test_generator.py: valid_json takes overrides and gives image replies a negative_prompt; new tests for the strict schema per target, output retry (succeeds, fails twice, call budget), the retry message wording, and goal-only / content-only / both / neither.
- tests/test_guardrails.py: tests for missing_output_fields and check_has_input; two message assertions updated to the new format.
- tests/test_app.py: shared mock fixture; new goal-only and empty-input cases.

**Commands run:**
- `.venv\Scripts\python.exe -m pytest -v`: 189 passed (after updating 2 tests that still expected the generic schema)

**Result:** Ollama structured outputs now enforce the target's sections and the negative_prompt; anything that still slips through gets one targeted retry. Goal-only prompts work. Not yet re-tested live.

**Issues & fixes:**
- Image prompt without negative_prompt from llama3.2 → the generic Pydantic schema makes negative_prompt optional and sections a free-form dict, so structured outputs didn't enforce them → per-target strict schema plus one output retry.
- Python edit scripts sent through Bash heredocs turned `\n` into real line breaks (once leaving a syntax error in a test, once leaving a generator edit half-applied) → backslash handling on the Git Bash path → fixed by hand; used the Edit tool for any text with backslashes.

**Decisions:**
- Retry budget is tracked with two flags in one loop, so the limit is exactly one JSON retry plus one output retry, in any order.
- The retry message uses missing_output_fields, so it names the exact missing parts (e.g. `"Tasks" section, final_prompt`). For other check_output failures (unknown target, leaked secret) it passes on check_output's message instead.
- check_output stays in app.py as a final safety check; it can't change the result, because generate_prompt only returns prompts that pass it.
- A file that yields no text, with no goal or pasted text, fails check_has_input with the generic "describe / paste / upload" message.

**Next steps:**
- Re-run the live Ollama test for all three targets, including goal-only.
- Check that claude-sonnet-5-5 accepts `temperature`.

## 2026-10-20 — Scope change: Databricks data & analytics only, plus Groq provider

**Goal:** Narrow PromptForge to one use case (safe, Databricks-ready SQL/analytics prompts), remove the coding and image use cases (preserved by the user in git tag multi-target-v0), add Groq via an OpenAI-compatible provider module, and rebrand.

**Files changed:**
- src/targets.py: only `data_analytics` remains (dict shape kept); DEFAULT_TARGET = "data_analytics"
- src/extractors.py: removed extract_image and IMAGE_MEDIA_TYPES, and the import of generator; added SUPPORTED_EXTENSIONS (txt, md, pdf, docx)
- src/guardrails.py: removed MAX_IMAGE_BYTES, IMAGE_EXTENSIONS, IMAGE_BLOCKED_PHRASES, check_image_request and the negative_prompt checks; ALLOWED_EXTENSIONS = SUPPORTED_EXTENSIONS; check_file uses extractors.file_extension again (no circular import any more)
- src/schema.py: removed the image-only `negative_prompt` field
- Added src/providers.py: PROVIDERS dict (groq), read_api_key, provider_model, call_openai_compatible (JSON mode, max_retries=1, friendly errors)
- src/generator.py: removed describe_image, the vision model and image parameters; SUPPORTED_PROVIDERS = ollama, anthropic + PROVIDERS keys; model_for(provider); call_model routes groq to call_openai_compatible; call_anthropic uses read_api_key and handles 429; system prompt tells the model to keep [EMAIL]-style tags and never guess the original values
- app.py: no target selectbox; render_input returns (goal, pasted_text, uploaded_file); new title "PromptForge for Databricks" and tagline; sidebar shows provider + model; uploads limited to txt/md/pdf/docx; negative prompt display removed
- CLAUDE.md: new scope section (Databricks only, removed targets in tag multi-target-v0), providers.py and targets.py added to Structure
- .env.example: added GROQ_API_KEY and GROQ_TEXT_MODEL; removed OLLAMA_VISION_MODEL
- requirements.txt: added openai (approved by the user)
- samples/: added vague_request.txt and detailed_request.txt; README.md rewritten. No image samples existed, so nothing to delete.
- tests/: test_targets, test_schema, test_generator and test_app rewritten; test_extractors and test_guardrails updated; new test_providers.py

**Commands run:**
- `.venv\Scripts\python.exe -m pip install openai`: installed openai 3.35.1
- `.venv\Scripts\python.exe -m pytest -v`: 175 passed
- redact_pii / find_injection_attempts on the two new samples: no false positives
- grep for leftover image/coding references: only tests asserting they are gone

**Result:** Single-target Databricks app with three providers (ollama, groq, anthropic). Strict schema, output retry and goal-only input (done in the previous entry) carry over. Not yet tested live with Groq.

**Issues & fixes:**
- Removing the targets broke about 60 tests that used coding_agent/image_generation fixtures → expected → rewrote the fixtures around data_analytics, and added tests asserting the removed targets, image types and negative_prompt stay gone.

**Decisions:**
- Removed `negative_prompt` from the schema, not only its checks: it was image-only, and a dead field would confuse the model and the code.
- providers.py holds both the PROVIDERS data and call_openai_compatible, so adding an OpenAI-compatible provider means adding one dict entry.
- `read_api_key` is shared by Groq and Anthropic, so every missing-key message names its env var; "your-key-here" counts as missing.
- openai client `max_retries=1`: the default retries and backoff on 429 could leave the UI spinning; the user gets the rate-limit message quickly instead.
- Anthropic also maps 429 to the same rate-limit message, for consistency.
- Kept sample.txt/pdf/docx for upload testing; README says what they're for in the new scope.
- `run_pipeline` keeps a `target` parameter (default DEFAULT_TARGET), so a future target needs no signature change.

**Next steps:**
- Live test with Groq (GROQ_API_KEY in .env, LLM_PROVIDER=groq) using vague_request.txt, detailed_request.txt and goal-only input.
- Re-test with Ollama llama3.2 on the strict schema.
