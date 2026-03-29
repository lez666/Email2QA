# Python 流水线脚本

在仓库**根目录**执行，例如：

```bash
python scripts/scrub_markdown_pii.py --input-dir data/md_from_eml --output-dir data/md_full
python scripts/process_email_qa.py
```

脚本通过 `PROJECT_ROOT = Path(__file__).resolve().parent.parent` 定位仓库根，从而读取 `prompts/`、`secrets/`、`data/`。

完整流程与参数见根目录 [README.md](../README.md)。
