import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from . import blocks, convert, cover, epub, style

RATIO_MIN = 0.05
RATIO_MAX = 1.5
# the lowest body ratio across 98 sample rewrites (2026-09) was 0.56
BODY_RATIO_MIN = 0.35
UNCLOSED_TOKEN = re.compile(r"⟦[^⟦⟧]*(?=⟦|\Z)")
TITLE_TOKEN = re.compile(r"⟦TITLE-\d+[^⟧]*⟧\s*$")
LEADING_ANCHORS = re.compile(r"^(?:⟦ANCHOR:[^⟧]*⟧\s*)+")
RETIRED_APPARATUS = re.compile(r"\n## Key points\n(?:(?!\n#{1,2} ).)*?(?:\n## Check yourself\n.*)?\Z", re.S)
KEY_POINTS_HEADING = re.compile(r"^#+\s*key points\s*$", re.I | re.M)


@dataclass
class Result:
    index: int
    item_id: str
    title: str
    status: str  # rewritten | cached | skipped | failed
    words_in: int
    words_out: int
    detail: str = ""


def workdir_for(epub_path: Path, root: Path | None = None) -> Path:
    digest = hashlib.sha256(epub_path.read_bytes()).hexdigest()[:8]
    return (root or Path(".blasphemy")) / f"{epub_path.stem}-{digest}"


def chapter_file(workdir: str | Path, index: int, kind: str = "") -> Path:
    return Path(workdir) / f"{index:03d}{'.' + kind if kind else ''}.md"


def referenced_anchors(book, chapters: list[epub.Chapter]) -> dict[str, set[str]]:
    refs: dict[str, set[str]] = {}

    def add(file: str, fragment: str, same_file: str) -> None:
        name = (file or same_file).split("/")[-1]
        refs.setdefault(name, set()).add(fragment)

    for chapter in chapters:
        for match in re.finditer(r'href="([^"#]*)#([^"]+)"', chapter.html):
            add(match.group(1), match.group(2), chapter.href)

    def walk(entries) -> None:
        for entry in entries:
            if isinstance(entry, (tuple, list)):
                walk(entry)
            else:
                href = getattr(entry, "href", "") or ""
                if "#" in href:
                    file, fragment = href.split("#", 1)
                    add(file, fragment, file)

    walk(book.toc)
    return refs


def sane(source_md: str, output_md: str) -> bool:
    words_in = max(len(source_md.split()), 1)
    words_out = len(output_md.split())
    if words_out < words_in * RATIO_MIN:
        return False
    return words_out <= words_in * RATIO_MAX


def unclosed_token(md: str) -> bool:
    return bool(UNCLOSED_TOKEN.search(md))


def is_title(line: str) -> bool:
    # a `# ` heading, or the token a protected chapter title travels as
    return line.startswith("# ") or bool(TITLE_TOKEN.match(line))


def opening_line(md: str) -> str:
    for line in md.splitlines():
        rest = LEADING_ANCHORS.sub("", line.strip())
        if rest:
            return rest
    return ""


def upgrade_cached(source_md: str, md: str) -> str:
    """A cached output without what the retired assembler added (2026-09-26):
    the apparatus tail and, on Pandoc books, a doubled title."""
    if not KEY_POINTS_HEADING.search(source_md):
        md = RETIRED_APPARATUS.sub("", md)
    lines = md.strip().split("\n")
    if lines and is_title(lines[0]) and opening_line("\n".join(lines[1:])) == lines[0].strip():
        lines = lines[1:]
    return "\n".join(lines).strip()


def body_problem(source_md: str, body: str) -> str:
    """Why a body-pass result must not ship, or "" when it looks whole."""
    lines = [line for line in body.splitlines() if line.strip()]
    if is_title(opening_line(source_md)) and not is_title(opening_line(body)):
        return "body does not open with the chapter title"
    if unclosed_token(body):
        return "body cut off inside a ⟦token⟧"
    if lines and lines[-1].lstrip().startswith("#"):
        return "body ends on a bare heading"
    ratio = len(body.split()) / max(len(source_md.split()), 1)
    if ratio < BODY_RATIO_MIN:
        return f"body is {ratio:.0%} of the chapter"
    return ""


def optimise(
    epub_path: str | Path,
    out_path: str | Path,
    rewrite: Callable[[str, epub.Chapter], str],
    workdir: str | Path,
    min_words: int = 200,
    skip: set[int] | None = None,
    only: set[int] | None = None,
    force: bool = False,
    rebuild: bool = False,  # read-only reassembly: never evict the cache
    title_suffix: str = " (Optimised)",
    badge_text: str | None = "OPTIMISED",
    progress: Callable[[Result], None] = lambda r: None,
    starting: Callable[[epub.Chapter], None] = lambda c: None,
) -> list[Result]:
    epub_path = Path(epub_path)
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)

    book = epub.load(epub_path)
    all_chapters = epub.chapters(book)
    refs = referenced_anchors(book, all_chapters)
    results = []
    for chapter in all_chapters:
        starting(chapter)
        # blocks first: an anchor inside a protected figure travels with it,
        # so tokenising it too would restore the same id twice
        block_html, protected = blocks.protect(chapter.html)
        protected_html, anchor_ids = blocks.protect_anchors(
            block_html, refs.get(chapter.href.split("/")[-1], set())
        )
        source_md = convert.html_to_markdown(protected_html)
        source_file = chapter_file(workdir, chapter.index, "src")
        output_file = chapter_file(workdir, chapter.index)
        failed_file = chapter_file(workdir, chapter.index, "failed")

        if (
            chapter.passthrough
            or chapter.words < min_words
            or chapter.index in (skip or set())
            or (only is not None and chapter.index not in only)
        ):
            result = Result(
                chapter.index, chapter.item_id, chapter.title,
                "skipped", chapter.words, chapter.words,
            )
        else:
            source_file.write_text(source_md)
            cached = (
                output_file.read_text() if output_file.exists() and not force else None
            )
            stale = ""
            if cached is not None:
                upgraded = upgrade_cached(source_md, cached)
                problem = body_problem(source_md, upgraded)
                if problem:
                    stale, cached = f"cached rewrite unusable ({problem})", None
                else:
                    if upgraded != cached and not rebuild:
                        output_file.write_text(upgraded)
                    cached = upgraded
            if cached is not None:
                output_md = cached
                status, detail = "cached", ""
            else:
                try:
                    output_md = rewrite(source_md, chapter)
                    problem = ""
                    if not sane(source_md, output_md):
                        problem = "output failed sanity check (word ratio)"
                    elif unclosed_token(output_md):
                        problem = "output cut off inside a ⟦token⟧"
                    if problem:
                        failed_file.write_text(output_md)
                        raise ValueError(f"{problem}, see {failed_file}")
                    output_file.write_text(output_md)
                    status, detail = "rewritten", ""
                    slipped = style.banned(source_md, output_md)
                    if slipped:
                        detail = f"banned words: {', '.join(slipped)}"
                except Exception as error:
                    output_md, status = None, "failed"
                    detail = f"{stale}: {error}" if stale else str(error)
                    if force and not rebuild and output_file.exists():
                        output_file.replace(chapter_file(workdir, chapter.index, "stale"))
            if output_md is not None:
                html, missing = blocks.restore(
                    convert.markdown_to_html(output_md), protected
                )
                if missing:
                    if not rebuild:
                        failed_file.write_text(output_md)
                        output_file.unlink(missing_ok=True)
                    output_md, status = None, "failed"
                    detail = f"lost protected blocks: {', '.join(missing)}"
                else:
                    html, lost_anchors = blocks.restore_anchors(html, anchor_ids)
                    if lost_anchors:
                        note = f"anchors fell back to top: {', '.join(lost_anchors)}"
                        detail = f"{detail}; {note}" if detail else note
                    html, unmatched = blocks.restore_pre(
                        html, blocks.extract_pre(chapter.html)
                    )
                    if unmatched:
                        note = f"{unmatched} code block(s) left fenced (no matching original)"
                        detail = f"{detail}; {note}" if detail else note
                    html = blocks.carry_lead_class(html, chapter.html)
                    html = blocks.restore_captions(html, chapter.html)
                    html = blocks.restyle_notes(html, chapter.html)
                    # tokens from a cache written by an older pipeline are
                    # unrestorable here; never ship them to the reader
                    html = blocks.strip_tokens(html)
                    epub.replace_content(book, chapter.item_id, html)
            result = Result(
                chapter.index, chapter.item_id, chapter.title, status,
                len(source_md.split()),
                len(output_md.split()) if output_md else 0,
                detail,
            )
        results.append(result)
        progress(result)

    if title_suffix:
        epub.retitle(book, title_suffix)
    if badge_text:
        cover_item = epub.cover_image(book)
        if cover_item is not None:
            cover_item.set_content(cover.badge(cover_item.get_content(), badge_text))

    epub.save(book, out_path)
    return results
