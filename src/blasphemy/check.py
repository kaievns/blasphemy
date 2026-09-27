import json
import re
from typing import Callable

from . import style

HEADING = re.compile(r"^(#{1,6})\s")
FENCE = re.compile(r"^\s*(`{3,}|~{3,})")
TOKEN = re.compile(r"⟦[^⟦⟧]*⟧")
TOP_SECTIONS = 2


def split_top(body: str) -> tuple[str, str]:
    """The answer layer plus the first TOP_SECTIONS sections, and the rest."""
    lines = body.split("\n")
    fence = None
    headings = []
    for i, line in enumerate(lines):
        opened = FENCE.match(line)
        if opened:
            marker = opened.group(1)
            if fence is None:
                fence = marker
            elif marker.startswith(fence[0]) and len(marker) >= len(fence):
                fence = None
            continue
        match = HEADING.match(line) if fence is None else None
        if match and i > 0:
            headings.append((i, len(match.group(1))))
    if not headings:
        return body, ""
    level = min(depth for _, depth in headings)
    sections = [i for i, depth in headings if depth == level]
    if len(sections) <= TOP_SECTIONS:
        return body, ""
    cut = sections[TOP_SECTIONS]
    return "\n".join(lines[:cut]), "\n".join(lines[cut:])


def request(source_md: str, top: str) -> str:
    return f"ORIGINAL:\n\n{source_md}\n\n---\n\nTOP:\n\n{top}"


def parse_fixes(reply: str) -> list[dict]:
    start, end = reply.find("{"), reply.rfind("}")
    if start < 0 or end < start:
        return []
    try:
        data = json.loads(reply[start:end + 1])
    except ValueError:
        return []
    fixes = data.get("fixes") if isinstance(data, dict) else None
    return [
        fix for fix in fixes or []
        if isinstance(fix, dict)
        and isinstance(fix.get("sentence"), str) and fix["sentence"].strip()
        and isinstance(fix.get("replacement"), str)
    ]


def _flat(text: str) -> str:
    return " ".join(text.split())


def rejection(top: str, source_md: str, fix: dict) -> str:
    """Why a fix must not be applied, or "" when it can be."""
    sentence, replacement = fix["sentence"], fix["replacement"]
    if top.count(sentence) != 1:
        return "sentence not found once in the opening"
    quote = fix.get("source") or ""
    if quote.strip() and _flat(quote) not in _flat(source_md):
        return "quoted evidence is not in the original"
    if not set(TOKEN.findall(sentence)) <= set(TOKEN.findall(replacement)):
        return "replacement drops a ⟦token⟧"
    if style.banned(source_md, replacement):
        return "replacement uses a banned word"
    return ""


def apply_fixes(top: str, source_md: str, fixes: list[dict]) -> tuple[str, list[dict], list[dict]]:
    applied, rejected = [], []
    for fix in fixes:
        reason = rejection(top, source_md, fix)
        if reason:
            rejected.append({**fix, "rejected": reason})
            continue
        replacement = fix["replacement"].strip()
        if replacement:
            top = top.replace(fix["sentence"], replacement, 1)
        else:
            top = re.sub(re.escape(fix["sentence"]) + r" ?", "", top, count=1)
        applied.append(fix)
    return top, applied, rejected


def patch(source_md: str, body: str, ask: Callable[[str], str]) -> tuple[str, dict]:
    top, rest = split_top(body)
    fixes = parse_fixes(ask(request(source_md, top)))
    patched, applied, rejected = apply_fixes(top, source_md, fixes)
    joined = f"{patched}\n{rest}" if rest else patched
    return joined, {"applied": applied, "rejected": rejected}
