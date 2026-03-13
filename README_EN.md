# Email2QA - Turn Foxmail Emails into a Structured QA Knowledge Base

[中文](README.md) · [English](README_EN.md) · [日本語](README_JA.md)

![Python](https://img.shields.io/badge/python-3.10%2B-blue) ![License](https://img.shields.io/badge/license-MIT-green) ![Status](https://img.shields.io/badge/status-alpha-orange)

## 🚀 Background

Support engineers are often trapped in **low‑leverage repetitive work**:

- 📥 **Email triage**: answering very similar technical questions repeatedly, with almost the same logic  
- 🏗️ **Knowledge silos**: gigabytes of valuable solutions are buried in historical mailboxes, impossible to reuse systematically  
- 🌍 **Language barrier**: customers write in many different languages; multi‑lingual understanding and knowledge extraction is hard  

**Email2QA** uses an AI Agent pipeline to move from *manual search* to *automatic knowledge generation*:  
it cleans raw emails, understands them across languages, and restructures them into a consistent QA knowledge base –  
so engineers can focus on building products instead of searching old threads. 🔥

## Project Goal

Provide an end‑to‑end, reproducible way to transform **Foxmail (or similar clients) exported `.eml` emails** into a **structured QA dataset**  
(`JSONL` / `CSV`), ready to be plugged into **any knowledge base or RAG system**.

You only need to bring your own **LLM API key** (OpenAI‑compatible model is fine); the rest is handled by this project.

---

## ✨ Key Advantages

| Dimension      | Manual workflow                          | Email2QA automated pipeline                                      |
| ------------- | ----------------------------------------- | ---------------------------------------------------------------- |
| Speed         | ~10 minutes per email                     | Async batch processing, hundreds or thousands in minutes         |
| Multi‑lingual | Human + dictionary/translator             | LLM natively understands many languages, unified output (e.g. zh/en) |
| Consistency   | Tone & structure vary by engineer         | Stable QA schema and tone, ready for KB / BI tools              |
| Privacy       | Copy‑pasted email content everywhere      | Supports local execution and de‑identification (emails, orders, private links) |
| Output shape  | Scattered text, hard to reuse             | Structured JSONL / CSV, easy to aggregate, query and analyze    |

---

## Core Pipeline

Conceptually, the pipeline looks like this:

```text
Foxmail-exported .EML
    ↓
[Optional] Convert to Markdown threads (no LLM, pure formatting)
    ↓
LLM distillation → structured QA items
    ↓
JSONL / CSV for knowledge base import
```

---

## Folder Layout

### Code (project root)

- `distill_unitree_emails.py`  
  Distill **raw email files** into general technical knowledge (async), writing to `data/unitree_knowledge_distilled.jsonl`.

- `process_email_qa.py`  
  Extract QA items from **Markdown email threads** (single‑threaded, simple and robust).

- `process_email_qa_async.py`  
  Same logic as above, but async and concurrent – recommended for large batches of `.md` threads.

- `clean_qa_jsonl.py`  
  Second‑pass cleaning over existing QA JSONL: unify voice/person, remove private storage/video links, keep KB‑friendly text.

- `export_jsonl_to_csv.py`  
  Convert any JSONL to CSV (Excel‑friendly), with special support for the `file/category/model/issue/resolution/code_snippet` schema.

- `prompts/`  
  System prompts used by different stages:
  - `distill_unitree_emails_system.txt`: shared schema & rules for email distillation
  - `clean_qa_items_system.txt`: rules for QA cleaning / rewriting
  - `process_email_qa_system.txt`: (optional) dedicated prompt for markdown thread QA extraction

### Data (`data/` directory)

- `email_input/`  
  Raw `.eml` files exported from Foxmail (or other email clients).

- `md_full/`  
  Markdown versions of full email threads (converted from `.eml`, **without any prior LLM processing**).

- `qa_output/`  
  Main QA outputs:
  - `email_qa.jsonl`: QA records extracted from markdown threads

- Top‑level knowledge distillation outputs:
  - `unitree_knowledge_distilled.jsonl` / `.csv`: general knowledge distilled from raw emails
  - `processed_files.log`: progress log for resumable runs

> Note: in a real project, large or sensitive data directories under `data/` are typically listed in `.gitignore` and not pushed to GitHub.

---

## Environment

- Recommended **Python 3.10+**

Install dependencies:

```bash
pip install "openai>=1.0.0" "google-genai>=0.2.0" beautifulsoup4 tenacity tqdm
```

---

## OpenAI‑Compatible API Setup

Two options:

### 1. Environment variables (recommended)

```bash
export OPENAI_API_KEY="your_openai_api_key"
export OPENAI_MODEL="gpt-5.4"  # optional, default is gpt-5.4
```

### 2. Local `secrets` file

Create `secrets/openai_key.txt` at project root and put your API key there (not committed to git).

---

## How to Use

### Step 1: Prepare `.eml` files

Place your Foxmail‑exported `.eml` files under:

```text
data/email_input/
```

### Step 2 (optional): Convert `.eml` → Markdown threads

If you prefer working with markdown threads (for better readability or reuse),  
convert `.eml` into `.md` using your own tooling, then place them under:

```text
data/md_full/
```

> Important: markdown files in `data/md_full/` should be **raw, non‑LLM‑generated** representations of email threads.

### Step 3A: Distill from raw emails (optional, highly automated)

If you mainly have **raw emails** in mixed formats (`.eml/.html/.txt/.md`) and don’t want to manually normalize them into markdown threads, run:

```bash
python distill_unitree_emails.py
```

- Input: files under `data/emails/`  
- Output: `data/unitree_knowledge_distilled.jsonl` (can later be converted to CSV)  
- Behavior: performs basic cleaning (remove signatures/history, light de‑identification) and outputs structured knowledge.

### Step 3B: Extract QA from markdown threads (recommended when you already have threads)

If you already have markdown threads in `data/md_full/`, use one of:

#### Option A: Single‑threaded (simple & robust)

```bash
python process_email_qa.py
```

- Input: all `.md` files under `data/md_full/`  
- Output: `data/qa_output/email_qa.jsonl`  

#### Option B: Async + concurrent (recommended for large batches)

```bash
python process_email_qa_async.py
```

- Input: all `.md` files under `data/md_full/`  
- Output: `data/qa_output/email_qa.jsonl`  
- Concurrency: default 8 workers (tunable via `CONCURRENCY` in the script)  

**Output schema** (one JSON per line):

```json
{
  "file": "email_thread.md",
  "category": "environment | sdk | control | hardware | sensor | other",
  "model": "Go2 / G1 / B2 / ...",
  "issue": "Problem description in natural language",
  "resolution": "Solution steps / reasoning",
  "code_snippet": "Relevant code or commands (if any)"
}
```

### Step 3C: Second‑pass QA cleaning (optional, but highly recommended)

Regardless of whether you used 3A or 3B, you can run a second‑pass cleaning to:

- unify tone & perspective (e.g., convert “customer email says…” into neutral technical statements)  
- remove sensitive links (private drives, on‑site videos)  

Example:

```bash
python clean_qa_jsonl.py \
  --src data/qa_output/email_qa.jsonl \
  --dst data/qa_output/temp/knowledge_cleaned.jsonl
```

Input: any JSONL matching the `file/category/model/issue/resolution/code_snippet` pattern.  
Output: same schema, but `issue / resolution / code_snippet` are rewritten according to `prompts/clean_qa_items_system.txt`.

### Step 4: Export to CSV (optional)

```bash
python export_jsonl_to_csv.py \
  --src data/unitree_knowledge_distilled.jsonl \
  --dst data/unitree_knowledge_distilled.csv
```

Or point `--src` / `--dst` at any other JSONL / CSV pair you want.

---

## Data / Code Separation

- **Code** lives only in the project root (`.py` files, prompts, etc.)  
- **Data** lives under `data/`:
  - Raw emails: `data/email_input/`
  - Markdown threads: `data/md_full/`
  - Distilled knowledge: `data/unitree_knowledge_distilled.jsonl` / `.csv`
  - QA outputs: `data/qa_output/email_qa.jsonl` and any temp variants

This keeps the repository clean and makes it easy to ignore large/sensitive data when publishing to GitHub.

---

## Notes

1. **API key safety**: `secrets/openai_key.txt` is git‑ignored by default. Do not commit your real keys.  
2. **Data fidelity**: `process_email_qa*.py` assumes markdown threads are **raw, not LLM‑rewritten**; prompts explicitly tell the model this.  
3. **Concurrency**: `process_email_qa_async.py` uses async + concurrency to speed up large batches; tune `CONCURRENCY` based on your rate limits.  
4. **Resumability**: `distill_unitree_emails.py` is resumable via `processed_files.log`. The QA scripts currently are simpler (restart from scratch or reuse existing outputs).

---

## License

This project is released under the **MIT License**.  
You are free to use, modify and distribute it (including for commercial purposes) under the terms of the MIT license.

