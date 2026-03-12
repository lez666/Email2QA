## 项目简介

这个仓库用于将 Unitree 技术支持相关邮件/Markdown 文档整理成结构化数据，方便后续用于检索、分析或接入 RAG / 知识库系统。  
主要包含两条处理链路：

- **邮件 → 结构化知识 JSONL → CSV**
- **Markdown 邮件 → QA JSONL**

所有输入/输出数据统一存放在 `data/` 目录下，代码只放在项目根目录。

---

## 目录结构（简要）

- **distill_unitree_emails.py**：从原始邮件文本中蒸馏技术知识，输出 JSONL。
- **export_jsonl_to_csv.py**：把蒸馏后的 JSONL 转成 CSV，方便用 Excel 查看/编辑。
- **process_email_qa.py**：从 Markdown 格式的技术支持邮件中抽取 QA 对。
- **prompts/**：集中存放各脚本的系统 Prompt 文本（方便单独调整提示词）。
- **data/**：所有输入/输出数据目录（请不要把数据直接放在项目根目录）。
  - **emails/**：原始技术支持邮件文件（.eml/.html/.txt/.md 等）。
  - **support_md_full/**：Markdown 格式的完整邮件线程。
  - **qa_output/**：QA 结果输出目录。
  - **unitree_knowledge_distilled.jsonl / .csv**：蒸馏后的知识库数据及其 CSV 版本。
  - **processed_files.log**：`distill_unitree_emails.py` 的断点续传日志。
  - **support_md_full_index.txt**：对 `support_md_full/` 的索引（如有需要可自行维护）。
  - **1/**、**2/**：历史或多轮实验结果备份，可根据需要保留/清理。
- **secrets/**：本地保存的 `openai_key.txt`，不应提交到版本库。

---

## 环境依赖

建议使用 Python 3.10+。

- **通用依赖**
  - `openai>=1.0.0`
- **仅 distill_unitree_emails.py 需要**
  - `beautifulsoup4`
  - `tenacity`
  - `tqdm`

示例安装（可根据自己环境调整）：

```bash
pip install "openai>=1.0.0" beautifulsoup4 tenacity tqdm
```

---

## OpenAI API 配置

三种方式选其一：

- **环境变量方式（推荐）**

```bash
export OPENAI_API_KEY="你的_openai_api_key"
export OPENAI_BASE_URL="https://api.openai.com/v1"  # 如用官方云可省略
```

- **本地 secrets 文件**

在项目根目录创建 `secrets/openai_key.txt`，把 API Key 写进去（仅本地使用，不要提交到 Git）。

---

## 流程一：邮件 → 结构化知识（JSONL / CSV）

### 1. 准备数据

- 将 1500 封（或任意数量）原始邮件文件放入：
  - `data/emails/` 目录下
  - 支持 `.eml` / `.html` / `.htm` / `.txt` / `.md` 等扩展名

### 2. 运行蒸馏脚本

在项目根目录执行：

```bash
python distill_unitree_emails.py
```

脚本会：

- 从 `data/emails/` 读取邮件内容，做清洗、脱敏、去历史回复等。
- 调用 OpenAI 模型，抽取有价值的技术知识点。
- 按行写入 `data/unitree_knowledge_distilled.jsonl`（每行一个 JSON 对象）。
- 记录已处理文件名到 `data/processed_files.log`，支持断点续传。

可以多次运行脚本，它会跳过已经出现在 `processed_files.log` 里的文件。

### 3. 导出 CSV

当 `data/unitree_knowledge_distilled.jsonl` 生成后，可执行：

```bash
python export_jsonl_to_csv.py
```

脚本会：

- 从 `data/unitree_knowledge_distilled.jsonl` 读取每一条记录。
- 把多行文本压成单行，避免 CSV 换行导致错列。
- 生成 `data/unitree_knowledge_distilled.csv`，使用 `utf-8-sig` 编码，方便 Excel 打开。

---

## 流程二：Markdown 邮件 → QA JSONL

### 1. 准备 Markdown 邮件

- 将已经整理好的 Markdown 格式邮件线程放入：
  - `data/support_md_full/` 目录下
  - 每封/每个线程一个 `.md` 文件

（如有需要，可用 `data/support_md_full_index.txt` 维护索引/说明。）

### 2. 抽取 QA

在项目根目录执行：

```bash
python process_email_qa.py
```

脚本会：

- 遍历 `data/support_md_full/` 下所有 `.md` 文件。
- 调用 OpenAI 模型，从每个邮件线程中抽取若干条 QA。
- 将结果写入 `data/qa_output/email_qa.jsonl`，每行一条记录，形如：
  - `{"source_file": "xxx.md", "qa": {...}}`

如果想先只处理部分文件，可以在 `process_email_qa.py` 中将 `limit_files=None` 改成一个整数（比如 `20`）。

---

## 数据与代码分离约定

- **代码**：只放在项目根目录（`.py` 文件等）。
- **数据**：统一放在 `data/` 下，包括：
  - 原始邮件：`data/emails/`
  - Markdown 邮件：`data/support_md_full/`
  - 中间结果：`data/unitree_knowledge_distilled.jsonl`、`data/processed_files.log`
  - 导出结果：`data/unitree_knowledge_distilled.csv`、`data/qa_output/email_qa.jsonl`
  - 其他实验/备份：`data/1/`、`data/2/` 等

后续如果增加新的脚本或数据类型，建议也遵循相同约定：  
**主目录只放代码，所有数据统一挂在 `data/` 下对应子目录。**

