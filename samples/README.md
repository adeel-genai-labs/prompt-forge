# Sample inputs for manual testing

All names, numbers and records in these files are made up. Use them when trying
PromptForge by hand. Automated tests build their own files in memory and do not use this folder.

| File | What it is | What to check |
|------|------------|---------------|
| `sample.txt` | Short team meeting notes | Plain text extraction and a normal prompt |
| `sample.pdf` | Two-page fictional product brief | Both pages are extracted, in order |
| `sample.docx` | Status report: heading, paragraph and a 3×3 table | Paragraphs and table rows (`Task \| Owner \| Status`) are extracted |
| `pii_sample.txt` | Fake customer record: email, two phone numbers, test card number (4111…), US SSN, UK NI number, Indian Aadhaar and PAN (fake but correctly formatted, and the Aadhaar passes its checksum, so the precise patterns match) | Every item is replaced by a tag such as `[EMAIL]`; the order number, date and total on the last line are **not** redacted |
| `injection_sample.txt` | Report notes with "Ignore previous instructions…" in the middle | The injection check flags it and the model treats it as data, not as an instruction |

`sample.pdf` and `sample.docx` were created with PyMuPDF and python-docx. Recreate them the
same way if they need to change, and keep the data fictional.
