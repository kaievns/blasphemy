import re


def section(raw: str, name: str) -> str:
    match = re.search(rf"=== {name} ===\n(.*?)(?=\n=== |\Z)", raw, re.S)
    return match.group(1).strip() if match else ""


def insert_pauses(body: str, pauses: str) -> tuple[str, int, int]:
    paragraphs = body.split("\n\n")
    inserted = skipped = 0
    for match in re.finditer(r"AFTER:\s*(.+)\nPAUSE:\s*(.+)", pauses):
        locator = match.group(1).strip().strip('"')
        pause = match.group(2).strip()
        hit = next(
            (
                i
                for i, para in enumerate(paragraphs)
                if para.rstrip().endswith(locator) or locator in para
            ),
            None,
        )
        # a skipped pause beats a misplaced one
        if (
            hit is None
            or hit < 3
            or (hit + 1 < len(paragraphs) and paragraphs[hit + 1].lstrip().startswith("#"))
        ):
            skipped += 1
            continue
        paragraphs.insert(hit + 1, f"**Pause:** {pause}")
        inserted += 1
    return "\n\n".join(paragraphs), inserted, skipped


def _title(source_md: str, body: str) -> tuple[str, str]:
    lines = body.splitlines()
    if lines and lines[0].startswith("# "):
        return lines[0], "\n".join(lines[1:]).strip()
    for line in source_md.splitlines():
        if line.startswith("# "):
            return line, body
    return "", body


def assemble(source_md: str, body: str, raw: str) -> str:
    orient = section(raw, "ORIENT")
    watch = section(raw, "WATCH FOR")
    key_points = section(raw, "KEY POINTS")
    check = section(raw, "CHECK YOURSELF")
    answers = section(raw, "ANSWERS")

    title, body = _title(source_md, body)
    if not (orient or key_points):
        return f"{title}\n\n{body}" if title else body

    body, _inserted, _skipped = insert_pauses(body, section(raw, "PAUSES"))
    parts = []
    if title:
        parts.append(title)
    if orient:
        parts.append(f"**Orient.** {orient}")
    if watch:
        parts.append(f"**Watch for**\n\n{watch}")
    parts.append(body)
    if key_points:
        parts.append(f"## Key points\n\n{key_points}")
    if check:
        block = f"## Check yourself\n\n{check}"
        if answers:
            block += f"\n\n**Answers**\n\n{answers}"
        parts.append(block)
    return "\n\n".join(parts)
