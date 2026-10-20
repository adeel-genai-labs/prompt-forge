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
