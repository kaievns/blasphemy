from pathlib import Path
from typing import Callable

from . import convert
from .epub import Chapter

EXCERPT_WORDS = 120


def excerpts(chapters: list[Chapter], min_words: int = 200) -> str:
    lines = []
    for chapter in chapters:
        if chapter.is_nav or chapter.words < min_words:
            continue
        opening = " ".join(convert.html_to_markdown(chapter.html).split()[:EXCERPT_WORDS])
        lines.append(f"## Chapter {chapter.index}: {chapter.title or chapter.href}")
        lines.append(f"({chapter.words} words) {opening}\n")
    return "\n".join(lines)


def build(
    chapters: list[Chapter],
    generate: Callable[[str], str],
    workdir: Path,
    force: bool = False,
    min_words: int = 200,
) -> str:
    workdir.mkdir(parents=True, exist_ok=True)
    cache = workdir / "primer.md"
    if cache.exists() and not force:
        return cache.read_text()
    primer = generate(excerpts(chapters, min_words))
    cache.write_text(primer)
    return primer


def chapter_context(primer: str, chapter: Chapter) -> str:
    return (
        f"\n\n# Book context\n\n{primer}\n\n"
        f"# Current chapter\n\nYou are rewriting chapter {chapter.index}: "
        f"{chapter.title or chapter.href}. Chapters before it in the book may be "
        f"referenced in cumulative questions; chapters after it may not."
    )
