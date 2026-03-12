import os
import json
from pathlib import Path

from openai import OpenAI, APIConnectionError


"""
使用说明（简版）：

1. 在终端设置环境变量（或在代码里直接写入 API Key）：
   export OPENAI_API_KEY="你的_openai_api_key"

2. 在项目根目录执行：
   python process_email_qa.py

3. 数据目录约定（所有输入/输出都在 data/ 下）：
   - 输入：遍历 ./data/md_full 下的所有 .md 邮件文件（这些是未经过 LLM 处理的原始 Markdown）
   - 输出：./data/qa_output/email_qa.jsonl（每行一条 QA 记录，JSON 格式）

你可以之后再把 qa_output/email_qa.jsonl 导入到自己的知识库系统。
"""


PROJECT_ROOT = Path(__file__).parent
PROMPT_DIR = PROJECT_ROOT / "prompts"

# 模型名称优先从环境变量 OPENAI_MODEL 读取，便于在不同环境下灵活切换；
# 未设置时默认使用最新的 GPT-5.4 模型。
DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.4").strip() or "gpt-5.4"


def load_prompt(filename: str) -> str:
    """从 prompts/ 目录加载系统提示词文本。"""
    path = PROMPT_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"找不到提示词文件：{path}")
    return path.read_text(encoding="utf-8")


def load_api_key() -> str:
    """
    优先从环境变量读取 OPENAI_API_KEY，
    如果没有，则尝试从 ./secrets/openai_key.txt 读取（仅在本地保存，不要进版本控制）。
    """
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if key:
        return key

    key_path = Path(__file__).parent / "secrets" / "openai_key.txt"
    if key_path.exists():
        return key_path.read_text(encoding="utf-8").strip()

    raise RuntimeError("未找到 OPENAI_API_KEY，请正确配置。")


def get_client() -> OpenAI:
    api_key = load_api_key()
    return OpenAI(api_key=api_key)


def build_prompt(email_markdown: str, filename: str) -> list:
    """
    构造给 OpenAI 的对话消息，指导模型从邮件线程中抽取 QA。
    返回的是 chat.completions 需要的 messages 列表。
    """
    # 统一使用 distill_unitree_emails_system.txt 中定义的 schema 与规则，
    # 这样无论是直接处理原始邮件还是 markdown 线程，最终结构都是
    # { "items": [ { "category", "model", "issue", "resolution", "code_snippet" }, ... ] }。
    system_msg = {
        "role": "system",
        "content": load_prompt("distill_unitree_emails_system.txt"),
    }

    user_msg = {
        "role": "user",
        "content": (
            f"下面是一个 Markdown 格式的技术支持邮件线程内容（文件名：{filename}）。"
            "这些数据是直接从邮件转换而来的原始 Markdown，未经过任何 LLM 处理。\n\n"
            "---------------- 原始邮件开始 ----------------\n"
            f"{email_markdown}\n"
            "---------------- 原始邮件结束 ----------------\n\n"
            "请严格按照系统提示词中的要求，返回一个 JSON 对象，形如："
            '{ "items": [ { "category": "...","model": "...","issue": "...","resolution": "...","code_snippet": "..." }, ... ] }。'
        ),
    }
    return [system_msg, user_msg]


def extract_qa_from_email(
    client: OpenAI, email_text: str, filename: str, model: str = DEFAULT_MODEL
):
    """
    调用 OpenAI 模型，从单封（包含线程）的邮件文本中抽取 QA 列表。
    返回 Python 对象（list[dict]）。
    """
    messages = build_prompt(email_text, filename)

    # 简单重试 3 次，避免偶发网络抖动导致整个流程中断
    last_err: Exception | None = None
    for attempt in range(3):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.1,
            )
            break
        except APIConnectionError as e:
            last_err = e
            print(f"[WARN] API 连接错误，第 {attempt + 1} 次重试中，文件：{filename}")
    else:
        # 连续重试失败，返回空结果但不中断整体流程
        print(f"[ERROR] API 连接多次失败，跳过该文件：{filename}，错误：{last_err}")
        return []

    # 因为我们在系统提示里要求返回「顶层是数组」，这里统一解析为 JSON
    content = resp.choices[0].message.content
    if not content:
        return []

    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        # 如果解析失败，简单略过这封邮件，避免整个流程中断
        print(f"[WARN] 解析 JSON 失败，文件：{filename}")
        return []

    # 兼容多种返回结构：
    # 1) 顶层就是数组： [...]
    # 2) 顶层是对象，里面有 items 字段：{ "items": [...] }
    # 3) 顶层是对象，里面有 data / qa / qas 等字段时，也尽量取数组
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        if "items" in data and isinstance(data["items"], list):
            items = data["items"]
        elif "qa" in data and isinstance(data["qa"], list):
            items = data["qa"]
        elif "qas" in data and isinstance(data["qas"], list):
            items = data["qas"]
        elif "data" in data and isinstance(data["data"], list):
            items = data["data"]
        else:
            # 调试输出一小段原始内容，方便后续根据实际返回结构做适配
            preview = (content[:200] + "...") if len(content) > 200 else content
            print(f"[WARN] 模型返回对象中未找到数组字段，文件：{filename}，content 预览：{preview}")
            return []
    else:
        print(f"[WARN] 模型返回的顶层既不是数组也不是对象，文件：{filename}")
        return []

    return items


def process_directory(
    input_dir: Path,
    output_path: Path,
    model: str = DEFAULT_MODEL,
    limit_files: int | None = None,
) -> None:
    """
    遍历目录下的所有 .md 文件，抽取 QA 并写入 JSONL。

    - input_dir: 存放邮件 markdown 的目录，比如 ./support_md_full
    - output_path: 输出的 JSONL 文件路径，比如 ./qa_output/email_qa.jsonl
    - model: 使用的 OpenAI 模型名称
    - limit_files: 调试用，可限制最多处理多少个文件
    """
    client = get_client()

    input_dir = input_dir.expanduser().resolve()
    output_path = output_path.expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    md_files = sorted(input_dir.glob("*.md"))
    if limit_files is not None:
        md_files = md_files[:limit_files]

    print(f"[INFO] 将处理目录：{input_dir}")
    print(f"[INFO] 找到 {len(md_files)} 个 markdown 邮件文件")
    print(f"[INFO] 输出文件：{output_path}")
    print(f"[INFO] 模型：{model}\n")

    processed_files = 0
    total_records = 0
    with output_path.open("w", encoding="utf-8") as fout:
        for idx, path in enumerate(md_files, start=1):
            filename = path.name

            try:
                content = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                print(f"[WARN] 读取文件失败（编码问题），已跳过：{filename}")
                processed_files += 1
                # 每处理 10 个文件输出一次进度
                if processed_files % 10 == 0:
                    progress_pct = (processed_files / len(md_files)) * 100
                    print(f"[进度] 已处理文件：{processed_files}/{len(md_files)} ({progress_pct:.1f}%) | 已生成记录：{total_records} | 完成度：{(total_records/len(md_files)*100):.2f}%")
                continue

            # 可以根据需要做截断，这里先直接全量丢给模型
            qa_items = extract_qa_from_email(
                client=client, email_text=content, filename=filename, model=model
            )

            processed_files += 1

            if not qa_items:
                # 每处理 10 个文件输出一次进度
                if processed_files % 10 == 0:
                    progress_pct = (processed_files / len(md_files)) * 100
                    print(f"[进度] 已处理文件：{processed_files}/{len(md_files)} ({progress_pct:.1f}%) | 已生成记录：{total_records} | 完成度：{(total_records/len(md_files)*100):.2f}%")
                continue

            for qa in qa_items:
                # 统一为与 distill_unitree_emails.py 相同的字段结构，便于后续合并使用
                record = {
                    "file": filename,
                    "category": qa.get("category"),
                    "model": qa.get("model"),
                    "issue": qa.get("issue"),
                    "resolution": qa.get("resolution"),
                    "code_snippet": qa.get("code_snippet", "") or "",
                }
                fout.write(json.dumps(record, ensure_ascii=False) + "\n")
                total_records += 1

            # 每处理 10 个文件输出一次进度
            if processed_files % 10 == 0:
                progress_pct = (processed_files / len(md_files)) * 100
                print(f"[进度] 已处理文件：{processed_files}/{len(md_files)} ({progress_pct:.1f}%) | 已生成记录：{total_records} | 完成度：{(total_records/len(md_files)*100):.2f}%")

    print(f"\n[DONE] 处理完成！")
    print(f"[DONE] 共处理文件：{processed_files}/{len(md_files)}")
    print(f"[DONE] 共写出 {total_records} 条 QA 记录到 {output_path}")


def main():
    # 默认输入目录和输出路径，你也可以根据需要改成 argparse 接收命令行参数
    project_root = PROJECT_ROOT
    data_dir = project_root / "data"
    input_dir = data_dir / "md_full"
    output_path = data_dir / "qa_output" / "email_qa.jsonl"

    # 如需测试先只跑前 N 个文件，可以把 limit_files 改成一个整数，比如 20
    process_directory(
        input_dir=input_dir,
        output_path=output_path,
        model=DEFAULT_MODEL,
        limit_files=None,
    )


if __name__ == "__main__":
    main()
