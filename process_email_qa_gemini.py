import os
import json
from pathlib import Path

from google import genai

"""
使用 Gemini（例如 gmini3 / gemini-1.5-flash）从邮件 markdown 中抽取 QA。

用法（在项目根目录 /home/wasabi/email-to-QA）：
    # 推荐：把 key 放到 secrets/google_api_key.txt（见 secrets/README.md）
    # 或者：
    export GOOGLE_API_KEY="你的_gemini_api_key"

    python process_email_qa_gemini.py

默认：
    输入：./data/msy_email_md_full_demo 下所有 .md
    输出：./data/qa_output/temp/msy_email_md_full_demo_qa_v1.jsonl
    （会复用原来 OpenAI 版本的输出文件，并根据其中的 file 做断点续传，只处理剩下没跑完的 .md）
"""


PROJECT_ROOT = Path(__file__).parent
PROMPT_DIR = PROJECT_ROOT / "prompts"

DATA_DIR = PROJECT_ROOT / "data"
DEFAULT_INPUT_DIR = DATA_DIR / "msy_email_md_full_demo"
DEFAULT_OUTPUT = DATA_DIR / "qa_output" / "temp" / "msy_email_md_full_demo_qa_v1.jsonl"


def load_prompt(filename: str) -> str:
    path = PROMPT_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"找不到提示词文件：{path}")
    return path.read_text(encoding="utf-8")


def load_gemini_key() -> str:
    key = os.getenv("GOOGLE_API_KEY", "").strip()
    if key:
        return key
    key_path = PROJECT_ROOT / "secrets" / "google_api_key.txt"
    if key_path.exists():
        return key_path.read_text(encoding="utf-8").strip()
    raise RuntimeError("未找到 GOOGLE_API_KEY，请在环境变量或 secrets/google_api_key.txt 中配置。")


def build_prompt(email_markdown: str, filename: str) -> str:
    """
    对 Gemini，我们直接拼成一个长文本 prompt：
    - 先是系统指令（distill_emails_system.txt）
    - 再附上当前这封邮件的 markdown 内容
    """
    system_text = load_prompt("distill_emails_system.txt")
    user_part = (
        f"下面是一个 Markdown 格式的技术支持邮件线程内容（文件名：{filename}）。"
        "这些数据应已在离线环境完成格式转换与隐私脱敏，可发往模型做结构化抽取。\n\n"
        "---------------- 原始邮件开始 ----------------\n"
        f"{email_markdown}\n"
        "---------------- 原始邮件结束 ----------------\n\n"
        "请严格按照前面的系统指令，返回一个 JSON 对象，形如："
        '{ \"items\": [ { \"category\": \"...\",\"model\": \"...\",\"issue\": \"...\",\"resolution\": \"...\",\"code_snippet\": \"...\" }, ... ] }。'
    )
    return system_text + "\n\n" + user_part


def get_gemini_model():
    api_key = load_gemini_key()
    client = genai.Client(api_key=api_key)
    # 你的 key 来自 gmini3，这里默认用 gmini 系列的 flash 模型；
    # 如需切换，可以通过环境变量 GEMINI_MODEL 覆盖。
    model_name = os.getenv("GEMINI_MODEL", "gmini-1.5-flash").strip() or "gmini-1.5-flash"
    return client, model_name


def extract_qa_with_gemini(client, model_name: str, email_text: str, filename: str):
    prompt = build_prompt(email_text, filename)

    # 简单重试 3 次
    last_err: Exception | None = None
    for attempt in range(3):
        try:
            resp = client.models.generate_content(
                model=model_name,
                contents=prompt,
            )
            # 新版 google.genai 返回结构中，主要内容在 candidates[0].content.parts[0].text
            content = ""
            try:
                if resp.candidates:
                    parts = resp.candidates[0].content.parts
                    if parts and hasattr(parts[0], "text"):
                        content = parts[0].text or ""
            except Exception:
                # 保底：尝试直接用 str
                content = str(resp)
            if not content:
                return []
            try:
                data = json.loads(content)
            except json.JSONDecodeError:
                # Gemini 可能输出前后有解释文字，这里简单做一次截断尝试
                # 找到第一个 '{' 和最后一个 '}' 之间的内容再尝试一次
                start = content.find("{")
                end = content.rfind("}")
                if start != -1 and end != -1 and end > start:
                    try:
                        data = json.loads(content[start : end + 1])
                    except json.JSONDecodeError:
                        print(f"[WARN] Gemini 返回 JSON 解析失败，文件：{filename}")
                        return []
                else:
                    print(f"[WARN] Gemini 返回中未找到 JSON，文件：{filename}")
                    return []

            # 与 OpenAI 版本一样，兼容多种结构
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
                    preview = (content[:200] + "...") if len(content) > 200 else content
                    print(f"[WARN] Gemini 返回对象中未找到数组字段，文件：{filename}，content 预览：{preview}")
                    return []
            else:
                print(f"[WARN] Gemini 返回的顶层既不是数组也不是对象，文件：{filename}")
                return []

            return items
        except Exception as e:  # noqa: BLE001
            last_err = e
            print(f"[WARN] Gemini 调用错误，第 {attempt + 1} 次重试中，文件：{filename}，错误：{e}")

    print(f"[ERROR] Gemini 调用多次失败，跳过文件：{filename}，错误：{last_err}")
    return []


def process_directory_with_gemini(
    input_dir: Path,
    output_path: Path,
    limit_files: int | None = None,
) -> None:
    """
    基本流程仿照 process_email_qa.process_directory：
    - 读 input_dir 下所有 .md
    - 读取已有 JSONL，提取已处理的 file 做断点续传
    - 对剩余文件依次调用 Gemini
    """
    client, model_name = get_gemini_model()

    input_dir = input_dir.expanduser().resolve()
    output_path = output_path.expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    md_files = sorted(input_dir.glob("*.md"))
    if limit_files is not None:
        md_files = md_files[:limit_files]

    # 断点续传：读取已处理的文件名
    processed_file_set: set[str] = set()
    existing_record_count = 0
    if output_path.exists():
        print(f"[INFO] 检测到已有输出文件：{output_path}")
        try:
            with output_path.open("r", encoding="utf-8") as fin:
                for line in fin:
                    if line.strip():
                        try:
                            record = json.loads(line)
                            if "file" in record:
                                processed_file_set.add(record["file"])
                            existing_record_count += 1
                        except json.JSONDecodeError:
                            pass
            print(f"[INFO] 已找到 {len(processed_file_set)} 个已处理的文件，{existing_record_count} 条已有记录")
        except Exception as e:  # noqa: BLE001
            print(f"[WARN] 读取已有文件失败：{e}，将从头开始处理")

    remaining_files = [f for f in md_files if f.name not in processed_file_set]
    print(f"[INFO] 将处理目录：{input_dir}")
    print(f"[INFO] 找到 {len(md_files)} 个 markdown 邮件文件")
    print(f"[INFO] 已处理 {len(processed_file_set)} 个文件，剩余 {len(remaining_files)} 个文件待处理")
    print(f"[INFO] 输出文件：{output_path}")
    print(f"[INFO] 使用模型：Gemini（通过 google-generativeai）\n")

    processed_files = len(processed_file_set)
    total_records = existing_record_count

    with output_path.open("a", encoding="utf-8") as fout:
        for idx, path in enumerate(remaining_files, start=1):
            filename = path.name

            try:
                content = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                print(f"[WARN] 读取文件失败（编码问题），已跳过：{filename}")
                processed_files += 1
                if processed_files % 10 == 0:
                    progress_pct = (processed_files / len(md_files)) * 100
                    print(
                        f"[进度] 已处理文件：{processed_files}/{len(md_files)} "
                        f"({progress_pct:.1f}%) | 已生成记录：{total_records}",
                        flush=True,
                    )
                continue

            qa_items = extract_qa_with_gemini(client, model_name, content, filename)
            processed_files += 1

            if not qa_items:
                if processed_files % 10 == 0 or processed_files == len(md_files):
                    progress_pct = (processed_files / len(md_files)) * 100
                    print(
                        f"[进度] 已处理文件：{processed_files}/{len(md_files)} "
                        f"({progress_pct:.1f}%) | 已生成记录：{total_records}",
                        flush=True,
                    )
                continue

            for qa in qa_items:
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

            if processed_files % 10 == 0 or processed_files == len(md_files):
                progress_pct = (processed_files / len(md_files)) * 100
                print(
                    f"[进度] 已处理文件：{processed_files}/{len(md_files)} "
                    f"({progress_pct:.1f}%) | 已生成记录：{total_records}",
                    flush=True,
                )

    print(f"\n[DONE] 处理完成！")
    print(f"[DONE] 共处理文件：{processed_files}/{len(md_files)}")
    print(f"[DONE] 共写出 {total_records} 条 QA 记录到 {output_path}")


def main():
    input_dir = DEFAULT_INPUT_DIR
    output_path = DEFAULT_OUTPUT
    process_directory_with_gemini(
        input_dir=input_dir,
        output_path=output_path,
        limit_files=None,
    )


if __name__ == "__main__":
    main()

