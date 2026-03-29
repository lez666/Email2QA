# Email2QA - Turn Foxmail Emails into a Structured QA Knowledge Base

[中文](README.md) · [English](README_EN.md) · [日本語](README_JA.md)

![Python](https://img.shields.io/badge/python-3.10%2B-blue) ![License](https://img.shields.io/badge/license-MIT-green) ![Status](https://img.shields.io/badge/status-alpha-orange)

## Background

Support mailboxes are large, multilingual, and privacy-sensitive. This repo splits the work into three stages:

1. **Format conversion (no LLM)**: `.eml` → long Markdown, using **`tools/Toolforeml2QA`** (Python + **pandoc** for HTML bodies).
2. **Deep scrub (MD→MD)**: `scripts/scrub_markdown_pii.py` **defaults to the same credentials as QA** — official **OpenAI** (`OPENAI_API_KEY` / `secrets/openai_key.txt`). For a **local** OpenAI-compatible server (e.g. vLLM), set `OPENAI_BASE_URL` and `OPENAI_MODEL` (see [secrets/README.md](secrets/README.md)).
3. **Distillation (MD→QA JSONL)**: call the API with `prompts/distill_emails_system.txt`, then optionally `scripts/clean_qa_jsonl.py` and `scripts/export_jsonl_to_csv.py`.

Keys live under `secrets/`; scrub and QA **share** `openai_key.txt` by default.

---

## End-to-end pipeline

```text
.eml files → put under data/email_input/
    ↓
tools/Toolforeml2QA (pandoc for HTML → Markdown)
    ↓
data/md_from_eml/
    ↓
scripts/scrub_markdown_pii.py (MD→MD scrub)
    ↓
data/md_full/          ← only from here onward should go to a public API
    ↓
scripts/process_email_qa.py
    ↓
data/qa_output/email_qa.jsonl
    ↓
[optional] scripts/clean_qa_jsonl.py → scripts/export_jsonl_to_csv.py
```

---

## Quick start: where to put `.eml` files

1. **Drop exported `.eml` files into `data/email_input/`** (create the folder if needed). Subfolders are OK; the batch script scans recursively.
2. From the **project root**, run:

```bash
mkdir -p data/email_input data/md_from_eml
chmod +x tools/Toolforeml2QA/batch-eml2md.sh
./tools/Toolforeml2QA/batch-eml2md.sh data/email_input data/md_from_eml
```

3. HTML bodies need **`pandoc`** on `PATH`. Then run scrub → QA as in the sections below.  
**Folder layout:** see **[data/README.md](data/README.md)**.

> **Demo the pipeline without real mail?** Use **`data/email_input_demo/`** (20 fictional `.eml` files). Names, domains, serials, and “business noise” are synthetic placeholders for testing and public demos—**not** real customers. De-identification rationale and safety notes: **[data/email_input_demo/README.md](data/email_input_demo/README.md)**. Use a separate output directory (e.g. `data/md_from_eml_demo`).

---

## Toolforeml2QA (`tools/Toolforeml2QA/`)

Folder **`tools/Toolforeml2QA/`** is self-contained. For HTML parts, **`pandoc`** must be on `PATH`. See [tools/Toolforeml2QA/README.md](tools/Toolforeml2QA/README.md). When using this repo, **input = `data/email_input/`, output = `data/md_from_eml/`**.

---

## `scripts/` (run from repo root: `python scripts/…`)

| Script | Role |
|--------|------|
| `scripts/scrub_markdown_pii.py` | MD→MD scrub (`prompts/scrub_md_pii_system.txt`; same API config as QA by default) |
| `scripts/process_email_qa.py` | QA from `data/md_full/`, single-threaded, append + skip processed files |
| `scripts/clean_qa_jsonl.py` | Second-pass QA rewrite |
| `scripts/export_jsonl_to_csv.py` | JSONL → CSV |

Layout: **[docs/STRUCTURE.md](docs/STRUCTURE.md)**.

### `prompts/`

- `distill_emails_system.txt` — structured QA extraction (online).
- `scrub_md_pii_system.txt` — PII scrub prompt.
- `clean_qa_items_system.txt` — `clean_qa_jsonl.py`.

### `secrets/` (real keys stay local — **see [secrets/README.md](secrets/README.md)**)

After clone, copy `*.example.txt` → `*.txt` and fill in. Full table and rules are in `secrets/README.md`.

| File | Purpose |
|------|---------|
| `openai_key.txt` | OpenAI-compatible API key (shared by scrub, QA, cleaning) |
| `openai_base_url.txt` | Optional custom base URL (proxy / local vLLM); or use `OPENAI_BASE_URL` |

Env: `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_MODEL`, `SCRUB_CONCURRENCY`, etc. See [secrets/README.md](secrets/README.md).

---

## Environment

Python **3.10+** recommended. Format conversion also needs **pandoc** (system install).

```bash
pip install -r requirements.txt
```

---

## MD scrub (`scripts/scrub_markdown_pii.py`)

**Default:** same as QA — official OpenAI (no `OPENAI_BASE_URL`).

```bash
export OPENAI_API_KEY="your-key"   # or secrets/openai_key.txt
export SCRUB_CONCURRENCY="4"      # optional
python scripts/scrub_markdown_pii.py --input-dir data/md_from_eml --output-dir data/md_full
```

**Local OpenAI-compatible server** (e.g. vLLM on GPU):

```bash
export OPENAI_BASE_URL="http://127.0.0.1:8000/v1"
export OPENAI_API_KEY="local"
export OPENAI_MODEL="your-local-model-id"
python scripts/scrub_markdown_pii.py --input-dir data/md_from_eml --output-dir data/md_full
```

You can also put the base URL in `secrets/openai_base_url.txt` (one line). Details: [secrets/README.md](secrets/README.md).

---

## QA extraction (`scripts/process_email_qa.py`)

```bash
export OPENAI_API_KEY="your-key"
export OPENAI_MODEL="gpt-4.1"   # example
python scripts/process_email_qa.py
# python scripts/process_email_qa.py --help
# python scripts/process_email_qa.py --limit 5
```

Or put the key in `secrets/openai_key.txt` (first non-empty, non-`#` line; any prefix OK). Custom endpoint: `OPENAI_BASE_URL` or `openai_base_url.txt`. Paths: `--input-dir`, `--output` (repo-relative or absolute).

---

## Notes

1. Scrub and QA share `openai_key.txt` by default; point `OPENAI_BASE_URL` at a local server only when you intend to run scrub on that host.
2. `scripts/process_email_qa.py` appends to the output JSONL and skips `.md` files whose names already appear in existing records (resume-friendly). Delete the JSONL to force a full rerun.

---

## License

MIT License. Free to use, modify, and distribute (including commercially) under MIT terms.
