# Python 流水线脚本

在仓库**根目录**执行（`python scripts/…`）。脚本通过 `Path(__file__).resolve().parent.parent` 定位仓库根，从而读取 `prompts/`、`secrets/`、`data/`。

## 一览

| 脚本 | 作用 | 常用参数 |
|------|------|----------|
| `scrub_markdown_pii.py` | MD→MD 脱敏 | `--input-dir` / `--output-dir`、`--overwrite`、`--limit` |
| `process_email_qa.py` | MD → QA JSONL | `--input-dir` / `--output`、`--model`、`--limit` |
| `clean_qa_jsonl.py` | JSONL 二次清洗 | `--src` / `--dst`、`--model`、`--limit`、`--no-resume` |
| `export_jsonl_to_csv.py` | JSONL → CSV | `--src` / `--dst` |

查看全部参数：

```bash
python scripts/scrub_markdown_pii.py --help
python scripts/process_email_qa.py --help
python scripts/clean_qa_jsonl.py --help
python scripts/export_jsonl_to_csv.py --help
```

## 典型顺序

```bash
python scripts/scrub_markdown_pii.py --input-dir data/md_from_eml --output-dir data/md_full
python scripts/process_email_qa.py
python scripts/clean_qa_jsonl.py
python scripts/export_jsonl_to_csv.py
```

**试跑（省 API 调用）**：`process_email_qa.py --limit 3`、`scrub_markdown_pii.py --limit 3`、`clean_qa_jsonl.py --limit 20`。

**全量重跑 QA 蒸馏**：备份或删除 `data/qa_output/email_qa.jsonl` 后再运行 `process_email_qa.py`。  
**全量重跑清洗**：使用 `clean_qa_jsonl.py --no-resume`（会覆盖 `--dst`）。

完整流程与目录约定见根目录 [README.md](../README.md)、[data/README.md](../data/README.md)。
