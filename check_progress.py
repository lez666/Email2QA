import json
from pathlib import Path

"""
简单进度检测脚本：

在项目根目录运行：
    python check_progress.py

作用：
1. 统计 data/support_md_full 下总共有多少个 .md 邮件文件。
2. 统计 data/qa_output/email_qa.jsonl 中已经写出了多少条记录。
3. 粗略估算完成百分比。
"""


def main() -> None:
    project_root = Path(__file__).parent
    data_dir = project_root / "data"

    input_dir = data_dir / "support_md_full"
    output_path = data_dir / "qa_output" / "email_qa.jsonl"

    # 1. 统计待处理邮件总数
    if not input_dir.exists():
        print(f"[ERROR] 目录不存在：{input_dir}")
        return

    md_files = sorted(input_dir.glob("*.md"))
    total_files = len(md_files)

    # 2. 统计已生成记录数
    processed_items = 0
    if output_path.exists():
        with output_path.open("r", encoding="utf-8") as f:
            for _ in f:
                processed_items += 1

    # 3. 估算进度（这里只是“知识条目数 / 邮件数”的粗略比值，不是严格一一对应）
    percent = 0.0
    if total_files > 0:
        percent = min(100.0, (processed_items / total_files) * 100.0)

    print(f"[INFO] support_md_full 中邮件文件总数：{total_files}")
    print(f"[INFO] qa_output/email_qa.jsonl 中已写出记录数：{processed_items}")
    print(f"[INFO] 粗略完成度（记录数 / 文件数）：{percent:.2f}%")


if __name__ == "__main__":
    main()

