#!/usr/bin/env python3
"""
Convert .eml (RFC 822 email) files to Markdown.

Strategy:
1) Parse the email with Python stdlib `email`.
2) Prefer text/plain; fallback to text/html.
3) If HTML is used, convert to GitHub-flavored Markdown via pandoc.

Usage:
  ./eml2md.py input.eml -o output.md
  ./eml2md.py input.eml --stdout
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from email import policy
from email.parser import BytesParser
from email.utils import parsedate_to_datetime


def _decode_part(part) -> str:
    payload = part.get_payload(decode=True)
    if payload is None:
        return ""
    charset = part.get_content_charset() or "utf-8"
    try:
        return payload.decode(charset, errors="replace")
    except LookupError:
        return payload.decode("utf-8", errors="replace")


def _extract_best_body(msg) -> tuple[str, str]:
    """
    Returns (kind, text) where kind is "plain" or "html".
    """
    if msg.is_multipart():
        plain = None
        html = None
        for part in msg.walk():
            if part.get_content_maintype() == "multipart":
                continue
            ctype = (part.get_content_type() or "").lower()
            disp = (part.get("Content-Disposition") or "").lower()
            if "attachment" in disp:
                continue
            if ctype == "text/plain" and plain is None:
                plain = _decode_part(part)
            elif ctype == "text/html" and html is None:
                html = _decode_part(part)
        if plain and plain.strip():
            return "plain", plain
        if html and html.strip():
            return "html", html
        return "plain", ""
    else:
        ctype = (msg.get_content_type() or "").lower()
        if ctype == "text/html":
            return "html", _decode_part(msg)
        return "plain", _decode_part(msg)


def _format_headers(msg) -> str:
    subject = (msg.get("Subject") or "").strip()
    from_ = (msg.get("From") or "").strip()
    to_ = (msg.get("To") or "").strip()
    cc_ = (msg.get("Cc") or "").strip()
    date_raw = (msg.get("Date") or "").strip()
    date_iso = ""
    if date_raw:
        try:
            date_iso = parsedate_to_datetime(date_raw).isoformat()
        except Exception:
            date_iso = ""

    lines = []
    if subject:
        lines.append(f"# {subject}")
        lines.append("")
    meta = []
    if from_:
        meta.append(f"- From: {from_}")
    if to_:
        meta.append(f"- To: {to_}")
    if cc_:
        meta.append(f"- Cc: {cc_}")
    if date_iso:
        meta.append(f"- Date: {date_iso}")
    elif date_raw:
        meta.append(f"- Date: {date_raw}")
    if meta:
        lines.extend(meta)
        lines.append("")
        lines.append("---")
        lines.append("")
    return "\n".join(lines)


def _pandoc_html_to_gfm(html: str) -> str:
    try:
        proc = subprocess.run(
            ["pandoc", "-f", "html", "-t", "gfm", "--wrap=none"],
            input=html,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
    except FileNotFoundError as e:
        raise RuntimeError("pandoc 未安装或不在 PATH 中（需要 pandoc 来把 HTML 转成 Markdown）。") from e
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"pandoc 转换失败：{e.stderr.strip()}") from e
    return proc.stdout


def _cleanup_text(s: str) -> str:
    # Normalize newlines, strip NULs
    s = s.replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "")
    # Collapse excessive trailing spaces
    s = re.sub(r"[ \t]+\n", "\n", s)
    return s


_QUOTE_CUTOFF_PATTERNS = [
    r"^From:\s",  # common in quoted replies
    r"^To:\s",
    r"^Cc:\s",
    r"^Date:\s",
    r"^Subject:\s",
    r"^-----Original Message-----\s*$",
    r"^On .+ wrote:\s*$",
    r"^在.+写道[:：]\s*$",
    r"^发件人[:：]\s*",
    r"^发送时间[:：]\s*",
    r"^收件人[:：]\s*",
    r"^主题[:：]\s*",
]

_SIGNATURE_CUTOFF_PATTERNS = [
    r"^--\s*$",  # signature delimiter
    r"^--\s",  # signature delimiter with text
    r"^(Kind regards|Kind Regards|Best regards|Best Regards|Regards|Sincerely)[,]?\s*$",
    r"^谢谢[!！]?\s*$",
    r"^此致[，,]?\s*敬礼\s*$",
]


def _strip_quoted_history(text: str) -> str:
    """
    Keep only the newest message content by cutting off at the first
    strong "quote boundary" marker.
    """
    lines = text.split("\n")
    cutoff_re = re.compile("|".join(f"(?:{p})" for p in _QUOTE_CUTOFF_PATTERNS), re.IGNORECASE)
    for i, line in enumerate(lines):
        if cutoff_re.search(line):
            # Only cut if we already have some real content above.
            if any(l.strip() for l in lines[:i]):
                return "\n".join(lines[:i]).rstrip()
    return text.rstrip()


def _strip_signature(text: str) -> str:
    """
    Remove common signature blocks starting at typical markers.
    """
    lines = text.split("\n")
    sig_re = re.compile("|".join(f"(?:{p})" for p in _SIGNATURE_CUTOFF_PATTERNS))
    for i, line in enumerate(lines):
        if sig_re.search(line.strip()):
            if any(l.strip() for l in lines[:i]):
                return "\n".join(lines[:i]).rstrip()
    return text.rstrip()


def _postprocess_md(md: str, *, strip_quoted: bool, strip_signature: bool) -> str:
    md = _cleanup_text(md)
    if strip_quoted:
        md = _strip_quoted_history(md)
    if strip_signature:
        md = _strip_signature(md)
    return md.rstrip()


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="Convert .eml files to Markdown")
    p.add_argument("input_eml", help="Path to .eml file")
    p.add_argument("-o", "--output", help="Output .md path (default: <input>.md)")
    p.add_argument("--stdout", action="store_true", help="Write Markdown to stdout")
    p.add_argument("--no-headers", action="store_true", help="Do not include email headers")
    p.add_argument("--keep-quoted", action="store_true", help="Keep quoted history / forwarded content")
    p.add_argument("--keep-signature", action="store_true", help="Keep signature blocks")
    args = p.parse_args(argv)

    in_path = args.input_eml
    if not os.path.exists(in_path):
        print(f"输入文件不存在：{in_path}", file=sys.stderr)
        return 2

    with open(in_path, "rb") as f:
        msg = BytesParser(policy=policy.default).parse(f)

    kind, body = _extract_best_body(msg)
    body = _cleanup_text(body)

    md_parts = []
    if not args.no_headers:
        md_parts.append(_format_headers(msg))

    if kind == "html":
        md_parts.append(_pandoc_html_to_gfm(body))
    else:
        # For text/plain we keep as-is (already "mostly markdown-friendly").
        md_parts.append(body)

    md = "\n".join([x for x in md_parts if x is not None])
    md = _postprocess_md(
        md,
        strip_quoted=not args.keep_quoted,
        strip_signature=not args.keep_signature,
    ).rstrip() + "\n"

    if args.stdout:
        sys.stdout.write(md)
        return 0

    out_path = args.output
    if not out_path:
        base, _ = os.path.splitext(in_path)
        out_path = base + ".md"

    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
