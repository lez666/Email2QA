# Email2QA - 从 Foxmail 导出邮件到知识库 QA 的完整解决方案

## 项目目的

本项目提供一套完整的解决方案，用于将 **从 Foxmail 导出的大量有意义的 .EML 文件**，通过 **LLM 提取成 QA 格式**，最终输出成 **CSV 文件**，方便整理知识库。

**你只需要自己购买 LLM 的 API Key 并接入项目即可使用。**

---

## 核心流程

```
Foxmail 导出的 .EML 文件
    ↓
[可选] 转换为 Markdown 格式（不使用 LLM，纯格式转换）
    ↓
使用 LLM 从 Markdown 邮件中提取结构化知识（QA 格式）
    ↓
输出 JSONL / CSV 格式，用于知识库整理
```

---

## 目录结构

### 代码文件（项目根目录）

- **`process_email_qa.py`**：从 Markdown 格式的邮件线程中抽取 QA（**单线程顺序版**，稳定可靠）
- **`process_email_qa_async.py`**：从 Markdown 格式的邮件线程中抽取 QA（**异步并发版**，速度更快，推荐用于大批量处理）
- **`distill_unitree_emails.py`**：从原始邮件文本中蒸馏技术知识，输出 JSONL（异步并发）
- **`export_jsonl_to_csv.py`**：把 JSONL 转成 CSV，方便用 Excel 查看/编辑
- **`check_progress.py`**：检查处理进度的工具脚本
- **`prompts/`**：集中存放各脚本的系统 Prompt 文本（方便单独调整提示词）
  - `distill_unitree_emails_system.txt`：统一的知识蒸馏提示词（两个脚本都用这个）

### 数据目录（`data/` 下）

- **`email_input/`**：存放从 Foxmail 导出的原始 .EML 文件
- **`md_full/`**：存放完整的 Markdown 格式邮件线程（从 .EML 转换而来，**未经过 LLM 处理**）
- **`qa_output/`**：QA 结果输出目录
  - `email_qa.jsonl`：提取的 QA 数据（JSONL 格式）
- **`unitree_knowledge_distilled.jsonl`** / **`.csv`**：蒸馏后的知识库数据及其 CSV 版本
- **`processed_files.log`**：断点续传日志
- **`secrets/`**：本地保存的 `openai_key.txt`（不应提交到版本库）

---

## 环境依赖

建议使用 **Python 3.10+**。

### 安装依赖

推荐使用 `requirements.txt` 一键安装：

```bash
pip install -r requirements.txt
```

如果你只想手动安装核心依赖，可以参考：

```bash
pip install "openai>=1.0.0" "google-genai>=0.2.0" beautifulsoup4 tenacity tqdm
```

---

## OpenAI API 配置

**两种方式选其一：**

### 方式 1：环境变量（推荐）

```bash
export OPENAI_API_KEY="你的_openai_api_key"
export OPENAI_MODEL="gpt-5.4"  # 可选，默认就是 gpt-5.4
```

### 方式 2：本地 secrets 文件

在项目根目录创建 `secrets/openai_key.txt`，把 API Key 写进去（仅本地使用，不会提交到 Git）。

**注意**：`secrets/openai_key.txt` 在仓库中已有一个示例文件，你需要将其中的占位符替换为你的真实 API Key。

---

## 使用流程

### 步骤 1：准备 .EML 文件

将从 Foxmail 导出的 .EML 文件放入：

```
data/email_input/
```

### 步骤 2：[可选] 将 .EML 转换为 Markdown

如果你需要将 .EML 转换为 Markdown 格式（**不使用 LLM，纯格式转换**），可以使用你习惯的工具或脚本。

转换后的 Markdown 文件放入：

```
data/md_full/
```

**重要提示**：`data/md_full/` 中的 Markdown 文件应该是**未经过 LLM 处理的原始数据**，脚本会直接使用这些原始内容进行知识提取。

### 步骤 3：使用 LLM 提取 QA

#### 方案 A：单线程版本（稳定可靠）

```bash
python process_email_qa.py
```

- 输入：`data/md_full/` 下的所有 `.md` 文件
- 输出：`data/qa_output/email_qa.jsonl`
- 特点：顺序处理，稳定可靠，适合小批量或调试

#### 方案 B：异步并发版本（推荐，速度快）

```bash
python process_email_qa_async.py
```

- 输入：`data/md_full/` 下的所有 `.md` 文件
- 输出：`data/qa_output/email_qa.jsonl`
- 特点：并发处理（默认 8 个并发），速度快，适合大批量处理
- 可通过修改脚本中的 `CONCURRENCY` 变量调整并发数（建议 5~10）

**输出格式**：每行一个 JSON 对象，包含以下字段：

```json
{
  "file": "邮件文件名.md",
  "category": "问题类型（environment/sdk/control/hardware/sensor/other）",
  "model": "机器人型号（Go2/G1/B2等）",
  "issue": "问题描述（中文）",
  "resolution": "解决方案（中文）",
  "code_snippet": "代码片段或关键命令"
}
```

### 步骤 4：导出为 CSV

```bash
python export_jsonl_to_csv.py
```

脚本会读取 `data/unitree_knowledge_distilled.jsonl`（或你指定的 JSONL 文件），生成对应的 CSV 文件，方便用 Excel 打开和编辑。

---

## 检查处理进度

在处理过程中，可以随时运行：

```bash
python check_progress.py
```

查看当前处理进度（已处理的文件数、已生成的记录数等）。

---

## 数据与代码分离约定

- **代码**：只放在项目根目录（`.py` 文件等）
- **数据**：统一放在 `data/` 下，包括：
  - 原始邮件：`data/email_input/`
  - Markdown 邮件：`data/md_full/`
  - 中间结果：`data/unitree_knowledge_distilled.jsonl`、`data/processed_files.log`
  - 导出结果：`data/unitree_knowledge_distilled.csv`、`data/qa_output/email_qa.jsonl`

**主目录只放代码，所有数据统一挂在 `data/` 下对应子目录。**

---

## 注意事项

1. **API Key 安全**：`secrets/openai_key.txt` 已在 `.gitignore` 中，不会被提交到版本库。请妥善保管你的 API Key。

2. **数据来源**：`process_email_qa.py` 和 `process_email_qa_async.py` 处理的数据是**未经过 LLM 处理的原始 Markdown**，脚本会在提示词中明确告知模型这一点。

3. **并发控制**：`process_email_qa_async.py` 默认并发数为 8，可根据你的 API 限速和网络情况调整 `CONCURRENCY` 变量。

4. **断点续传**：`distill_unitree_emails.py` 支持断点续传（通过 `processed_files.log`），但 `process_email_qa.py` 和 `process_email_qa_async.py` 目前不支持，如需重新处理需要清空输出文件。

---

## 许可证

本项目采用 **MIT License** 开源协议。

你可以在遵守 MIT 协议的前提下自由使用、修改和分发本项目代码（包括商业用途）。  
完整条款见仓库根目录的 `LICENSE` 文件。
