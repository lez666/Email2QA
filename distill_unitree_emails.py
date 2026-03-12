import asyncio
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Set

from bs4 import BeautifulSoup
from openai import AsyncOpenAI, RateLimitError, APIError
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)
from tqdm import tqdm

"""
Unitree 技术支持邮件 → 结构化知识 JSONL 蒸馏脚本

依赖：
    pip install "openai>=1.0.0" beautifulsoup4 tenacity tqdm

运行方式（在项目根目录 /home/wasabi/email-to-QA）：
    export OPENAI_API_KEY="你的key"        # 或直接在下面修改 OPENAI_API_KEY 变量
    export OPENAI_BASE_URL="https://api.openai.com/v1"  # 如使用官方云可省略
    python distill_unitree_emails.py

数据目录约定（所有输入/输出都在 data/ 下，不放在项目根目录）：
    输入目录：
        ./data/emails/                 （请将 1500 封邮件放在此目录下，支持 .eml/.html/.txt/.md 等）
    输出文件：
        ./data/unitree_knowledge_distilled.jsonl   （每行一条结构化知识）
        ./data/processed_files.log                 （已成功处理的文件列表，用于断点续传）
"""


# ===== 基础配置 =====

# 如需写死在代码中，可直接填入字符串；优先使用环境变量
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "").strip()

# 模型名称优先从环境变量 OPENAI_MODEL 读取，便于在不同环境下灵活切换；
# 未设置时默认使用最新的 GPT-5.4 模型。
DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.4").strip() or "gpt-5.4"

CONCURRENCY = 8  # 并发数量，建议 5~10

PROJECT_ROOT = Path(__file__).parent
DATA_DIR = PROJECT_ROOT / "data"
PROMPT_DIR = PROJECT_ROOT / "prompts"
EMAIL_DIR = DATA_DIR / "emails"
OUTPUT_JSONL = DATA_DIR / "unitree_knowledge_distilled.jsonl"
PROCESSED_LOG = DATA_DIR / "processed_files.log"


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
    key = (OPENAI_API_KEY or os.getenv("OPENAI_API_KEY", "")).strip()
    if key:
        return key

    key_path = PROJECT_ROOT / "secrets" / "openai_key.txt"
    if key_path.exists():
        return key_path.read_text(encoding="utf-8").strip()

    raise RuntimeError("未找到 OPENAI_API_KEY，请正确配置。")


def get_client() -> AsyncOpenAI:
    api_key = load_api_key()
    if OPENAI_BASE_URL:
        return AsyncOpenAI(api_key=api_key, base_url=OPENAI_BASE_URL)
    return AsyncOpenAI(api_key=api_key)


# ===== 文本清洗相关 =====

SIGNATURE_PATTERNS = [
    r"^Kind Regards.*",
    r"^Best Regards.*",
    r"^Regards.*",
    r"^Sincerely.*",
    r"^此致.*",
    r"^敬礼.*",
    r"^谢谢.*",
    r"^Thanks[,]?.*",
]

HISTORY_START_PATTERNS = [
    r"^From: .+",
    r"^On .+ wrote:$",
    r"^发件人[:：].+",
    r"^-----Original Message-----",
]

PII_PATTERNS = [
    # 邮箱
    (re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"), "<EMAIL>"),
    # IPv4
    (re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b"), "<IP>"),
    # 简单订单号样式：包含 'Order', '订单', 'PO' 等跟随一串字母数字
    (re.compile(r"\b(?:Order|ORDER|order|订单|PO|Po|po)[\s#:]*[A-Za-z0-9_-]{4,}\b"), "<ORDER_ID>"),
    # 人名（非常粗略，仅作基础脱敏，中文两到三字）
    (re.compile(r"[^\x00-\x7F]{2,3}"), "<NAME>"),
]


def strip_html(raw: str) -> str:
    """使用 BeautifulSoup 去除 HTML 标签。"""
    # 如果本身是纯文本也没关系，bs4 也能处理
    soup = BeautifulSoup(raw, "html.parser")
    text = soup.get_text("\n")
    return text


def remove_signatures_and_history(text: str) -> str:
    """粗略去掉签名和历史邮件回复链，只保留最新一轮对话的主体内容。"""
    lines = text.splitlines()
    cleaned: List[str] = []
    signature_regexes = [re.compile(pat, re.IGNORECASE) for pat in SIGNATURE_PATTERNS]
    history_regexes = [re.compile(pat, re.IGNORECASE) for pat in HISTORY_START_PATTERNS]

    for line in lines:
        stripped = line.strip()

        # 跳过明显的历史引用（> 开头）
        if stripped.startswith(">"):
            continue

        # 如果检测到历史邮件起始标记，直接停止（只保留最上面的最新一段）
        if any(rgx.match(stripped) for rgx in history_regexes):
            break

        # 碰到签名开头，认为后面都是签名，停止
        if any(rgx.match(stripped) for rgx in signature_regexes):
            break

        cleaned.append(line)

    return "\n".join(cleaned).strip()


def redact_pii(text: str) -> str:
    """使用正则简单脱敏（邮箱、IP、订单号、人名等）。"""
    redacted = text
    for pattern, repl in PII_PATTERNS:
        redacted = pattern.sub(repl, redacted)
    return redacted


def preprocess_email_content(raw: str) -> str:
    """完整预处理：HTML → 文本 → 去签名/历史 → 脱敏。"""
    text = strip_html(raw)
    text = remove_signatures_and_history(text)
    text = redact_pii(text)
    return text


# ===== OpenAI 调用与重试 =====

def build_messages(clean_text: str, filename: str) -> List[Dict[str, Any]]:
    system_content = load_prompt("distill_unitree_emails_system.txt")

    user_content = (
        f"下面是已经清洗和脱敏后的邮件内容文本（文件名：{filename}）：\n\n"
        "---------------- 邮件开始 ----------------\n"
        f"{clean_text}\n"
        "---------------- 邮件结束 ----------------\n\n"
        "请按照系统指令，返回一个 JSON 对象 {\"items\": [...]}。"
    )

    return [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_content},
    ]


async def call_openai_with_retry(
    client: AsyncOpenAI,
    messages: List[Dict[str, Any]],
    model: str = DEFAULT_MODEL,
) -> Dict[str, Any]:
    """带 tenacity 重试的 OpenAI 调用（适配速率限制等）。"""

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
            content = resp.choices[0].message.content or "{}"
            return json.loads(content)

    # 理论上不会走到这里
    return {"items": []}


# ===== 文件处理与并发调度 =====

def load_processed_files() -> Set[str]:
    if not PROCESSED_LOG.exists():
        return set()
    with PROCESSED_LOG.open("r", encoding="utf-8") as f:
        return {line.strip() for line in f if line.strip()}


def list_email_files() -> List[Path]:
    if not EMAIL_DIR.exists():
        raise FileNotFoundError(f"邮件目录不存在：{EMAIL_DIR}")
    # 支持常见扩展名
    exts = {".eml", ".txt", ".md", ".html", ".htm"}
    files: List[Path] = []
    for path in sorted(EMAIL_DIR.iterdir()):
        if path.is_file() and path.suffix.lower() in exts:
            files.append(path)
    return files


async def process_one_file(
    client: AsyncOpenAI,
    path: Path,
    jsonl_lock: asyncio.Lock,
    log_lock: asyncio.Lock,
    pbar: tqdm,
):
    filename = path.name

    try:
        raw = path.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        pbar.write(f"[ERROR] 读取失败 {filename}: {e}")
        pbar.update(1)
        return

    clean_text = preprocess_email_content(raw)
    if not clean_text.strip():
        # 空内容也标记为已处理，避免下次重复
        async with log_lock:
            with PROCESSED_LOG.open("a", encoding="utf-8") as flog:
                flog.write(f"{filename}\n")
        pbar.update(1)
        return

    messages = build_messages(clean_text, filename)

    try:
        result = await call_openai_with_retry(client, messages)
    except Exception as e:
        pbar.write(f"[ERROR] OpenAI 调用失败 {filename}: {e}")
        pbar.update(1)
        return

    items = result.get("items") or []
    if not isinstance(items, list):
        items = []

    # 将每个 item 作为一条 JSONL 写入
    if items:
        async with jsonl_lock:
            with OUTPUT_JSONL.open("a", encoding="utf-8") as fout:
                for item in items:
                    record = {
                        "file": filename,
                        "category": item.get("category"),
                        "model": item.get("model"),
                        "issue": item.get("issue"),
                        "resolution": item.get("resolution"),
                        "code_snippet": item.get("code_snippet", "") or "",
                    }
                    fout.write(json.dumps(record, ensure_ascii=False) + "\n")

    # 成功或无内容，都记为已处理
    async with log_lock:
        with PROCESSED_LOG.open("a", encoding="utf-8") as flog:
            flog.write(f"{filename}\n")

    pbar.update(1)


async def main_async():
    client = get_client()

    OUTPUT_JSONL.parent.mkdir(parents=True, exist_ok=True)

    processed = load_processed_files()
    all_files = list_email_files()

    # 过滤掉已处理文件
    pending_files = [f for f in all_files if f.name not in processed]

    if not pending_files:
        print("没有待处理的邮件文件（全部已在 processed_files.log 中）。")
        return

    print(f"总邮件文件数：{len(all_files)}，其中待处理：{len(pending_files)}")
    print(f"输出 JSONL：{OUTPUT_JSONL}")
    print(f"断点续传日志：{PROCESSED_LOG}")

    jsonl_lock = asyncio.Lock()
    log_lock = asyncio.Lock()
    sem = asyncio.Semaphore(CONCURRENCY)

    async def worker(path: Path):
        async with sem:
            await process_one_file(client, path, jsonl_lock, log_lock, pbar)

    with tqdm(total=len(pending_files), desc="Distilling emails") as pbar:
        tasks = [asyncio.create_task(worker(p)) for p in pending_files]
        await asyncio.gather(*tasks)

    print("蒸馏完成。")


def main():
    asyncio.run(main_async())


if __name__ == "__main__":
    main()

