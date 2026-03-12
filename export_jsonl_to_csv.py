import json
import csv
from pathlib import Path


"""
将 unitree_knowledge_distilled.jsonl 转成 CSV，方便用 Excel 调整查看。

使用方式（在项目根目录 /home/wasabi/email-to-QA）：
    python export_jsonl_to_csv.py

数据目录约定（所有输入/输出都在 data/ 下）：
    输入：./data/unitree_knowledge_distilled.jsonl
    输出：./data/unitree_knowledge_distilled.csv
"""


def jsonl_to_csv(
    src_path: Path = Path("data") / "unitree_knowledge_distilled.jsonl",
    dst_path: Path = Path("data") / "unitree_knowledge_distilled.csv",
) -> None:
    if not src_path.exists():
        raise FileNotFoundError(f"找不到源文件：{src_path}")

    rows = []
    for line in src_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        data = json.loads(line)
        # 将多行文本压成一行，避免换行把一条记录拆成多行
        def _oneline(v: str | None) -> str:
            if v is None:
                return ""
            return " ".join(str(v).splitlines())

        rows.append(
            {
                "file": data.get("file"),
                "category": data.get("category"),
                "model": data.get("model"),
                "issue": _oneline(data.get("issue")),
                "resolution": _oneline(data.get("resolution")),
                "code_snippet": _oneline(data.get("code_snippet")),
            }
        )

    if not rows:
        print("JSONL 中没有数据，未生成 CSV。")
        return

    # 用 utf-8-sig 方便 Excel 正常识别中文；强制引用，避免逗号/分号导致错列
    with dst_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=list(rows[0].keys()),
            quoting=csv.QUOTE_ALL,
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"已生成 CSV：{dst_path}，共 {len(rows)} 条记录。")


if __name__ == "__main__":
    project_root = Path(__file__).parent
    data_dir = project_root / "data"
    src = data_dir / "unitree_knowledge_distilled.jsonl"
    dst = data_dir / "unitree_knowledge_distilled.csv"
    jsonl_to_csv(src, dst)

