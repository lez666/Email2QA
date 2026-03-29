# Email2QA 仓库结构

在仓库**根目录**下打开终端；Python 脚本一律使用 `python scripts/<脚本名>.py`。

## 根目录

| 条目 | 说明 |
|------|------|
| `README.md` / `README_EN.md` / `README_JA.md` | 主文档（中 / 英 / 日） |
| `LICENSE` | MIT |
| `requirements.txt` | Python 依赖 |
| `.gitignore` | Git 忽略规则 |

## `scripts/` — 流水线入口

| 文件 | 作用 |
|------|------|
| `scrub_markdown_pii.py` | MD→MD 脱敏 |
| `process_email_qa.py` | 从 `data/md_full/` 抽取 QA |
| `clean_qa_jsonl.py` | QA JSONL 二次清洗 |
| `export_jsonl_to_csv.py` | JSONL → CSV |

脚本内 `PROJECT_ROOT` 指向仓库根目录，可正确找到 `prompts/`、`secrets/`、`data/`。

## `tools/Toolforeml2QA/` — 格式转换

将 `.eml` 转为 `.md`（HTML 正文依赖 **pandoc**）。可整体拷贝到其它环境独立使用。详见 [tools/Toolforeml2QA/README.md](../tools/Toolforeml2QA/README.md)。

## `prompts/` — 提示词

| 文件 | 使用者 |
|------|--------|
| `distill_emails_system.txt` | QA 蒸馏 |
| `scrub_md_pii_system.txt` | 脱敏 |
| `clean_qa_items_system.txt` | QA 清洗 |

## `secrets/` — 本地密钥

说明与示例模板见 [secrets/README.md](../secrets/README.md)。真实 key **勿提交**。

## `data/` — 数据目录

`data/` 约定、脚本参数与敏感程度见根目录 [README.md](../README.md)（「数据目录」「脚本与参数」）。大文件与隐私内容默认被 `.gitignore` 排除。虚构演示见 **`data/email_input_demo/`**（可随仓库提交）。

## `docs/` — 文档与配图

- **`STRUCTURE.md`**（本文件）：目录与职责说明。
- **`assets/logicpic.png`**：主 README 中的处理工作流配图。
