# Email2QA - Turn Foxmail Emails into a Structured QA Knowledge Base

[中文](README.md) · [English](README_EN.md) · [日本語](README_JA.md)

![Python](https://img.shields.io/badge/python-3.10%2B-blue) ![License](https://img.shields.io/badge/license-MIT-green) ![Status](https://img.shields.io/badge/status-alpha-orange)

## Background

Support mailboxes are large, multilingual, and privacy-sensitive. This repo splits the work into three stages:

1. **Format conversion (no LLM)**: `.eml` → long Markdown, using **`Toolforeml2QA`** (Python + **pandoc** for HTML bodies).
2. **Offline deep scrub (MD→MD)**: run on an air-gapped GPU box or a local OpenAI-compatible server; remove customer/org/contact details before anything touches a public API.
3. **Online distillation (MD→QA JSONL)**: call your **cloud API** with `prompts/distill_emails_system.txt`, then optionally `clean_qa_jsonl.py` and `export_jsonl_to_csv.py`.

Use **separate** env vars / `secrets/` files for offline vs online keys.

---

## End-to-end pipeline

```text
.eml from Foxmail
    ↓
Toolforeml2QA (pandoc for HTML → Markdown)
    ↓
data/md_from_eml/
    ↓
scrub_markdown_pii.py (offline OpenAI-compatible API, MD→MD)
    ↓
data/md_full/          ← only from here onward should go to a public API
    ↓
process_email_qa.py
    ↓
data/qa_output/email_qa.jsonl
    ↓
[optional] clean_qa_jsonl.py → export_jsonl_to_csv.py
```

---

## Toolforeml2QA

Folder **`Toolforeml2QA/`** is self-contained. For HTML parts, **`pandoc`** must be on `PATH`. See [Toolforeml2QA/README.md](Toolforeml2QA/README.md). Typical batch output goes to **`data/md_from_eml/`** (or any dir you pass to `--input-dir`).

---

## Scripts (project root)

| Script | Role |
|--------|------|
| `scrub_markdown_pii.py` | Offline MD→MD scrub (`prompts/scrub_md_pii_system.txt`) |
| `process_email_qa.py` | QA from `data/md_full/`, single-threaded, append + skip processed files |
| `process_email_qa_gemini.py` | (Optional) Same QA schema via Google Gemini |
| `clean_qa_jsonl.py` | Second-pass QA rewrite |
| `export_jsonl_to_csv.py` | JSONL → CSV |

### `prompts/`

- `distill_emails_system.txt` — structured QA extraction (online).
- `scrub_md_pii_system.txt` — offline scrub.
- `clean_qa_items_system.txt` — `clean_qa_jsonl.py`.

### `secrets/` (real keys stay local — **see [`secrets/README.md`](secrets/README.md)**)

After clone, copy `*.example.txt` → `*.txt` and fill in. Full table and rules are in `secrets/README.md`.

| File | Purpose |
|------|---------|
| `offline_openai_api_key.txt` | Offline scrub service |
| `offline_openai_base_url.txt` | Optional OpenAI-compatible base URL |
| `openai_key.txt` | **Online** API key |
| `google_api_key.txt` | Gemini (`process_email_qa_gemini.py`) |

Env overrides: `OFFLINE_OPENAI_*`, `OPENAI_API_KEY`, `OPENAI_MODEL`, etc.

---

## Environment

Python **3.10+** recommended. Format conversion also needs **pandoc** (system install).

```bash
pip install -r requirements.txt
```

---

## Offline scrub

```bash
export OFFLINE_OPENAI_BASE_URL="http://127.0.0.1:8000/v1"
export OFFLINE_OPENAI_API_KEY="local-token"
export OFFLINE_OPENAI_MODEL="your-model-id"
python scrub_markdown_pii.py --input-dir data/md_from_eml --output-dir data/md_full
```

Default base URL if unset: `http://127.0.0.1:8000/v1`.

---

## Online QA extraction

```bash
export OPENAI_API_KEY="your-key"
export OPENAI_MODEL="gpt-4.1"   # example
python process_email_qa.py
```

Or put the key in `secrets/openai_key.txt` (first non-empty, non-`#` line; any prefix OK).

---

## Notes

1. Keep offline and online credentials separate.
2. `process_email_qa.py` appends to the output JSONL and skips `.md` files whose names already appear in existing records (resume-friendly). Delete the JSONL to force a full rerun.

---

## License

MIT License. Free to use, modify, and distribute (including commercially) under MIT terms.
