<div align="center">

# 📧 Email2QA

**从 Foxmail 导出邮件到知识库 QA 的自动化流水线**

*转换 → 脱敏 → 蒸馏：把凌乱、多语种、含隐私的 `.eml`，变成可入库的结构化 QA。*

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-alpha-orange)](https://github.com/lez666/Email2QA)

[简体中文](README.md) · [English](README_EN.md) · [日本語](README_JA.md)

</div>

---

## 🌟 核心亮点

| | |
| :--- | :--- |
| 🛡️ **隐私可控** | 脱敏步骤 **兼容 OpenAI 接口**：可接 **内网 vLLM / Ollama**（`OPENAI_BASE_URL`），敏感原文不必出内网；也支持默认走云端 API，按合规自选。 |
| 🧩 **格式保真** | HTML 正文经 **pandoc** 转 Markdown，尽量保留代码块、列表与结构（见 `Toolforeml2QA/`）。 |
| 🧠 **面向邮件的 Prompt** | `prompts/distill_emails_system.txt` 等针对技术支持邮件场景调优，输出统一 QA 字段。 |
| ⚡ **断点续跑** | `process_email_qa.py` 会跳过 JSONL 中已出现过的 `file`；`scrub` 支持跳过已生成目标文件（`--overwrite` 可强刷）。 |
| 📁 **目录约定清晰** | **`.eml` 固定放 `data/email_input/`**，其余阶段见下表与 [data/README.md](data/README.md)。 |

---

## 🔄 处理工作流

<div align="center">

![Email2QA 处理工作流：从 email_input 经 Pandoc、脱敏、QA 蒸馏到 qa_output](logicpic.png)

</div>

> **说明**：脱敏与 QA 默认共用 `secrets/openai_key.txt`；若脱敏走内网模型，请为该步骤配置 `OPENAI_BASE_URL` / `openai_base_url.txt`，避免误将敏感 MD 发到错误端点。详见 [secrets/README.md](secrets/README.md)。

---

## 🚀 快速开始

### 1️⃣ 环境准备

```bash
pip install -r requirements.txt
```

- **pandoc**（邮件正文为 HTML 时需要）：  
  `sudo apt install pandoc`（Ubuntu） / `brew install pandoc`（macOS）

### 2️⃣ 放入原始邮件

将 Foxmail 等导出的 **`.eml`** 放入：

```text
data/email_input/
```

（可建子目录分类；没有该文件夹请自行 `mkdir -p data/email_input`。）

### 3️⃣ 三步流水线

**第一步 — EML → Markdown（无 LLM）**

```bash
mkdir -p data/email_input data/md_from_eml
chmod +x Toolforeml2QA/batch-eml2md.sh
./Toolforeml2QA/batch-eml2md.sh data/email_input data/md_from_eml
```

**第二步 — MD 深度脱敏（🛡️ 隐私关键步骤）**

```bash
# 先配置 secrets/openai_key.txt 或 export OPENAI_API_KEY=...
python scrub_markdown_pii.py --input-dir data/md_from_eml --output-dir data/md_full
```

💡 **只想在内网脱敏？** 将 `OPENAI_BASE_URL` 指向本地兼容服务（或写入 `secrets/openai_base_url.txt` 一行），并设置 `OPENAI_MODEL` 为本地模型 ID。示例：

```bash
export OPENAI_BASE_URL="http://127.0.0.1:8000/v1"
export OPENAI_MODEL="你的本地模型"
python scrub_markdown_pii.py --input-dir data/md_from_eml --output-dir data/md_full
```

**第三步 — QA 蒸馏（MD → JSONL）**

```bash
python process_email_qa.py
```

**可选 — 二次清洗与 Excel**

```bash
python clean_qa_jsonl.py --src data/qa_output/email_qa.jsonl --dst data/qa_output/email_qa_cleaned.jsonl
python export_jsonl_to_csv.py --src data/qa_output/email_qa.jsonl --dst data/qa_output/email_qa.csv
```

更细的步骤说明见 **[data/README.md](data/README.md)**；工具链选项见 **[Toolforeml2QA/README.md](Toolforeml2QA/README.md)**。

---

## 📁 `data/` 目录与敏感程度

| 路径 | 用途 | 敏感程度 |
|------|------|:--------:|
| `data/email_input/` | 📥 原始 `.eml` | 🔴 高 |
| `data/md_from_eml/` | 📝 转换后的 MD（仍含隐私） | 🟠 中 |
| `data/md_full/` | ✨ 脱敏后的 MD（可进入下游 API） | 🟢 低 |
| `data/qa_output/` | 💎 QA 结果（JSONL 等） | 🟢 低 |

以上目录默认**不提交**敏感内容到 Git（见 `.gitignore`）。

---

## 🧰 主要脚本与 `prompts/`

| 脚本 | 作用 |
|------|------|
| `scrub_markdown_pii.py` | MD→MD 脱敏（`prompts/scrub_md_pii_system.txt`） |
| `process_email_qa.py` | 从 `data/md_full/` 抽取 QA（单线程、可续跑） |
| `clean_qa_jsonl.py` | QA JSONL 二次清洗 |
| `export_jsonl_to_csv.py` | JSONL → CSV |

**Prompt 文件**：`distill_emails_system.txt`、`scrub_md_pii_system.txt`、`clean_qa_items_system.txt`。

---

## ⚙️ 配置与进阶

- **密钥**：在 `secrets/` 下按 [secrets/README.md](secrets/README.md) 创建 `openai_key.txt`（可复制 `*.example.txt`）。支持任意 **OpenAI 兼容**网关。
- **自定义端点**：`OPENAI_BASE_URL` 或 `secrets/openai_base_url.txt`（代理 / 本机 vLLM）。
- **模型名**：`OPENAI_MODEL`（脱敏与 QA 脚本共用该变量约定）。
- **脱敏并发**：`SCRUB_CONCURRENCY`（默认 4）。

---

## ⚠️ 注意事项

1. 脱敏与 QA **默认共用**同一套 Key；若脱敏只走内网，请显式设置 `OPENAI_BASE_URL`，避免误连公网。
2. `process_email_qa.py` 输出已存在时会按 `file` 字段跳过已处理邮件；全量重跑请先备份或删除原 JSONL。

---

## 🤝 贡献与反馈

若本仓库对你有帮助，欢迎 **Star 🌟**；Bug 与建议请发 **Issue**，改进工具链或 Prompt 欢迎 **Pull Request**。

---

## ⚖️ 许可证

本项目基于 **[MIT License](LICENSE)** 授权。
