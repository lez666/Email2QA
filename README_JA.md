# Email2QA - Foxmail メールを構造化 QA ナレッジに変換するツール

[中文](README.md) · [English](README_EN.md) · [日本語](README_JA.md)

![Python](https://img.shields.io/badge/python-3.10%2B-blue) ![License](https://img.shields.io/badge/license-MIT-green) ![Status](https://img.shields.io/badge/status-alpha-orange)

## 🚀 プロジェクト背景

サポートエンジニアは、日々つぎのような「非効率な繰り返し作業」に悩まされています：

- 📥 **メール対応**：よく似た問い合わせに、ほぼ同じロジックで何度も回答している  
- 🏗️ **ナレッジの分断**：解決策はすべて過去メールの中に埋もれており、体系的なナレッジとして再利用できない  
- 🌍 **多言語対応**：顧客は世界中におり、日本語・英語以外の言語も混在し、正確な理解とナレッジ化が難しい  

**Email2QA** は、これらのメールを **AI Agent** で自動的にクレンジング・理解・構造化し、  
「手作業による検索」から「自動生成される QA ナレッジ」への移行を実現するためのツールです。

## プロジェクトの目的

Foxmail などのメールクライアントからエクスポートした **`.eml` ファイル**を入力として、  
LLM を用いて **構造化された QA 形式のナレッジ**（`JSONL` / `CSV`）に変換し、  
任意のナレッジベースや RAG システムにそのまま取り込めるようにすることを目的としています。

必要なのは、**（OpenAI 互換の）LLM API キー** だけです。それ以外の処理フローは本プロジェクトで完結します。

---

## ✨ 特長（なぜ Email2QA を使うのか）

| 観点           | 従来の手作業フロー                     | Email2QA 自動化フロー                                     |
| -------------- | -------------------------------------- | --------------------------------------------------------- |
| スピード       | 1 通あたり 約 10 分                   | 非同期バッチ処理で数百〜数千通も数分〜数十分で完了       |
| 多言語対応     | 辞書/翻訳ツールを行き来しながら対応    | LLM が多言語をネイティブに理解し、出力言語も統一可能     |
| 一貫性         | 担当者ごとに文体や項目がバラバラ       | 固定スキーマの QA 形式に整形され、KB/BI への連携が簡単   |
| プライバシー   | メール本文を都度コピー＆ペースト       | ローカル実行とマスキング（メール・注文番号・私的リンク等）に対応 |
| 出力フォーマット | 断片的なテキストで再利用しづらい       | JSONL / CSV に統一してエクスポートし、再集計や検索が容易 |

---

## コアフロー（全体像）

概念的なフローは次の通りです：

```text
Foxmail からエクスポートした .EML
    ↓
[任意] Markdown スレッドへの変換（LLM 不使用、フォーマット変換のみ）
    ↓
LLM によるメール内容の蒸留（QA 形式への変換）
    ↓
JSONL / CSV として出力し、ナレッジベースへ取り込み
```

---

## ディレクトリ構成

### コード（プロジェクトルート）

- `distill_unitree_emails.py`  
  **生メールファイル** から汎用的な技術ナレッジを抽出するスクリプト（非同期・並列）。  
  出力は `data/unitree_knowledge_distilled.jsonl`。

- `process_email_qa.py`  
  **Markdown 形式のメールスレッド** から QA レコードを抽出（単一スレッド・シンプルで安定）。

- `process_email_qa_async.py`  
  上記と同じ処理を **非同期・並列** で実行。大量の `.md` を処理する場合に推奨。

- `clean_qa_jsonl.py`  
  既に生成された QA JSONL を **二次クレンジング** するスクリプト。  
  語調・人称の統一、プライベートストレージ/動画リンクなどの除去を行います。

- `export_jsonl_to_csv.py`  
  任意の JSONL を CSV（Excel で開きやすい形式）に変換。

- `prompts/`  
  各スクリプトが使用する **System Prompt** を格納：
  - `distill_unitree_emails_system.txt`：生メール蒸留用の共通プロンプト
  - `clean_qa_items_system.txt`：QA クレンジング用のプロンプト
  - `process_email_qa_system.txt`：Markdown からの QA 抽出用プロンプト

### データ（`data/` ディレクトリ）

- `email_input/`：Foxmail などからエクスポートした `.eml` を配置  
- `md_full/`：`.eml` から変換した **元のメールスレッドの Markdown**（LLM 未加工）  
- `qa_output/`：
  - `email_qa.jsonl`：Markdown スレッドから抽出された QA データ  
- そのほか：
  - `unitree_knowledge_distilled.jsonl` / `.csv`：生メールから蒸留したナレッジ  
  - `processed_files.log`：蒸留処理の進捗ログ（リジューム用）

※ 実運用では、`data/` 配下の大容量・機微データは `.gitignore` に登録し、GitHub には含めないことを推奨します。

---

## 環境設定

- 推奨 Python バージョン：**3.10 以上**

必要なライブラリのインストール：

```bash
pip install "openai>=1.0.0" "google-genai>=0.2.0" beautifulsoup4 tenacity tqdm
```

---

## OpenAI 互換 API の設定

### 1. 環境変数で設定（推奨）

```bash
export OPENAI_API_KEY="your_openai_api_key"
export OPENAI_MODEL="gpt-5.4"  # 省略可（デフォルトは gpt-5.4）
```

### 2. ローカルファイル `secrets/openai_key.txt` を利用

`secrets/openai_key.txt` を作成し、API キーを 1 行で記入します（Git にはコミットされません）。

---

## 使い方

### ステップ 1：`.eml` ファイルを用意

Foxmail からエクスポートした `.eml` を次のディレクトリに配置します：

```text
data/email_input/
```

### ステップ 2（任意）：`.eml` → Markdown スレッドに変換

読みやすさや再利用性のために、`.eml` を Markdown に変換する場合は、  
任意のツールで変換し、次のディレクトリに保存します：

```text
data/md_full/
```

> 重要：`data/md_full/` のファイルは **LLM で書き換えられていない** 元のスレッドであることを前提としています。

### ステップ 3A：生メールから直接ナレッジを蒸留（任意・フル自動）

生メール（`.eml/.html/.txt/.md` 混在）から、直接ナレッジを抽出したい場合は：

```bash
python distill_unitree_emails.py
```

- 入力：`data/emails/` 配下のファイル  
- 出力：`data/unitree_knowledge_distilled.jsonl`  
- 特徴：署名・メール履歴の削除、簡易的な匿名化などを行い、一般的な技術ナレッジとして保存します。

### ステップ 3B：Markdown メールスレッドから QA を抽出（推奨）

すでに `data/md_full/` に Markdown スレッドが揃っている場合、こちらを利用します。

#### パターン A：単一スレッド版（シンプル・安定）

```bash
python process_email_qa.py
```

- 入力：`data/md_full/` 以下のすべての `.md`  
- 出力：`data/qa_output/email_qa.jsonl`

#### パターン B：非同期並列版（大量データ向け）

```bash
python process_email_qa_async.py
```

- 入力：`data/md_full/` 以下の `.md`  
- 出力：`data/qa_output/email_qa.jsonl`  
- デフォルト並列数：8（`CONCURRENCY` で変更可能）

出力される JSONL の 1 行は次のような形式です：

```json
{
  "file": "email_thread.md",
  "category": "environment | sdk | control | hardware | sensor | other",
  "model": "Go2 / G1 / B2 / ...",
  "issue": "問題の説明（自然言語）",
  "resolution": "解決策・手順",
  "code_snippet": "関連するコード・コマンドなど（あれば）"
}
```

### ステップ 3C：QA の二次クレンジング（任意だが推奨）

ステップ 3A/3B で得られた JSONL に対して、もう一段クレンジングをかけることができます：

- 表現・人称の統一（例：「お客様のメールでは〜」→ 中立的な技術説明に変換）  
- プライベートリンク（個人クラウド・現場動画など）の除去  

例：

```bash
python clean_qa_jsonl.py \
  --src data/qa_output/email_qa.jsonl \
  --dst data/qa_output/temp/knowledge_cleaned.jsonl
```

入力：`file/category/model/issue/resolution/code_snippet` を含む JSONL。  
出力：同じスキーマだが、`issue / resolution / code_snippet` の内容が `prompts/clean_qa_items_system.txt` のルールに従って書き換えられます。

### ステップ 4：CSV へエクスポート（任意）

```bash
python export_jsonl_to_csv.py \
  --src data/unitree_knowledge_distilled.jsonl \
  --dst data/unitree_knowledge_distilled.csv
```

他の JSONL / CSV に対しても、`--src` / `--dst` を指定すれば同様に変換できます。

---

## データとコードの分離ポリシー

- **コード**：プロジェクトルート（`.py` ファイル・`prompts/` など）のみ  
- **データ**：すべて `data/` 配下に集約
  - 生メール：`data/email_input/`
  - Markdown スレッド：`data/md_full/`
  - 蒸留結果：`data/unitree_knowledge_distilled.jsonl` / `.csv`
  - QA 結果：`data/qa_output/email_qa.jsonl` など

これにより、リポジトリをクリーンに保ちつつ、大容量データだけを個別に管理できます。

---

## 注意事項

1. **API キーの安全性**：`secrets/openai_key.txt` は `.gitignore` 済みで、誤ってコミットされないようになっています。  
2. **データの前提**：`process_email_qa*.py` は「Markdown は LLM で加工されていない元データである」ことを前提とし、その旨をプロンプトにも明記しています。  
3. **並列実行**：`process_email_qa_async.py` は非同期 + 並列で API を叩くため、利用している LLM のレートリミットに応じて `CONCURRENCY` を調整してください。  
4. **リジューム**：`distill_unitree_emails.py` は `processed_files.log` を用いた途中再開に対応しています。一方、QA 抽出スクリプトはシンプルな設計で、必要に応じて出力ファイルを消して再実行してください。

---

## ライセンス

本プロジェクトは **MIT License** のもとで公開されています。  
MIT ライセンスの条件に従う範囲で、商用利用を含め自由に利用・改変・再配布することができます。

