# Email2QA - 从 Foxmail 导出邮件到知识库 QA 的完整解决方案

[中文](README.md) · [English](README_EN.md) · [日本語](README_JA.md)

![Python](https://img.shields.io/badge/python-3.10%2B-blue) ![License](https://img.shields.io/badge/license-MIT-green) ![Status](https://img.shields.io/badge/status-alpha-orange)

## 项目背景与目的

技术支持场景下，历史邮件体量大、语种杂、隐私敏感。本项目将流程拆成三段：

1. **格式转换（无 LLM）**：`.eml` → 长 Markdown（依赖 **pandoc**，见下节 `Toolforeml2QA`）。
2. **离线深度脱敏（MD→MD，推荐在内网 GPU / 本地 OpenAI 兼容服务上跑）**：进一步去掉客户/公司/联系方式等隐私后，再进入下一步。
3. **线上知识蒸馏（MD→结构化 QA）**：对已脱敏的 Markdown 调用**线上 API**，结合 `prompts/distill_emails_system.txt` 输出 JSONL，可选再跑 QA 清洗与 CSV 导出。

**线上步骤只需配置兼容 OpenAI 协议的 API Key；离线步骤使用单独的环境变量或 `secrets/` 下的专用文件，避免与公网 Key 混放。**

---

## 推荐流水线（总览）

```
Foxmail 等导出的 .eml
    ↓
Toolforeml2QA（Python + pandoc，HTML 正文转 Markdown）
    ↓
data/md_from_eml/     ← 长 Markdown（可先做邮箱等简单处理）
    ↓
scrub_markdown_pii.py（离线 OpenAI 兼容接口，MD→MD）
    ↓
data/md_full/         ← 仅此处及之后的文件适合发往公网 API
    ↓
process_email_qa.py（单线程，顺序处理）
    ↓
data/qa_output/email_qa.jsonl
    ↓
[可选] clean_qa_jsonl.py → export_jsonl_to_csv.py
```

---

## Toolforeml2QA（.eml → .md）

目录 **`Toolforeml2QA/`** 为独立小工具，可复制到任意机器使用。邮件正文为 **HTML** 时，会通过 **pandoc** 转为 GitHub 风格 Markdown（`pandoc` 需在 `PATH` 中）。详见该目录下的 [Toolforeml2QA/README.md](Toolforeml2QA/README.md)。

典型用法：批量将 `.eml` 输出到 **`data/md_from_eml/`**（目录名可按需调整，与离线脚本 `--input-dir` 一致即可）。

---

## 目录结构（代码与数据）

### 根目录脚本

| 脚本 | 作用 |
|------|------|
| **`scrub_markdown_pii.py`** | 离线 MD→MD 脱敏（`prompts/scrub_md_pii_system.txt`） |
| **`process_email_qa.py`** | 从 `data/md_full/` 抽取 QA，**单线程**，支持按已输出记录断点续跑 |
| **`clean_qa_jsonl.py`** | 对已生成的 QA JSONL 二次清洗（口吻与链接等） |
| **`export_jsonl_to_csv.py`** | JSONL → CSV |

### `prompts/`

- **`distill_emails_system.txt`**：邮件线程 → 结构化 QA 的共享系统提示词（线上蒸馏）。
- **`scrub_md_pii_system.txt`**：离线 MD 脱敏用系统提示词。
- **`clean_qa_items_system.txt`**：`clean_qa_jsonl.py` 使用的系统提示词。

### `data/`（默认约定，均在 `.gitignore` 中忽略敏感内容）

| 路径 | 含义 |
|------|------|
| `md_from_eml/` | 工具链从 `.eml` 转出的长 Markdown（尚未深度脱敏） |
| `md_full/` | 离线脱敏后的 Markdown，**仅本目录内容建议接入线上 API** |
| `qa_output/email_qa.jsonl` | QA 抽取结果 |

### `secrets/`（密钥目录，**真实 key 勿提交**）

**完整说明与示例模板见仓库内 [`secrets/README.md`](secrets/README.md)。** 克隆后请本地新建 `openai_key.txt` 等文件（可复制同目录下 `*.example.txt` 再改名、改内容）。

| 文件 | 用途 |
|------|------|
| `offline_openai_api_key.txt` | 离线服务 API Key 或 token（一行；可用 `#` 写注释） |
| `offline_openai_base_url.txt` | 可选，例如 `http://127.0.0.1:8000/v1` |
| `openai_key.txt` | **线上** API Key（一行；可用 `#` 注释） |

也可用环境变量覆盖：`OFFLINE_OPENAI_API_KEY`、`OFFLINE_OPENAI_BASE_URL`、`OFFLINE_OPENAI_MODEL`、`OPENAI_API_KEY`、`OPENAI_MODEL` 等。

---

## 环境依赖

建议使用 **Python 3.10+**。

```bash
pip install -r requirements.txt
```

格式转换阶段另需系统安装 **pandoc**（仅 HTML 邮件需要）。

---

## 配置说明

### 离线脱敏（`scrub_markdown_pii.py`）

```bash
export OFFLINE_OPENAI_BASE_URL="http://127.0.0.1:8000/v1"
export OFFLINE_OPENAI_API_KEY="你的本地token"
export OFFLINE_OPENAI_MODEL="服务中的模型名"
# 可选：并发数
export OFFLINE_SCRUB_CONCURRENCY="4"
python scrub_markdown_pii.py --input-dir data/md_from_eml --output-dir data/md_full
```

未设置环境变量时，从 `secrets/offline_openai_api_key.txt` 与可选的 `secrets/offline_openai_base_url.txt` 读取；未提供 Base URL 时默认 `http://127.0.0.1:8000/v1`。

### 线上 QA 抽取（`process_email_qa.py`）

```bash
export OPENAI_API_KEY="你的线上_key"
export OPENAI_MODEL="gpt-4.1"   # 可选，按你的服务商填写
python process_email_qa.py
```

或写入 `secrets/openai_key.txt`（第一行非注释非空即为 Key，**不限定 `sk-` 前缀**，便于兼容代理网关）。

---

## 使用步骤摘要

1. 将 Foxmail 导出的 `.eml` 用 **`Toolforeml2QA`** 转为 Markdown，放入 **`data/md_from_eml/`**。
2. 在**离线环境**运行 **`python scrub_markdown_pii.py`**，输出到 **`data/md_full/`**。
3. 在可访问**线上 API** 的环境运行 **`python process_email_qa.py`**，得到 **`data/qa_output/email_qa.jsonl`**（已处理过的文件会按输出 JSONL 中的 `file` 字段跳过，便于断点续跑）。
4. （可选）**`clean_qa_jsonl.py`** 二次清洗 → **`export_jsonl_to_csv.py`** 导出 Excel 友好 CSV。

**输出 JSONL 每行字段示例**：`file`、`category`、`model`、`issue`、`resolution`、`code_snippet`（与 `distill_emails_system.txt` 中约定一致）。

---

## 数据与代码分离约定

- 代码放在项目根目录；**数据只放在 `data/`** 下对应子目录。
- **不要**将未脱敏的 `md_from_eml` 直接提交到公开仓库；`secrets/` 始终本地保存。

---

## 注意事项

1. **密钥分离**：离线与线上使用不同文件或环境变量，避免把内网推理服务的 token 与公网 Key 混在同一配置里。
2. **`process_email_qa.py`** 若输出 JSONL 已存在，会读取其中已出现的 `file` 并跳过对应 Markdown，适合长时间任务中断后续跑；若要全量重跑，请先删除或移走该 JSONL。

---

## 许可证

本项目采用 **MIT License** 开源协议。你可以在遵守 MIT 协议的前提下自由使用、修改和分发本项目代码（包括商业用途）。
