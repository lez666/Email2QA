# Email2QA - Foxmail メールを構造化 QA ナレッジに変換するツール

[中文](README.md) · [English](README_EN.md) · [日本語](README_JA.md)

![Python](https://img.shields.io/badge/python-3.10%2B-blue) ![License](https://img.shields.io/badge/license-MIT-green) ![Status](https://img.shields.io/badge/status-alpha-orange)

## 概要

処理は大きく三段階に分かれます。

1. **形式変換（LLM 不使用）**：`.eml` → 長い Markdown（**`Toolforeml2QA`**。HTML 本文は **pandoc** で変換）。
2. **オフラインでの MD→MD 脱敏**：内网 GPU やローカルの OpenAI 互換 API 上で実行し、顧客・組織・連絡先などを除去してから次へ。
3. **オンラインでの知識蒸留**：`data/md_full/` を **公開 API** に送り、`prompts/distill_emails_system.txt` で QA JSONL を生成。必要に応じて `clean_qa_jsonl.py` と CSV 出力。

**オフライン用とオンライン用の API キーは別ファイル／環境変数で管理してください。**

---

## 推奨パイプライン

```text
Foxmail 等の .eml
    ↓
Toolforeml2QA（pandoc で HTML→Markdown）
    ↓
data/md_from_eml/
    ↓
scrub_markdown_pii.py（オフライン OpenAI 互換、MD→MD）
    ↓
data/md_full/     ← 以降のみ公网 API に送る想定
    ↓
process_email_qa.py
    ↓
data/qa_output/email_qa.jsonl
    ↓
[任意] clean_qa_jsonl.py → export_jsonl_to_csv.py
```

---

## Toolforeml2QA

**`Toolforeml2QA/`** は単体で動くツールです。HTML 本文には **pandoc** が必要です。詳細は [Toolforeml2QA/README.md](Toolforeml2QA/README.md)。バッチ出力は通常 **`data/md_from_eml/`** に向けます。

---

## スクリプト一覧

| スクリプト | 役割 |
|-----------|------|
| `scrub_markdown_pii.py` | オフライン MD→MD 脱敏 |
| `process_email_qa.py` | `data/md_full/` から QA 抽出（単一スレッド） |
| `process_email_qa_gemini.py` | （任意）Google Gemini で同スキーマ抽出 |
| `clean_qa_jsonl.py` | QA JSONL の二次クレンジング |
| `export_jsonl_to_csv.py` | JSONL → CSV |

### `secrets/`（実キーはコミットしない・**詳細は [`secrets/README.md`](secrets/README.md)**）

クローン後、`*.example.txt` を `*.txt` にコピーして記入。一覧とルールは `secrets/README.md` を参照。

| ファイル | 用途 |
|---------|------|
| `offline_openai_api_key.txt` | オフライン脱敏サービス |
| `offline_openai_base_url.txt` | 任意（OpenAI 互換 Base URL） |
| `openai_key.txt` | **オンライン** API キー |
| `google_api_key.txt` | Gemini（`process_email_qa_gemini.py`） |

環境変数 `OFFLINE_OPENAI_*` / `OPENAI_API_KEY` 等で上書き可能です。

---

## 環境

Python **3.10+** 推奨。形式変換にはシステムに **pandoc** を入れてください。

```bash
pip install -r requirements.txt
```

---

## オフライン脱敏の例

```bash
export OFFLINE_OPENAI_BASE_URL="http://127.0.0.1:8000/v1"
export OFFLINE_OPENAI_API_KEY="local-token"
export OFFLINE_OPENAI_MODEL="モデルID"
python scrub_markdown_pii.py --input-dir data/md_from_eml --output-dir data/md_full
```

---

## オンライン QA 抽出の例

```bash
export OPENAI_API_KEY="your-key"
python process_email_qa.py
```

キーは `secrets/openai_key.txt` の先頭の非コメント行でも可（`sk-` 以外のプレフィックスも可）。

---

## 注意

1. オフライン／オンラインの認証情報を混在させないこと。  
2. `process_email_qa.py` は既存の JSONL に含まれる `file` を読み、該当 `.md` をスキップして再開しやすくしています。全件やり直す場合は JSONL を削除または退避してください。

---

## ライセンス

**MIT License**。MIT の条件の範囲で商用利用を含め自由に利用・改変・再配布できます。
