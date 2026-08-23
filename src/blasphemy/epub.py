from dataclasses import dataclass
from pathlib import Path

from bs4 import BeautifulSoup
from ebooklib import ITEM_DOCUMENT, epub


@dataclass
class Chapter:
    index: int
    item_id: str
    href: str
    title: str
    html: str
    words: int


def load(path: str | Path) -> epub.EpubBook:
    book = epub.read_epub(str(path))
    _ensure_toc_uids(book.toc)
    return book


def _ensure_toc_uids(entries, counter: list[int] | None = None) -> None:
    # ebooklib can't write an NCX whose parsed Links lack uids
    counter = counter if counter is not None else [0]
    for entry in entries:
        if isinstance(entry, (tuple, list)):
            _ensure_toc_uids(entry, counter)
        elif isinstance(entry, epub.Link) and not entry.uid:
            counter[0] += 1
            entry.uid = f"navpoint-{counter[0]}"


def chapters(book: epub.EpubBook) -> list[Chapter]:
    result = []
    docs = {item.get_id(): item for item in book.get_items_of_type(ITEM_DOCUMENT)}
    for index, (item_id, _linear) in enumerate(book.spine):
        item = docs.get(item_id)
        if item is None:
            continue
        html = item.get_content().decode("utf-8", errors="replace")
        soup = BeautifulSoup(html, "html.parser")
        heading = soup.find(["h1", "h2", "h3"])
        title = heading.get_text(strip=True) if heading else ""
        words = len(soup.get_text().split())
        result.append(Chapter(index, item_id, item.get_name(), title, html, words))
    return result


def replace_content(book: epub.EpubBook, item_id: str, body_html: str) -> None:
    item = book.get_item_with_id(item_id)
    document = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<html xmlns="http://www.w3.org/1999/xhtml">'
        f"<head><title></title></head><body>{body_html}</body></html>"
    )
    item.set_content(document.encode("utf-8"))


def save(book: epub.EpubBook, path: str | Path) -> None:
    epub.write_epub(str(path), book)
