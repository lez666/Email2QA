# `data/` 目录说明（本地数据放这里）

本目录下的邮件与中间文件**默认不提交到 Git**（见仓库根目录 `.gitignore`）。  
下面约定与 [主 README](../README.md) 中的「新手教程」一致。

## 流水线目录（按处理顺序）

| 路径 | 你要做的事 |
|------|------------|
| **`email_input/`** | **把 Foxmail（或其它客户端）导出的 `.eml` 文件放在这里。** 可建子文件夹分类；批量转换时会递归扫描。 |
| **`md_from_eml/`** | 由 `tools/Toolforeml2QA` 从 `.eml` 转出的 **长 Markdown**（工具自动生成，勿手抄）。 |
| **`md_full/`** | 由 `scripts/scrub_markdown_pii.py` 脱敏后的 Markdown，再给 `scripts/process_email_qa.py` 用。 |
| **`qa_output/`** | QA 抽取结果（如 `email_qa.jsonl`）。 |

## 示例与演示（可随仓库提交）

| 路径 | 说明 |
|------|------|
| **`email_input_demo/`** | **虚构、去标识化** `.eml`（当前 20 封），仅用于测试与展示流程。构造原则见 [email_input_demo/README.md](email_input_demo/README.md)。 |

首次使用若缺少流水线目录，在项目根执行：

```bash
mkdir -p data/email_input data/md_from_eml data/md_full data/qa_output
```

## 和 `tools/Toolforeml2QA` 的配合（摘要）

1. `.eml` → 放进 **`data/email_input/`**。
2. 在项目根执行批量转换，输出到 **`data/md_from_eml/`**：

```bash
chmod +x tools/Toolforeml2QA/batch-eml2md.sh
./tools/Toolforeml2QA/batch-eml2md.sh data/email_input data/md_from_eml
```

3. 后续脱敏、抽 QA 见主 README（`python scripts/…`）。

**依赖**：邮件正文为 **HTML** 时需要系统已安装 **`pandoc`** 并在 `PATH` 中；纯文本正文不依赖 pandoc。
