import json
import csv
import argparse
from pathlib import Path


"""
通用 JSONL → CSV 转换脚本。

默认行为（在项目根目录）：
    python export_jsonl_to_csv.py
等价于：
    python export_jsonl_to_csv.py \\
        --src data/qa_output/email_qa.jsonl \\
        --dst data/qa_output/email_qa.csv

也可以自定义任意输入/输出路径，例如：
    python export_jsonl_to_csv.py \\
        --src data/qa_output/temp/Enzi'sknowledge.jsonl \\
        --dst data/qa_output/temp/Enzi'sknowledge.csv
"""


def _oneline(v: str | None) -> str:
    """将多行文本压成一行，避免换行把一条记录拆成多行。"""
    if v is None:
        return ""
    return " ".join(str(v).splitlines())


def jsonl_to_csv(src_path: Path, dst_path: Path) -> None:
    if not src_path.exists():
        raise FileNotFoundError(f"找不到源文件：{src_path}")

    rows: list[dict] = []
    for line in src_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        data = json.loads(line)

        # 如果是“知识库”结构，常见字段统一压成一行；否则原样写出
        if all(
            k in data
            for k in (
                "file",
                "category",
                "model",
                "issue",
                "resolution",
                "code_snippet",
            )
        ):
            row = {
                "file": data.get("file"),
                "category": data.get("category"),
                "model": data.get("model"),
                "issue": _oneline(data.get("issue")),
                "resolution": _oneline(data.get("resolution")),
                "code_snippet": _oneline(data.get("code_snippet")),
            }
        else:
            # 通用模式：保持原始 key，不做字段强制约束
            row = {
                k: _oneline(v) if isinstance(v, str) else v
                for k, v in data.items()
            }

        rows.append(row)

    if not rows:
        print("JSONL 中没有数据，未生成 CSV。")
        return

    # 统一字段顺序：用所有 key 的并集，按第一次出现的顺序
    fieldnames: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for k in row.keys():
            if k not in seen:
                seen.add(k)
                fieldnames.append(k)

    # 用 utf-8-sig 方便 Excel 正常识别中文；强制引用，避免逗号/分号导致错列
    dst_path.parent.mkdir(parents=True, exist_ok=True)
    with dst_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
            quoting=csv.QUOTE_ALL,
        )
        writer.writeheader()
        writer.writerows(rows)

    print(
        f"已生成 CSV：{dst_path}，共 {len(rows)} 条记录，字段：{fieldnames}"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="将 JSONL 转换为 CSV。")
    parser.add_argument(
        "--src",
        type=str,
        default="data/qa_output/email_qa.jsonl",
        help="输入 JSONL 文件路径（默认：data/qa_output/email_qa.jsonl）",
    )
    parser.add_argument(
        "--dst",
        type=str,
        default="data/qa_output/email_qa.csv",
        help="输出 CSV 文件路径（默认：data/qa_output/email_qa.csv）",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    project_root = Path(__file__).parent
    src = (project_root / args.src).resolve()
    dst = (project_root / args.dst).resolve()
    jsonl_to_csv(src, dst)
