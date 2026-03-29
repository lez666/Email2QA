"""
对 Markdown 邮件正文做 MD→MD 深度脱敏（OpenAI 兼容 Chat Completions）。

默认与 `process_email_qa.py` 相同：使用**线上 OpenAI 官方 API**（或你在环境变量里指定的兼容端点）。

认证与地址（优先级从高到低）：
  - `OPENAI_API_KEY`；若未设置则读取 `secrets/openai_key.txt`（第一行非 `#` 的非空行）
  - `OPENAI_BASE_URL`；可选 `secrets/openai_base_url.txt`（一行）；
    若仍无则走官方端点
  - `OPENAI_MODEL`：默认与 `process_email_qa.py` 一致（见下方 DEFAULT_MODEL）

改用**本机 vLLM / Ollama 等**时，只需设置 Base URL 与本地模型名，Key 仍可用同一文件或环境变量，例如：

  export OPENAI_BASE_URL="http://127.0.0.1:8000/v1"
  export OPENAI_API_KEY="local"
  # 或写入 secrets/openai_key.txt
  export OPENAI_MODEL="你的本地模型 ID"
  python scripts/scrub_markdown_pii.py --input-dir data/md_from_eml --output-dir data/md_full

并发数：`SCRUB_CONCURRENCY`（默认 4）；仍识别旧名 `OFFLINE_SCRUB_CONCURRENCY`。

默认目录：输入 `data/md_from_eml`，输出 `data/md_full`。
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

from openai import AsyncOpenAI, APIError, RateLimitError
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)
from tqdm import tqdm

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROMPT_DIR = PROJECT_ROOT / "prompts"
DATA_DIR = PROJECT_ROOT / "data"

DEFAULT_INPUT = DATA_DIR / "md_from_eml"
DEFAULT_OUTPUT = DATA_DIR / "md_full"
DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.4").strip() or "gpt-5.4"
_raw_conc = os.getenv("SCRUB_CONCURRENCY") or os.getenv(
    "OFFLINE_SCRUB_CONCURRENCY", "4"
)
CONCURRENCY = max(1, int(_raw_conc))


def load_prompt(filename: str) -> str:
    path = PROMPT_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"找不到提示词文件：{path}")
    return path.read_text(encoding="utf-8")


def _first_credential_line(path: Path) -> str | None:
    if not path.exists():
        return None
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            return line
    return None


def load_api_key() -> str:
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if key:
        return key
    p = PROJECT_ROOT / "secrets" / "openai_key.txt"
    v = _first_credential_line(p)
    if v:
        return v
    raise RuntimeError(
        "未配置 API 密钥：请设置环境变量 OPENAI_API_KEY，"
        "或在 secrets/openai_key.txt 写入一行 Key（可配合 # 注释）。"
    )


def load_base_url() -> str | None:
    """有值时使用自定义 Base URL；否则由 SDK 走官方 OpenAI。"""
    url = os.getenv("OPENAI_BASE_URL", "").strip()
    if url:
        return url.rstrip("/")
    p = PROJECT_ROOT / "secrets" / "openai_base_url.txt"
    v = _first_credential_line(p)
    if v:
        return v.rstrip("/")
    return None


def get_client() -> AsyncOpenAI:
    api_key = load_api_key()
    base_url = load_base_url()
    if base_url:
        return AsyncOpenAI(api_key=api_key, base_url=base_url)
    return AsyncOpenAI(api_key=api_key)


def build_messages(md_text: str, filename: str) -> list[dict[str, str]]:
    system = load_prompt("scrub_md_pii_system.txt")
    user = (
        f"文件名（仅供参考）：{filename}\n\n"
        "以下为待脱敏的 Markdown 全文：\n\n"
        "---------------- 原文开始 ----------------\n"
        f"{md_text}\n"
        "---------------- 原文结束 ----------------"
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


async def scrub_one(
    client: AsyncOpenAI,
    content: str,
    filename: str,
    model: str,
) -> str | None:
    messages = build_messages(content, filename)
    try:
        async for attempt in AsyncRetrying(
            retry=retry_if_exception_type((RateLimitError, APIError)),
            wait=wait_exponential(multiplier=1, min=1, max=60),
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
        tqdm.write(f"[ERROR] {filename}: {e}")
        return None

    raw = resp.choices[0].message.content
    if not raw:
        return None
    try:
        data: dict[str, Any] = json.loads(raw)
    except json.JSONDecodeError:
        tqdm.write(f"[WARN] JSON 解析失败：{filename}")
        return None
    md = data.get("markdown")
    if isinstance(md, str):
        return md
    tqdm.write(f"[WARN] 返回 JSON 缺少 markdown 字段：{filename}")
    return None


def _base_url_display() -> str:
    u = load_base_url()
    return u if u else "(OpenAI 官方默认端点)"


async def process_directory_async(
    input_dir: Path,
    output_dir: Path,
    model: str,
    overwrite: bool,
    limit: int | None,
) -> None:
    client = get_client()
    input_dir = input_dir.expanduser().resolve()
    output_dir = output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    md_files = sorted(input_dir.glob("*.md"))
    if limit is not None:
        md_files = md_files[:limit]

    if not md_files:
        print(f"[WARN] 目录下无 .md 文件：{input_dir}")
        return

    print(f"[INFO] 输入：{input_dir}")
    print(f"[INFO] 输出：{output_dir}")
    print(f"[INFO] Base URL：{_base_url_display()}")
    print(f"[INFO] 模型：{model}")
    print(f"[INFO] 并发：{CONCURRENCY}\n")

    sem = asyncio.Semaphore(CONCURRENCY)
    lock = asyncio.Lock()
    ok = 0
    skip = 0
    fail = 0

    async def worker(path: Path, pbar: tqdm) -> None:
        nonlocal ok, skip, fail
        out_path = output_dir / path.name
        if out_path.exists() and not overwrite:
            async with lock:
                skip += 1
            pbar.update(1)
            return

        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            tqdm.write(f"[WARN] 无法读取 {path.name}: {e}")
            async with lock:
                fail += 1
            pbar.update(1)
            return

        async with sem:
            result = await scrub_one(client, text, path.name, model)

        if result is None:
            async with lock:
                fail += 1
            pbar.update(1)
            return

        try:
            out_path.write_text(result, encoding="utf-8")
            async with lock:
                ok += 1
        except OSError as e:
            tqdm.write(f"[WARN] 无法写入 {out_path.name}: {e}")
            async with lock:
                fail += 1
        pbar.update(1)

    with tqdm(total=len(md_files), desc="Scrubbing MD (PII)") as pbar:
        await asyncio.gather(*[worker(p, pbar) for p in md_files])

    print(f"\n[DONE] 成功 {ok}，跳过 {skip}，失败 {fail}")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="MD→MD 隐私脱敏（默认使用线上 OpenAI API，与 process_email_qa 共用密钥配置）。"
    )
    p.add_argument(
        "--input-dir",
        type=str,
        default=str(DEFAULT_INPUT),
        help=f"输入目录（默认 {DEFAULT_INPUT}）",
    )
    p.add_argument(
        "--output-dir",
        type=str,
        default=str(DEFAULT_OUTPUT),
        help=f"输出目录（默认 {DEFAULT_OUTPUT}）",
    )
    p.add_argument(
        "--model",
        type=str,
        default=DEFAULT_MODEL,
        help="模型 ID（默认读环境变量 OPENAI_MODEL，与 process_email_qa 一致）",
    )
    p.add_argument(
        "--overwrite",
        action="store_true",
        help="若输出文件已存在则覆盖；默认跳过已存在文件",
    )
    p.add_argument("--limit", type=int, default=None, help="仅处理前 N 个文件（调试）")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    input_dir = (PROJECT_ROOT / args.input_dir).resolve()
    output_dir = (PROJECT_ROOT / args.output_dir).resolve()
    if not input_dir.is_dir():
        print(f"[ERROR] 输入目录不存在：{input_dir}", file=sys.stderr)
        sys.exit(1)
    asyncio.run(
        process_directory_async(
            input_dir=input_dir,
            output_dir=output_dir,
            model=args.model,
            overwrite=args.overwrite,
            limit=args.limit,
        )
    )


if __name__ == "__main__":
    main()
