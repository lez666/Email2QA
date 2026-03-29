#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() {
  cat <<'USAGE'
批量把目录里的 .eml 转成 .md（与本目录下的 eml2md.py 配套，可单独拷贝使用）

用法:
  ./batch-eml2md.sh /path/to/eml_dir /path/to/out_dir [-- eml2md.py 额外参数...]

说明:
  - 会递归扫描 eml_dir 下所有 *.eml
  - 输出目录结构与输入保持一致
  - 每个 .eml 生成同名 .md
  - 默认会“断点续跑”：如果目标 .md 已存在则跳过
  - 可用环境变量 BATCH_TIMEOUT_SEC 为单封转换设置超时（例如 60 或 120）
  - 额外参数通过 `--` 之后传给同目录的 eml2md.py（例如 --keep-quoted --keep-signature）
USAGE
}

if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
  usage
  exit 0
fi

IN_DIR="${1:-}"
OUT_DIR="${2:-}"
shift 2 || true

EXTRA_ARGS=()
if [ "${1:-}" = "--" ]; then
  shift
  EXTRA_ARGS=("$@")
fi

if [ -z "$IN_DIR" ] || [ -z "$OUT_DIR" ]; then
  usage >&2
  exit 2
fi

if [ ! -d "$IN_DIR" ]; then
  echo "输入目录不存在: $IN_DIR" >&2
  exit 2
fi

# 绝对路径；cd -P 解析符号链接，否则起始路径为 symlink 时 GNU find 可能不进入子目录（无法匹配任何 .eml）
IN_DIR="$(cd -P "$IN_DIR" && pwd)"
mkdir -p "$OUT_DIR"
OUT_DIR="$(cd -P "$OUT_DIR" && pwd)"

while IFS= read -r -d '' eml; do
  rel="${eml#$IN_DIR/}"
  rel_no_ext="${rel%.eml}"
  out="$OUT_DIR/$rel_no_ext.md"
  mkdir -p "$(dirname "$out")"
  if [ -f "$out" ] && [ -s "$out" ]; then
    echo "SKIP: $rel -> ${out#$OUT_DIR/}"
    continue
  fi

  if [ -n "${BATCH_TIMEOUT_SEC:-}" ]; then
    if timeout "${BATCH_TIMEOUT_SEC}"s python3 "$SCRIPT_DIR/eml2md.py" "$eml" -o "$out" "${EXTRA_ARGS[@]}"; then
      echo "OK: $rel -> ${out#$OUT_DIR/}"
    else
      echo "FAIL: $rel" >&2
      rm -f "$out" || true
    fi
  else
    if python3 "$SCRIPT_DIR/eml2md.py" "$eml" -o "$out" "${EXTRA_ARGS[@]}"; then
      echo "OK: $rel -> ${out#$OUT_DIR/}"
    else
      echo "FAIL: $rel" >&2
      rm -f "$out" || true
    fi
  fi
done < <(find "$IN_DIR" -type f -name '*.eml' -print0)
