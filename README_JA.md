# Email2QA - Foxmail メールを構造化 QA ナレッジに変換するツール

[中文](README.md) · [English](README_EN.md) · [日本語](README_JA.md)

![Python](https://img.shields.io/badge/python-3.10%2B-blue) ![License](https://img.shields.io/badge/license-MIT-green) ![Status](https://img.shields.io/badge/status-alpha-orange)

## 概要

処理は大きく三段階に分かれます。

1. **形式変換（LLM 不使用）**：`.eml` → 長い Markdown（**`tools/Toolforeml2QA`**。HTML 本文は **pandoc** で変換）。
2. **MD→MD 脱敏**：`scripts/scrub_markdown_pii.py` は **デフォルトで QA 抽出と同じ** OpenAI 公式 API（`OPENAI_API_KEY` / `secrets/openai_key.txt`）。**ローカル**の互換 API（vLLM 等）を使う場合は `OPENAI_BASE_URL` と `OPENAI_MODEL` を設定（[`secrets/README.md`](secrets/README.md)）。
3. **知識蒸留**：`data/md_full/` を API に送り、`prompts/distill_emails_system.txt` で QA JSONL を生成。必要に応じて `scripts/clean_qa_jsonl.py` と CSV 出力。

**脱敏と QA はデフォルトで `openai_key.txt` を共有します。**

---

## 推奨パイプライン

```text
.eml を data/email_input/ に置く
    ↓
tools/Toolforeml2QA（pandoc で HTML→Markdown）
    ↓
data/md_from_eml/
    ↓
scripts/scrub_markdown_pii.py
    ↓
data/md_full/     ← 以降のみ公网 API に送る想定
    ↓
scripts/process_email_qa.py
    ↓
data/qa_output/email_qa.jsonl
    ↓
[任意] scripts/clean_qa_jsonl.py → scripts/export_jsonl_to_csv.py
```

---

## はじめに：`.eml` の置き場所

1. Foxmail 等からエクスポートした **`.eml` を `data/email_input/` に置く**（なければ作成）。サブフォルダ可。
2. **プロジェクトルート**で：

```bash
mkdir -p data/email_input data/md_from_eml
chmod +x tools/Toolforeml2QA/batch-eml2md.sh
./tools/Toolforeml2QA/batch-eml2md.sh data/email_input data/md_from_eml
```

3. HTML 本文には **`pandoc`** が必要。その後は脱敏→QA。フォルダ説明は **[data/README.md](data/README.md)**。

---

## Toolforeml2QA（`tools/Toolforeml2QA/`）

**`tools/Toolforeml2QA/`** は単体で動くツールです。HTML 本文には **pandoc** が必要です。本リポジトリでは **入力 `data/email_input/`、出力 `data/md_from_eml/`** を推奨。詳細は [tools/Toolforeml2QA/README.md](tools/Toolforeml2QA/README.md)。

---

## `scripts/`（ルートで `python scripts/…`）

| スクリプト | 役割 |
|-----------|------|
| `scripts/scrub_markdown_pii.py` | MD→MD 脱敏（デフォルトは QA と同じ API 設定） |
| `scripts/process_email_qa.py` | `data/md_full/` から QA 抽出（単一スレッド） |
| `scripts/clean_qa_jsonl.py` | QA JSONL の二次クレンジング |
| `scripts/export_jsonl_to_csv.py` | JSONL → CSV |

レイアウト：[docs/STRUCTURE.md](docs/STRUCTURE.md)

### `secrets/`（実キーはコミットしない・**詳細は [`secrets/README.md`](secrets/README.md)**）

クローン後、`*.example.txt` を `*.txt` にコピーして記入。一覧とルールは `secrets/README.md` を参照。

| ファイル | 用途 |
|---------|------|
| `openai_key.txt` | OpenAI 互換 API キー（脱敏・QA・清洗で共有） |
| `openai_base_url.txt` | 任意（プロキシ／ローカル vLLM 等）。または `OPENAI_BASE_URL` |

環境変数 `OPENAI_API_KEY`、`OPENAI_BASE_URL`、`OPENAI_MODEL`、`SCRUB_CONCURRENCY` 等。詳細は [`secrets/README.md`](secrets/README.md)。

---

## 環境

Python **3.10+** 推奨。形式変換にはシステムに **pandoc** を入れてください。

```bash
pip install -r requirements.txt
```

---

## MD 脱敏（`scripts/scrub_markdown_pii.py`）

**デフォルト**：QA 抽出と同じく **OpenAI 公式 API**（`OPENAI_BASE_URL` 未設定時）。

```bash
export OPENAI_API_KEY="your-key"
export SCRUB_CONCURRENCY="4"   # 任意
python scripts/scrub_markdown_pii.py --input-dir data/md_from_eml --output-dir data/md_full
```

**ローカル互換 API**（例：vLLM）を使う場合：

```bash
export OPENAI_BASE_URL="http://127.0.0.1:8000/v1"
export OPENAI_API_KEY="local"
export OPENAI_MODEL="ローカルモデルID"
python scripts/scrub_markdown_pii.py --input-dir data/md_from_eml --output-dir data/md_full
```

Base URL は `secrets/openai_base_url.txt` に 1 行で書いても可。詳細は [`secrets/README.md`](secrets/README.md)。

---

## QA 抽出の例

```bash
export OPENAI_API_KEY="your-key"
python scripts/process_email_qa.py
```

キーは `secrets/openai_key.txt` の先頭の非コメント行でも可（`sk-` 以外のプレフィックスも可）。カスタム端点は `OPENAI_BASE_URL` または `openai_base_url.txt`。

---

## 注意

1. 脱敏と QA はデフォルトで同じ `openai_key.txt` を使う。ローカル推論だけに向ける場合は `OPENAI_BASE_URL` を明示すること。  
2. `scripts/process_email_qa.py` は既存の JSONL に含まれる `file` を読み、該当 `.md` をスキップして再開しやすくしています。全件やり直す場合は JSONL を削除または退避してください。

---

## ライセンス

**MIT License**。MIT の条件の範囲で商用利用を含め自由に利用・改変・再配布できます。
