import re
from typing import Callable

from . import check, pipeline, style

HEADING = re.compile(r"^#{1,6}\s")
FENCED = re.compile(r"^[ \t]*(`{3,}|~{3,}).*?^[ \t]*\1[^\n]*$", re.S | re.M)
LINK = re.compile(r"\]\(([^)]*)\)")
ATTEMPTS = 2
LENGTH_RANGE = (0.8, 1.1)


def request(source_md: str, body: str) -> str:
    return f"ORIGINAL:\n\n{source_md}\n\n---\n\nREWRITE:\n\n{body}"


def _outline(md: str) -> tuple[list[str], list[str], list[str]]:
    lines = [line.strip() for line in FENCED.sub("", md).splitlines()]
    return (
        [line for line in lines if HEADING.match(line)],
        [line for line in lines if line.startswith("|")],
        [match.group(0).strip() for match in FENCED.finditer(md)],
    )


def revision_problem(source_md: str, before: str, after: str) -> str:
    """Why a revised chapter must not replace the body, or "" when it can."""
    problem = pipeline.body_problem(source_md, after)
    if problem:
        return problem
    if set(check.TOKEN.findall(before)) != set(check.TOKEN.findall(after)):
        return "⟦tokens⟧ changed"
    headings, tables, code = _outline(before)
    headings_after, tables_after, code_after = _outline(after)
    if headings != headings_after:
        return "headings changed"
    if code != code_after:
        return "code changed"
    if tables != tables_after:
        return "tables changed"
    if not set(LINK.findall(before)) <= set(LINK.findall(after)):
        return "a link was dropped"
    if style.banned(source_md, after):
        return "banned word"
    ratio = len(after.split()) / max(len(before.split()), 1)
    if not LENGTH_RANGE[0] <= ratio <= LENGTH_RANGE[1]:
        return f"length {ratio:.0%} of the body"
    return ""


def polish(source_md: str, body: str, ask: Callable[[str], str]) -> tuple[str, dict]:
    """The revised body, or the body unchanged when no attempt passes the guards."""
    problems = []
    for _ in range(ATTEMPTS):
        revised = ask(request(source_md, body)).strip() + "\n"
        problem = revision_problem(source_md, body, revised)
        if not problem:
            return revised, {"attempts": len(problems) + 1, "rejected": problems}
        problems.append(problem)
    return body, {"attempts": ATTEMPTS, "rejected": problems, "kept_body": True}
