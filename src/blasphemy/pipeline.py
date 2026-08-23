import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from . import blocks, convert, cover, epub

RATIO_MIN = 0.05
RATIO_MAX = 1.5


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


def sane(source_md: str, output_md: str) -> bool:
    words_in = max(len(source_md.split()), 1)
    ratio = len(output_md.split()) / words_in
    return RATIO_MIN <= ratio <= RATIO_MAX


def optimise(
    epub_path: str | Path,
    out_path: str | Path,
    rewrite: Callable[[str], str],
    workdir: str | Path,
    min_words: int = 200,
    skip: set[int] | None = None,
    force: bool = False,
    title_suffix: str = " (Optimised)",
    badge_text: str | None = "OPTIMISED",
    progress: Callable[[Result], None] = lambda r: None,
) -> list[Result]:
    epub_path = Path(epub_path)
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)

    book = epub.load(epub_path)
    results = []
    for chapter in epub.chapters(book):
        protected_html, protected = blocks.protect(chapter.html)
        source_md = convert.html_to_markdown(protected_html)
        source_file = workdir / f"{chapter.index:03d}.src.md"
        output_file = workdir / f"{chapter.index:03d}.md"

        if chapter.is_nav or chapter.words < min_words or chapter.index in (skip or set()):
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
                    output_md = rewrite(source_md)
                    if not sane(source_md, output_md):
                        failed_file = workdir / f"{chapter.index:03d}.failed.md"
                        failed_file.write_text(output_md)
                        raise ValueError(
                            f"output failed sanity check (word ratio), see {failed_file}"
                        )
                    output_file.write_text(output_md)
                    status, detail = "rewritten", ""
                except Exception as error:
                    output_md, status, detail = None, "failed", str(error)
            if output_md is not None:
                html, missing = blocks.restore(
                    convert.markdown_to_html(output_md), protected
                )
                if missing:
                    (workdir / f"{chapter.index:03d}.failed.md").write_text(output_md)
                    output_file.unlink(missing_ok=True)
                    output_md, status = None, "failed"
                    detail = f"lost protected blocks: {', '.join(missing)}"
                else:
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
