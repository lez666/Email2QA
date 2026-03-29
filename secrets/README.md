# API Key 存放说明（本地专用目录）

本目录用于在**本机**保存各类密钥与 Base URL，**不要**把含真实密钥的文件提交到 Git。  
克隆仓库后请**自行创建**下列文件（可复制对应的 `*.example.txt` 再改名）。

| 本地文件名 | 用途 | 环境变量（可替代文件） |
|------------|------|-------------------------|
| `openai_key.txt` | **线上** OpenAI 兼容 API（`process_email_qa.py`、`clean_qa_jsonl.py` 等） | `OPENAI_API_KEY` |
| `offline_openai_api_key.txt` | **离线**脱敏服务（`scrub_markdown_pii.py`） | `OFFLINE_OPENAI_API_KEY` |
| `offline_openai_base_url.txt` | 离线服务地址，一行即可，例如 `http://127.0.0.1:8000/v1` | `OFFLINE_OPENAI_BASE_URL` |
| `google_api_key.txt` | Google Gemini（`process_email_qa_gemini.py`） | `GOOGLE_API_KEY` |

## 填写规则

- 每个文件**第一行非空、且不以 `#` 开头的行**即视为密钥或 URL（支持 `#` 注释行）。
- 线上 Key **不限定**必须以 `sk-` 开头，便于兼容自建网关。

## 从示例复制

```bash
cd secrets
cp openai_key.example.txt openai_key.txt
# 编辑 openai_key.txt，写入真实 key 后保存
```

示例文件仅含占位符，可安全存在于仓库中。
