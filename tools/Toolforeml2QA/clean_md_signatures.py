#!/usr/bin/env python3
"""
Post-process .md files to strip signatures and forwarded/quoted headers.

This is designed for cleaning technical support mail exports:
- Remove company signature blocks (name + title + contact info).
- Remove forwarded headers like "----------转发的邮件信息----------", "发件人：", etc.

Usage:
  ./clean_md_signatures.py /path/to/md_dir
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path


FORWARD_MARKERS = [
    r"^[-]{5,}\s*转发的邮件信息[-\s]*$",
    r"^[-]{5,}\s*Forwarded message[-\s]*$",
    r"^发件人[:：]",
    r"^收件人[:：]",
    r"^抄送人[:：]",
    r"^主题[:：]",
    r"^日期[:：]",
]

SIGNATURE_MARKERS = [
    r"^JIM MA\s*$",
    r"^Unitree Robotics \|\s*Robot Engineer\s*$",
    r"^Unitree Robotics \|\s*Technical Support\s*$",
    r"^This is the Unitree Technical Support team",
    r"^Kind Regards\s*$",
    r"^Best Regards\s*$",
    r"^Regards\s*$",
    r"^谢谢[!！]?\s*$",
    r"^此致[，,]?\s*敬礼\s*$",
    r"^Office:\s*\+?\d",
    r"^Mobile:\s*\+?\d",
    r"^WhatsApp:\s*\+?\d",
    r"^WeChat:\s*",
    r"^Email:\s*support_",
    r"^3rd floor, Block 1, 88 Dongliu Rd\.",
    r"^Unitree Robotics \|",
]

FORWARD_RE = re.compile("|".join(f"(?:{p})" for p in FORWARD_MARKERS))
SIGNATURE_RE = re.compile("|".join(f"(?:{p})" for p in SIGNATURE_MARKERS), re.IGNORECASE)


def clean_one(path: Path) -> bool:
    """Clean a single markdown file in-place. Returns True if modified."""
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.split("\n")

    cutoff = None
    for i, line in enumerate(lines):
        if FORWARD_RE.search(line):
            cutoff = i
            break
        if SIGNATURE_RE.search(line):
            cutoff = i
            break

    if cutoff is None:
        return False

    new_lines = lines[:cutoff]
    # Strip trailing blank lines
    while new_lines and not new_lines[-1].strip():
        new_lines.pop()

    new_text = "\n".join(new_lines) + "\n"
    if new_text == text:
        return False

    path.write_text(new_text, encoding="utf-8")
    return True


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Clean signatures/forwarded headers from markdown files.")
    ap.add_argument("root", help="Root directory containing .md files")
    args = ap.parse_args(argv)

    root = Path(args.root).expanduser().resolve()
    if not root.is_dir():
        print(f"目录不存在: {root}")
        return 2

    changed = 0
    total = 0
    for p in root.rglob("*.md"):
        total += 1
        if clean_one(p):
            changed += 1
            print(f"CLEANED: {p}")
    print(f"Done. scanned={total} cleaned={changed}")
    return 0


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv[1:]))
