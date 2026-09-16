import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from . import blocks, convert, cover, epub, style

RATIO_MIN = 0.05
RATIO_MAX = 1.5
# flat headroom for the apparatus pass, whose budget has a ~220-word floor:
# small reference chapters (tables, templates) keep their body ~verbatim, so
# without this a chapter under ~450 words could never pass the ceiling
APPARATUS_ALLOWANCE = 250


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
    return words_out <= words_in * RATIO_MAX + APPARATUS_ALLOWANCE


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
        source_file = workdir / f"{chapter.index:03d}.src.md"
        output_file = workdir / f"{chapter.index:03d}.md"

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
            if output_file.exists() and not force:
                output_md = output_file.read_text()
                status, detail = "cached", ""
            else:
                try:
                    output_md = rewrite(source_md, chapter)
                    if not sane(source_md, output_md):
                        failed_file = workdir / f"{chapter.index:03d}.failed.md"
                        failed_file.write_text(output_md)
                        raise ValueError(
                            f"output failed sanity check (word ratio), see {failed_file}"
                        )
                    output_file.write_text(output_md)
                    status, detail = "rewritten", ""
                    slipped = style.banned(source_md, output_md)
                    if slipped:
                        detail = f"banned words: {', '.join(slipped)}"
                except Exception as error:
                    output_md, status, detail = None, "failed", str(error)
            if output_md is not None:
                html, missing = blocks.restore(
                    convert.markdown_to_html(output_md), protected
                )
                if missing:
                    if not rebuild:
                        (workdir / f"{chapter.index:03d}.failed.md").write_text(output_md)
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
