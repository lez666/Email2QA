# Email2QA - 从 Foxmail 导出邮件到知识库 QA 的完整解决方案

[中文](README.md) · [English](README_EN.md) · [日本語](README_JA.md)

![Python](https://img.shields.io/badge/python-3.10%2B-blue) ![License](https://img.shields.io/badge/license-MIT-green) ![Status](https://img.shields.io/badge/status-alpha-orange)

## 项目背景与目的

技术支持场景下，历史邮件体量大、语种杂、隐私敏感。本项目将流程拆成三段：

1. **格式转换（无 LLM）**：`.eml` → 长 Markdown（依赖 **pandoc**，见下节 `Toolforeml2QA`）。
2. **深度脱敏（MD→MD）**：`scrub_markdown_pii.py` **默认与 QA 抽取相同**，使用 **OpenAI 官方 API**（`OPENAI_API_KEY` / `secrets/openai_key.txt`）；若在内网 GPU 上跑本地兼容服务，只需设置 `OPENAI_BASE_URL` 与 `OPENAI_MODEL`（详见 [`secrets/README.md`](secrets/README.md)）。
3. **知识蒸馏（MD→结构化 QA）**：对已脱敏的 Markdown 调用 API，结合 `prompts/distill_emails_system.txt` 输出 JSONL，可选再跑 QA 清洗与 CSV 导出。

**密钥与端点统一放在 `secrets/`（见该目录 README）；脱敏与 QA 默认共用同一套 `openai_key.txt`，无需单独「离线 key」文件。**

---

## 推荐流水线（总览）

```
Foxmail 等导出的 .eml
    ↓
Toolforeml2QA（Python + pandoc，HTML 正文转 Markdown）
    ↓
data/md_from_eml/     ← 长 Markdown（可先做邮箱等简单处理）
    ↓
scrub_markdown_pii.py（MD→MD 脱敏，默认线上 OpenAI，可改为本机端点）
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

## 新手教程：`.eml` 放哪、接下来怎么做

### 第一步：放好 `.eml` 文件

1. 在项目中使用固定目录：**`data/email_input/`**（没有就新建）。
2. 把 Foxmail 等软件**导出**的 `.eml` **全部复制/移动到这个文件夹里**（可以按主题再分子文件夹，批量工具会递归查找）。
3. 说明：原始 `.eml` 只放在这里即可，**不要**和后面的 `.md` 混在一起，方便对照教程排查问题。

### 第二步：转成 Markdown（无 LLM）

在项目**根目录**（与 `Toolforeml2QA/`、`scrub_markdown_pii.py` 同级）打开终端：

```bash
# 建议先建好输出目录（没有会自动创建，写上更直观）
mkdir -p data/email_input data/md_from_eml

# 批量：左边是放 .eml 的目录，右边是输出的 .md 目录
chmod +x Toolforeml2QA/batch-eml2md.sh
./Toolforeml2QA/batch-eml2md.sh data/email_input data/md_from_eml
```

- 邮件正文是 **HTML** 时，需要先安装 **`pandoc`** 并保证在终端能执行 `pandoc`。
- 只想转一封试跑：`python3 Toolforeml2QA/eml2md.py data/email_input/某封.eml -o data/md_from_eml/某封.md`（详见 [Toolforeml2QA/README.md](Toolforeml2QA/README.md)）。
- **可选**：去掉签名、转发块（会**直接改** md 目录里的文件）  
  `python3 Toolforeml2QA/clean_md_signatures.py data/md_from_eml`

### 第三步～第五步：脱敏 → 抽 QA → 导出

配置好 `secrets/openai_key.txt`（或环境变量）后，按下面「配置说明」「使用步骤摘要」依次执行 `scrub_markdown_pii.py`、`process_email_qa.py` 等即可。

**更细的 `data/` 子目录含义**见 **[data/README.md](data/README.md)**。

---

## Toolforeml2QA（.eml → .md）

目录 **`Toolforeml2QA/`** 为独立小工具。邮件正文为 **HTML** 时，会通过 **pandoc** 转为 GitHub 风格 Markdown。完整选项见 [Toolforeml2QA/README.md](Toolforeml2QA/README.md)。

与本教程配套时：**输入目录用 `data/email_input/`，输出目录用 `data/md_from_eml/`**。

---

## 目录结构（代码与数据）

### 根目录脚本

| 脚本 | 作用 |
|------|------|
| **`scrub_markdown_pii.py`** | MD→MD 脱敏（`prompts/scrub_md_pii_system.txt`；默认与 `process_email_qa` 共用 API 配置） |
| **`process_email_qa.py`** | 从 `data/md_full/` 抽取 QA，**单线程**，支持按已输出记录断点续跑 |
| **`clean_qa_jsonl.py`** | 对已生成的 QA JSONL 二次清洗（口吻与链接等） |
| **`export_jsonl_to_csv.py`** | JSONL → CSV |

### `prompts/`

- **`distill_emails_system.txt`**：邮件线程 → 结构化 QA 的共享系统提示词（线上蒸馏）。
- **`scrub_md_pii_system.txt`**：MD 脱敏用系统提示词。
- **`clean_qa_items_system.txt`**：`clean_qa_jsonl.py` 使用的系统提示词。

### `data/`（默认约定，敏感内容多在 `.gitignore` 中；**说明见 [data/README.md](data/README.md)**）

| 路径 | 含义 |
|------|------|
| **`email_input/`** | **请你把导出的 `.eml` 放在这里**（教程起点） |
| `md_from_eml/` | `Toolforeml2QA` 从 `.eml` 转出的长 Markdown（尚未深度脱敏） |
| `md_full/` | 脱敏后的 Markdown，再给 `process_email_qa.py` 使用 |
| `qa_output/email_qa.jsonl` | QA 抽取结果 |

### `secrets/`（密钥目录，**真实 key 勿提交**）

**完整说明与示例模板见仓库内 [`secrets/README.md`](secrets/README.md)。** 克隆后请本地新建 `openai_key.txt` 等文件（可复制同目录下 `*.example.txt` 再改名、改内容）。

| 文件 | 用途 |
|------|------|
| `openai_key.txt` | OpenAI 兼容 API Key（`process_email_qa`、`scrub_markdown_pii`、`clean_qa_jsonl` 等共用） |
| `openai_base_url.txt` | **可选**，自定义 Base URL（代理 / 本机 vLLM 等）；也可用 `OPENAI_BASE_URL` |

环境变量：`OPENAI_API_KEY`、`OPENAI_BASE_URL`、`OPENAI_MODEL` 等（见 [`secrets/README.md`](secrets/README.md)）。

---

## 环境依赖

建议使用 **Python 3.10+**。

```bash
pip install -r requirements.txt
```

格式转换阶段另需系统安装 **pandoc**（仅 HTML 邮件需要）。

---

## 配置说明

### MD 脱敏（`scrub_markdown_pii.py`）

**默认**：与下面 QA 抽取相同，使用 **OpenAI 官方 API**（未设置 `OPENAI_BASE_URL` 时）。

```bash
export OPENAI_API_KEY="你的_key"   # 或写入 secrets/openai_key.txt
# export OPENAI_MODEL="gpt-5.4"    # 可选，与 process_email_qa 一致
export SCRUB_CONCURRENCY="4"      # 可选，并发数
python scrub_markdown_pii.py --input-dir data/md_from_eml --output-dir data/md_full
```

**改用本机 vLLM / 内网 OpenAI 兼容服务**时，增加端点与模型名即可（Key 仍可用同一 `openai_key.txt`）：

```bash
export OPENAI_BASE_URL="http://127.0.0.1:8000/v1"
export OPENAI_API_KEY="local"           # 按你的本地服务要求填写
export OPENAI_MODEL="你的本地模型 ID"
python scrub_markdown_pii.py --input-dir data/md_from_eml --output-dir data/md_full
```

也可把 Base URL 写入 `secrets/openai_base_url.txt`（一行）。详见 [`secrets/README.md`](secrets/README.md)。

### QA 抽取（`process_email_qa.py`）

```bash
export OPENAI_API_KEY="你的_key"
export OPENAI_MODEL="gpt-4.1"   # 可选，按你的服务商填写
python process_email_qa.py
```

或写入 `secrets/openai_key.txt`（第一行非注释非空即为 Key，**不限定 `sk-` 前缀**，便于兼容代理网关）。若使用自定义端点，同样可设置 `OPENAI_BASE_URL` 或 `secrets/openai_base_url.txt`。

---

## 使用步骤摘要（对应上方「新手教程」）

1. **`.eml` → `data/email_input/`** → 用 **`Toolforeml2QA`** 批量转为 **`data/md_from_eml/`**。
2. **`python scrub_markdown_pii.py`** → 输出 **`data/md_full/`**（内网脱敏可设 `OPENAI_BASE_URL`）。
3. **`python process_email_qa.py`** → **`data/qa_output/email_qa.jsonl`**（支持按已处理文件名续跑）。
4. （可选）**`clean_qa_jsonl.py`** → **`export_jsonl_to_csv.py`**。

**输出 JSONL 每行字段示例**：`file`、`category`、`model`、`issue`、`resolution`、`code_snippet`（与 `distill_emails_system.txt` 中约定一致）。

---

## 数据与代码分离约定

- 代码放在项目根目录；**数据只放在 `data/`** 下对应子目录。
- **不要**将未脱敏的 `md_from_eml` 直接提交到公开仓库；`secrets/` 始终本地保存。

---

## 注意事项

1. **密钥与端点**：脱敏与 QA 默认共用 `openai_key.txt`；仅在内网部署本地推理时，为脱敏步骤设置 `OPENAI_BASE_URL`（及对应模型名），避免误把未脱敏数据发往错误的端点。
2. **`process_email_qa.py`** 若输出 JSONL 已存在，会读取其中已出现的 `file` 并跳过对应 Markdown，适合长时间任务中断后续跑；若要全量重跑，请先删除或移走该 JSONL。

---

## 许可证

本项目采用 **MIT License** 开源协议。你可以在遵守 MIT 协议的前提下自由使用、修改和分发本项目代码（包括商业用途）。
