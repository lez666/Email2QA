# Toolforeml2QA

独立工具集：把 `.eml` 转为 `.md`，可选批量后处理。不依赖本仓库其它路径；将整个目录拷走即可使用。

## 在本仓库中的推荐路径（Email2QA 主项目）

与主仓库 [README](../../README.md) 约定一致时：

| 步骤 | 目录 |
|------|------|
| 放置 Foxmail 等导出的 `.eml` | **`data/email_input/`** |
| 批量转换输出的 `.md` | **`data/md_from_eml/`** |

在项目根目录执行示例：

```bash
mkdir -p data/email_input data/md_from_eml
chmod +x tools/Toolforeml2QA/batch-eml2md.sh
./tools/Toolforeml2QA/batch-eml2md.sh data/email_input data/md_from_eml
```

更完整的「新手教程」与 `data/` 目录说明见仓库根目录 **[README.md](../../README.md)**。

## 依赖

- Python 3（仅用标准库）
- `pandoc` 在 `PATH` 中（仅当邮件正文为 HTML 时需要）

## 用法

在本目录下执行（或写全路径）：

### 单封邮件

```bash
python3 eml2md.py /path/to/mail.eml -o /path/to/mail.md
```

常用选项：`--stdout`、`--no-headers`、`--keep-quoted`、`--keep-signature`。详见 `python3 eml2md.py -h`。

### 批量（递归目录）

```bash
chmod +x batch-eml2md.sh
./batch-eml2md.sh /path/to/eml_dir /path/to/out_md_dir
```

保留引用与签名的批量示例：

```bash
BATCH_TIMEOUT_SEC=120 ./batch-eml2md.sh /path/to/eml_dir /path/to/out_md_dir -- --keep-quoted --keep-signature
```

### 后处理：清理签名与转发头（就地改 `.md`）

```bash
python3 clean_md_signatures.py /path/to/md_dir
```

## 文件说明

| 文件 | 作用 |
|------|------|
| `eml2md.py` | 单封 `.eml` → `.md` |
| `batch-eml2md.sh` | 批量调用 `eml2md.py` |
| `clean_md_signatures.py` | 递归清理目录内 `.md` 中的签名/转发块 |
