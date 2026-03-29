# API Key 存放说明（本地专用目录）

本目录用于在**本机**保存各类密钥与可选 Base URL，**不要**把含真实密钥的文件提交到 Git。  
克隆仓库后请**自行创建**下列文件（可复制对应的 `*.example.txt` 再改名）。

## 主配置（与 `process_email_qa.py`、`scrub_markdown_pii.py`、`clean_qa_jsonl.py` 共用）

| 本地文件名 | 用途 | 环境变量（可替代文件） |
|------------|------|-------------------------|
| `openai_key.txt` | **OpenAI 兼容 API Key**（线上官方或任意兼容服务） | `OPENAI_API_KEY` |
| `openai_base_url.txt` | **可选**。仅在使用代理、Azure、或本机 vLLM 时需要自定义端点；一行 URL | `OPENAI_BASE_URL` |

模型名统一用环境变量 **`OPENAI_MODEL`**（各脚本内有默认值，与 `process_email_qa.py` 一致）。

### 脱敏脚本 `scrub_markdown_pii.py` 的默认行为

- **默认**：与 QA 抽取相同，使用 **OpenAI 官方 API**（未设置 `OPENAI_BASE_URL` / `openai_base_url.txt` 时）。
- **改用本机推理（如 4090 + vLLM）**：设置端点与模型即可，Key 仍可写在 `openai_key.txt`：

```bash
export OPENAI_BASE_URL="http://127.0.0.1:8000/v1"
export OPENAI_API_KEY="local"   # 或任意占位，视你的本地服务要求
export OPENAI_MODEL="你的本地模型 ID"
python scrub_markdown_pii.py --input-dir data/md_from_eml --output-dir data/md_full
```

也可把 URL 写入 `openai_base_url.txt`，Key 仍用 `openai_key.txt`。

## 填写规则

- 每个文件**第一行非空、且不以 `#` 开头的行**即视为密钥或 URL（支持 `#` 注释行）。
- Key **不限定**必须以 `sk-` 开头，便于兼容自建网关。

## 从示例复制

```bash
cd secrets
cp openai_key.example.txt openai_key.txt
# 编辑 openai_key.txt，写入真实 key 后保存
```

示例文件仅含占位符，可安全存在于仓库中。
