import os
import json
from pathlib import Path
from typing import Any, Dict

from openai import OpenAI


"""
用途：对已生成的 QA JSONL 结果做二次清洗，统一人称、口吻和隐私处理，避免出现
“客户邮件中……”这类表述，并去掉私有网盘/视频链接。

特点：
- 只处理每条 QA 的结构化字段，比直接喂整封邮件给模型便宜很多（节约 token）。
- 保留原有字段结构（file/category/model/issue/resolution/code_snippet）。

用法示例（在项目根目录下）：

  export OPENAI_API_KEY="你的_openai_key"
  # 建议清洗脚本使用 GPT-4 族模型（更便宜），如 gpt-4.1-mini
  export OPENAI_MODEL="gpt-4.1-mini"
  python clean_qa_jsonl.py \\
      --src data/qa_output/email_qa.jsonl \\
      --dst data/qa_output/temp/Enzi'sknowledge.jsonl
"""


PROJECT_ROOT = Path(__file__).parent
PROMPT_DIR = PROJECT_ROOT / "prompts"

# 清洗脚本可以使用更便宜的 GPT-4 系模型：
# 优先级：命令行 --model > 环境变量 CLEAN_OPENAI_MODEL > 环境变量 OPENAI_MODEL > 默认 "gpt-4.1-mini"
DEFAULT_MODEL = (
    os.getenv("CLEAN_OPENAI_MODEL")
    or os.getenv("OPENAI_MODEL")
    or "gpt-4.1-mini"
)


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

    key_path = PROJECT_ROOT / "secrets" / "openai_key.txt"
    if key_path.exists():
        content = key_path.read_text(encoding="utf-8")
        for line in content.splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                return line

    raise RuntimeError(
        "未找到 OPENAI_API_KEY，请正确配置。"
        "请设置环境变量 OPENAI_API_KEY 或在 secrets/openai_key.txt 中填写一行 API key（可配合 # 注释）。"
    )


def load_base_url() -> str | None:
    url = os.getenv("OPENAI_BASE_URL", "").strip()
    if url:
        return url.rstrip("/")
    p = PROJECT_ROOT / "secrets" / "openai_base_url.txt"
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                return line.rstrip("/")
    return None


def get_client() -> OpenAI:
    api_key = load_api_key()
    base = load_base_url()
    if base:
        return OpenAI(api_key=api_key, base_url=base)
    return OpenAI(api_key=api_key)


def build_messages_for_item(item: Dict[str, Any]) -> list[Dict[str, str]]:
    """
    构造给 OpenAI 的对话消息，输入是单条 QA 记录，输出是清洗后的同结构对象。
    """
    system_msg = {
        "role": "system",
        "content": load_prompt("clean_qa_items_system.txt"),
    }

    # 只把关心的字段传给模型，避免无关噪音
    minimal_item = {
        "file": item.get("file", ""),
        "category": item.get("category"),
        "model": item.get("model"),
        "issue": item.get("issue", "") or "",
        "resolution": item.get("resolution", "") or "",
        "code_snippet": item.get("code_snippet", "") or "",
    }

    user_msg = {
        "role": "user",
        "content": (
            "下面是一条已经从技术支持邮件中抽取好的 QA 记录，请根据系统提示词的要求，"
            "对其中的 issue / resolution / code_snippet 进行二次清洗和重写，"
            "统一人称和口吻，并去掉私有网盘/现场视频等敏感链接，保留公开技术文档链接。"
            "请输出清洗后的 JSON 对象，字段集合尽量与输入保持一致。\n\n"
            "原始记录 JSON：\n"
            f"{json.dumps(minimal_item, ensure_ascii=False)}"
        ),
    }

    return [system_msg, user_msg]


def clean_one_item(client: OpenAI, item: Dict[str, Any], model: str = DEFAULT_MODEL) -> Dict[str, Any]:
    """调用 OpenAI 对单条 QA 记录进行二次清洗，失败时尽量回退到原始内容。"""
    messages = build_messages_for_item(item)
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.1,
            response_format={"type": "json_object"},
        )
    except Exception as e:
        print(f"[WARN] 清洗失败，直接保留原始记录。原因：{e}")
        return item

    content = resp.choices[0].message.content or ""
    if not content.strip():
        print("[WARN] 清洗结果为空，保留原始记录。")
        return item

    try:
        cleaned = json.loads(content)
    except json.JSONDecodeError:
        print("[WARN] 清洗结果 JSON 解析失败，保留原始记录。")
        return item

    # 确保至少保留原始字段，避免模型删掉关键信息
    result: Dict[str, Any] = dict(item)
    for k, v in cleaned.items():
        result[k] = v
    return result


def process_jsonl(
    src: Path,
    dst: Path,
    model: str = DEFAULT_MODEL,
    limit: int | None = None,
    resume: bool = True,
) -> None:
    """逐行读取 src JSONL，清洗后写入 dst JSONL。

    - 默认开启简单断点续传：如果 dst 已存在且非空，将自动跳过 src 中前 N 条记录（按行计数），
      从第 N+1 条开始继续清洗并以 append 方式写入 dst。
    - 这样在中途报错或中断时，重新运行同一命令，可以从上次的位置继续往后清洗，避免重复花费 token。
    """
    src = src.expanduser().resolve()
    dst = dst.expanduser().resolve()
    dst.parent.mkdir(parents=True, exist_ok=True)

    if not src.exists():
        raise FileNotFoundError(f"找不到源文件：{src}")

    client = get_client()

    # 简单断点续传：如果 dst 已存在且非空，统计已写出的行数，后续跳过 src 中前 N 条
    existing_cleaned = 0
    write_mode = "w"
    if resume and dst.exists():
        with dst.open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    existing_cleaned += 1
        if existing_cleaned > 0:
            write_mode = "a"
            print(
                f"[INFO] 检测到已有清洗结果文件：{dst}，已写出 {existing_cleaned} 条记录，将从第 {existing_cleaned + 1} 条继续。",
            )

    total = 0
    cleaned = existing_cleaned

    print(f"[INFO] 源文件：{src}")
    print(f"[INFO] 目标文件：{dst}")
    print(f"[INFO] 使用模型：{model}")
    print(f"[INFO] 已有清洗记录数：{existing_cleaned}\n")

    with src.open("r", encoding="utf-8") as fin, dst.open(
        write_mode, encoding="utf-8"
    ) as fout:
        for line in fin:
            if not line.strip():
                continue

            total += 1

            # 断点续传：跳过 src 中前 existing_cleaned 条有效行
            if resume and total <= existing_cleaned:
                continue

            if limit is not None and (total - existing_cleaned) > limit:
                break

            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                print(f"[WARN] 第 {total} 行 JSON 解析失败，已跳过。")
                continue

            cleaned_item = clean_one_item(client, item, model=model)
            fout.write(json.dumps(cleaned_item, ensure_ascii=False) + "\n")
            cleaned += 1

            if (cleaned - existing_cleaned) % 50 == 0:
                print(f"[进度] 本次新增已清洗 {cleaned - existing_cleaned} 条，总计 {cleaned} 条。")

    print(
        f"\n[DONE] 清洗完成！源文件有效行数约 {total} 条，本次新增写出 {cleaned - existing_cleaned} 条，总计 {cleaned} 条。"
    )


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="对 QA JSONL 结果做二次清洗，统一口吻并去除私有链接。"
    )
    parser.add_argument(
        "--src",
        type=str,
        default=str(
            PROJECT_ROOT
            / "data"
            / "qa_output"
            / "temp"
            / "email_qasingle thread.jsonl"
        ),
        help="源 JSONL 文件路径（默认：data/qa_output/temp/email_qasingle thread.jsonl）",
    )
    parser.add_argument(
        "--dst",
        type=str,
        default=str(
            PROJECT_ROOT
            / "data"
            / "qa_output"
            / "temp"
            / "Enzi'sknowledge.jsonl"
        ),
        help="清洗后的 JSONL 输出路径（默认：data/qa_output/temp/Enzi'sknowledge.jsonl）",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=DEFAULT_MODEL,
        help=f"使用的 OpenAI 模型名称（默认从 OPENAI_MODEL 或 '{DEFAULT_MODEL}' 读取）",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="调试用，最多只处理前 N 条记录（默认：不限制）。",
    )

    args = parser.parse_args()

    process_jsonl(
        src=Path(args.src),
        dst=Path(args.dst),
        model=args.model,
        limit=args.limit,
        resume=True,
    )


if __name__ == "__main__":
    main()

