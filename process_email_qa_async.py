import asyncio
import os
import json
import sys
from pathlib import Path
from typing import Any, Dict, List
from datetime import datetime

from openai import AsyncOpenAI, RateLimitError, APIError

# 设置无缓冲输出，确保进度实时显示
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(line_buffering=True)
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)
from tqdm import tqdm


"""
使用说明（异步并发版）：

1. 在终端设置环境变量（或在代码里直接写入 API Key）：
   export OPENAI_API_KEY="你的_openai_api_key"
   export OPENAI_MODEL="gpt-5.4"  # 可选，默认就是 gpt-5.4

2. 在项目根目录执行：
   python process_email_qa_async.py

3. 数据目录约定（所有输入/输出都在 data/ 下）：
   - 输入：遍历 ./data/md_full 下的所有 .md 邮件文件
   - 输出：./data/qa_output/email_qa.jsonl（每行一条 QA 记录，JSON 格式）

4. 并发控制：
   - 默认并发数：8（可通过 CONCURRENCY 变量调整，建议 5~10）
   - 使用 tenacity 自动重试，处理速率限制和网络错误

注意：这是 process_email_qa.py 的异步并发版本，功能完全相同，但速度更快。
处理的数据是未经过 LLM 处理的原始 Markdown 邮件线程。
"""


PROJECT_ROOT = Path(__file__).parent
PROMPT_DIR = PROJECT_ROOT / "prompts"
DATA_DIR = PROJECT_ROOT / "data"

# 模型名称优先从环境变量 OPENAI_MODEL 读取，便于在不同环境下灵活切换；
# 未设置时默认使用最新的 GPT-5.4 模型。
DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.4").strip() or "gpt-5.4"

# 并发数量，建议 5~10，可根据你的 API 限速和网络情况调整
CONCURRENCY = 8

# 日志文件路径
PROCESS_LOG = DATA_DIR / "qa_output" / "process_log.txt"


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
        content = key_path.read_text(encoding="utf-8")
        # 跳过注释行（以 # 开头的行），只读取实际的 key
        for line in content.splitlines():
            line = line.strip()
            if line and not line.startswith("#") and line.startswith("sk-"):
                return line

    raise RuntimeError("未找到 OPENAI_API_KEY，请正确配置。请设置环境变量 OPENAI_API_KEY 或在 secrets/openai_key.txt 中填写真实的 API key（跳过注释行）。")


def get_client() -> AsyncOpenAI:
    api_key = load_api_key()
    return AsyncOpenAI(api_key=api_key)


def build_prompt(email_markdown: str, filename: str) -> List[Dict[str, Any]]:
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


async def extract_qa_from_email_async(
    client: AsyncOpenAI, email_text: str, filename: str, model: str = DEFAULT_MODEL
) -> List[Dict[str, Any]]:
    """
    异步调用 OpenAI 模型，从单封（包含线程）的邮件文本中抽取 QA 列表。
    返回 Python 对象（list[dict]）。
    使用 tenacity 自动重试，处理速率限制和网络错误。
    """
    messages = build_prompt(email_text, filename)

    try:
        async for attempt in AsyncRetrying(
            retry=retry_if_exception_type((RateLimitError, APIError)),
            wait=wait_exponential(multiplier=1, min=1, max=30),
            stop=stop_after_attempt(5),
            reraise=True,
        ):
            with attempt:
                resp = await client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=0.1,
                    response_format={"type": "json_object"},
                )
                break
    except Exception as e:
        import traceback
        # 尝试获取完整的错误信息
        try:
            error_str = str(e)
            # 尝试打印，如果失败说明是编码问题
            try:
                print(f"[ERROR] OpenAI 调用失败 {filename}: {error_str}")
            except (UnicodeEncodeError, UnicodeDecodeError):
                # 如果打印失败，使用安全的编码方式
                safe_filename = filename.encode('ascii', errors='replace').decode('ascii')
                safe_error = error_str.encode('ascii', errors='replace').decode('ascii')
                print(f"[ERROR] OpenAI call failed {safe_filename}: {safe_error}")
        except Exception as print_err:
            # 如果连错误信息都无法获取，记录到日志文件
            try:
                with open("error_debug.log", "a", encoding="utf-8") as f:
                    f.write(f"Error processing {filename}: {repr(e)}\n")
                    f.write(f"Print error: {repr(print_err)}\n")
                    traceback.print_exc(file=f)
            except:
                pass
        return []

    content = resp.choices[0].message.content
    if not content:
        return []

    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        print(f"[WARN] 解析 JSON 失败，文件：{filename}")
        return []

    # 兼容多种返回结构，优先取 items 字段
    if isinstance(data, dict) and "items" in data and isinstance(data["items"], list):
        return data["items"]
    elif isinstance(data, list):
        return data
    else:
        preview = (content[:200] + "...") if len(content) > 200 else content
        print(f"[WARN] 模型返回结构异常，文件：{filename}，content 预览：{preview}")
        return []


async def process_one_file(
    client: AsyncOpenAI,
    path: Path,
    output_path: Path,
    jsonl_lock: asyncio.Lock,
    pbar: tqdm,
    model: str,
) -> None:
    """处理单个 Markdown 文件，抽取 QA 并写入 JSONL。"""
    filename = path.name

    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        pbar.write(f"[WARN] 读取文件失败，已跳过：{filename}，错误：{e}")
        pbar.update(1)
        return

    qa_items = await extract_qa_from_email_async(
        client=client, email_text=content, filename=filename, model=model
    )

    if qa_items:
        async with jsonl_lock:
            with output_path.open("a", encoding="utf-8") as fout:
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

    pbar.update(1)


async def process_directory_async(
    input_dir: Path,
    output_path: Path,
    model: str = DEFAULT_MODEL,
    limit_files: int | None = None,
) -> None:
    """
    异步并发处理目录下的所有 .md 文件，抽取 QA 并写入 JSONL。

    - input_dir: 存放邮件 markdown 的目录，比如 ./md_full
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

    start_time = datetime.now()
    print(f"[INFO] 将处理目录：{input_dir}", flush=True)
    print(f"[INFO] 找到 {len(md_files)} 个 markdown 邮件文件", flush=True)
    print(f"[INFO] 输出文件：{output_path}", flush=True)
    print(f"[INFO] 模型：{model}", flush=True)
    print(f"[INFO] 并发数：{CONCURRENCY}", flush=True)
    print(f"[INFO] 开始时间：{start_time.strftime('%Y-%m-%d %H:%M:%S')}\n", flush=True)

    # 清空输出文件（从头开始）
    output_path.write_text("", encoding="utf-8")

    jsonl_lock = asyncio.Lock()
    sem = asyncio.Semaphore(CONCURRENCY)
    processed_count = asyncio.Lock()
    processed_counter = 0
    progress_lock = asyncio.Lock()

    async def worker(path: Path, pbar: tqdm):
        nonlocal processed_counter
        async with sem:
            await process_one_file(client, path, output_path, jsonl_lock, pbar, model)
            
            # 更新处理计数并输出进度
            async with processed_count:
                processed_counter += 1
                current_processed = processed_counter
                
                # 每处理 10 个文件输出一次进度
                if current_processed % 10 == 0 or current_processed == len(md_files):
                    # 统计当前记录数（需要加锁避免并发读取文件）
                    async with jsonl_lock:
                        current_record_count = sum(1 for _ in output_path.open("r", encoding="utf-8") if _.strip())
                    
                    progress_pct = (current_processed / len(md_files)) * 100
                    completion_pct = (current_record_count / len(md_files)) * 100 if len(md_files) > 0 else 0
                    async with progress_lock:
                        print(f"[进度] 已处理文件：{current_processed}/{len(md_files)} ({progress_pct:.1f}%) | 已生成记录：{current_record_count} | 完成度：{completion_pct:.2f}%", flush=True)

    with tqdm(total=len(md_files), desc="Distilling markdown emails") as pbar:
        tasks = [asyncio.create_task(worker(p, pbar)) for p in md_files]
        await asyncio.gather(*tasks)

    # 统计最终记录数
    final_record_count = sum(1 for _ in output_path.open("r", encoding="utf-8") if _.strip())
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    print(f"\n[DONE] 处理完成！", flush=True)
    print(f"[DONE] 共处理文件：{processed_counter}/{len(md_files)}", flush=True)
    print(f"[DONE] 共写出 {final_record_count} 条 QA 记录到 {output_path}", flush=True)
    print(f"[DONE] 总耗时：{duration:.1f} 秒 ({duration/60:.1f} 分钟)", flush=True)
    
    # 写入日志文件
    log_entry = {
        "start_time": start_time.strftime("%Y-%m-%d %H:%M:%S"),
        "end_time": end_time.strftime("%Y-%m-%d %H:%M:%S"),
        "duration_seconds": round(duration, 2),
        "model": model,
        "concurrency": CONCURRENCY,
        "total_files": len(md_files),
        "processed_files": processed_counter,
        "generated_records": final_record_count,
        "input_dir": str(input_dir),
        "output_file": str(output_path),
    }
    
    PROCESS_LOG.parent.mkdir(parents=True, exist_ok=True)
    with PROCESS_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
    
    print(f"[LOG] 处理日志已保存到：{PROCESS_LOG}", flush=True)


def main():
    # 默认输入目录和输出路径
    project_root = PROJECT_ROOT
    data_dir = project_root / "data"
    input_dir = data_dir / "md_full"
    output_path = data_dir / "qa_output" / "email_qa.jsonl"

    # 如需测试先只跑前 N 个文件，可以把 limit_files 改成一个整数，比如 20
    asyncio.run(
        process_directory_async(
            input_dir=input_dir,
            output_path=output_path,
            model=DEFAULT_MODEL,
            limit_files=None,
        )
    )


if __name__ == "__main__":
    main()
