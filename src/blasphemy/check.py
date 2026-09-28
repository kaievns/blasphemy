import json
import re
from typing import Callable

from . import pipeline, style

HEADING = re.compile(r"^(#{1,6})\s")
FENCE = re.compile(r"^\s*(`{3,}|~{3,})")
TOKEN = re.compile(r"⟦[^⟦⟧]*⟧")
TOP_SECTIONS = 2
PASSES = 2


def split_top(body: str) -> tuple[str, str]:
    """The chapter-level opening plus the first TOP_SECTIONS sections, and the rest."""
    lines = body.split("\n")
    opening = pipeline.opening_line(body)
    title_at = next(
        (i for i, line in enumerate(lines) if line.strip() and pipeline.LEADING_ANCHORS.sub("", line.strip()) == opening),
        None,
    ) if pipeline.is_title(opening) else None
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
        if match and i != title_at:
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


def parse_fixes(reply: str) -> list[dict] | None:
    """The fixes in the reply, or None when no {"fixes": [...]} object parses."""
    decoder = json.JSONDecoder()
    fixes = None
    for start in [i for i, char in enumerate(reply) if char == "{"]:
        try:
            data, _ = decoder.raw_decode(reply, start)
        except ValueError:
            continue
        if isinstance(data, dict) and isinstance(data.get("fixes"), list):
            fixes = data["fixes"]
            break
    if fixes is None:
        return None
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
    start = top.index(sentence)
    line = top[top.rfind("\n", 0, start) + 1:].lstrip()
    if "\n" in sentence or line.startswith(("#", "|", "⟦TITLE")):
        return "sentence is structure, not prose"
    if "\n" in replacement or ("|" in replacement and "|" not in sentence):
        return "replacement changes structure"
    quote = fix.get("source") or ""
    if quote.strip() and _flat(quote) not in _flat(source_md):
        return "quoted evidence is not in the original"
    if not set(TOKEN.findall(sentence)) <= set(TOKEN.findall(replacement)):
        return "replacement drops a ⟦token⟧"
    if style.banned(source_md, replacement):
        return "replacement uses a banned word"
    return ""


def _join(top: str, rest: str) -> str:
    return f"{top}\n{rest}" if rest else top


def apply_fixes(
    top: str, source_md: str, fixes: list[dict], rest: str = ""
) -> tuple[str, list[dict], list[dict]]:
    applied, rejected = [], []
    for fix in fixes:
        reason = rejection(top, source_md, fix)
        if reason:
            rejected.append({**fix, "rejected": reason})
            continue
        replacement = fix["replacement"].strip()
        if replacement:
            candidate = top.replace(fix["sentence"], replacement, 1)
        else:
            candidate = re.sub(re.escape(fix["sentence"]) + r" ?", "", top, count=1)
        if pipeline.body_problem(source_md, _join(candidate, rest)):
            rejected.append({**fix, "rejected": "breaks the body check"})
            continue
        top = candidate
        applied.append(fix)
    return top, applied, rejected


def patch(source_md: str, body: str, ask: Callable[[str], str]) -> tuple[str, dict]:
    top, rest = split_top(body)
    reply = ask(request(source_md, top))
    fixes = parse_fixes(reply)
    if fixes is None:
        return body, {"error": "unparseable reply", "reply": reply[:500]}
    patched, applied, rejected = apply_fixes(top, source_md, fixes, rest)
    return _join(patched, rest), {"applied": applied, "rejected": rejected}


def patch_repeatedly(
    source_md: str, body: str, ask: Callable[[str], str], passes: int = PASSES
) -> tuple[str, dict]:
    """Check the opening `passes` times, each on the last result; a failing or breaking pass stops the loop."""
    reports = []
    for _ in range(passes):
        try:
            patched, report = patch(source_md, body, ask)
        except Exception as error:
            reports.append({"error": str(error)})
            break
        problem = pipeline.body_problem(source_md, patched)
        if problem:
            reports.append({**report, "reverted": problem})
            break
        body = patched
        reports.append(report)
    return body, {"passes": reports}
