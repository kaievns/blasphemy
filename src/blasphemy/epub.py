import re
from dataclasses import dataclass
from pathlib import Path

from bs4 import BeautifulSoup
from ebooklib import ITEM_COVER, ITEM_DOCUMENT, ITEM_IMAGE, epub

DC = "http://purl.org/dc/elements/1.1/"


REFERENCE_TITLES = re.compile(
    r"^(index|glossary|bibliography|references|works cited|notes|"
    r"(table of )?contents( in detail)?)$",
    re.I,
)
REFERENCE_TYPES = re.compile(r"\b(index|glossary|bibliography|toc|landmarks)\b", re.I)
REFERENCE_CLASSES = REFERENCE_TYPES


@dataclass
class Chapter:
    index: int
    item_id: str
    href: str
    title: str
    html: str
    words: int
    is_nav: bool = False
    is_reference: bool = False  # index, glossary, bibliography, contents

    @property
    def passthrough(self) -> bool:
        return self.is_nav or self.is_reference


def _is_reference(soup: BeautifulSoup, title: str) -> bool:
    """Reference apparatus that must not be rewritten.

    An index or bibliography is a lookup structure, not an argument: a
    rewrite destroys it (Statistics' index came back as 23 code blocks with
    an "Orient" paragraph) and burns a chapter's worth of credits doing so.
    """
    if REFERENCE_TITLES.match(title.strip()):
        return True
    for node in soup.find_all(["body", "section", "nav", "div"], attrs={"epub:type": True}):
        if REFERENCE_TYPES.search(node["epub:type"]):
            return True
    body = soup.body or soup
    for node in body.find_all(["div", "section"], class_=True, limit=3):
        if any(REFERENCE_CLASSES.fullmatch(cls) for cls in node["class"]):
            return True
    return False


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
        # item.content is the raw document; get_content() regenerates from a
        # template and drops the head
        html = item.content.decode("utf-8", errors="replace")
        soup = BeautifulSoup(html, "html.parser")
        heading = soup.find(["h1", "h2", "h3"])
        title = heading.get_text(strip=True) if heading else ""
        words = len(soup.get_text().split())
        result.append(
            Chapter(
                index, item_id, item.get_name(), title, html, words,
                is_nav=isinstance(item, epub.EpubNav),
                is_reference=_is_reference(soup, title),
            )
        )
    return result


def replace_content(book: epub.EpubBook, item_id: str, body_html: str) -> None:
    # original head (stylesheet links) and body attrs survive so CSS keeps applying
    item = book.get_item_with_id(item_id)
    original = BeautifulSoup(
        item.content.decode("utf-8", errors="replace"), "html.parser"
    )
    head = (
        "".join(str(child) for child in original.head.contents)
        if original.head
        else "<title></title>"
    )
    attrs = ""
    if original.body:
        for name, value in original.body.attrs.items():
            joined = " ".join(value) if isinstance(value, list) else value
            attrs += f' {name}="{joined}"'
    document = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<html xmlns="http://www.w3.org/1999/xhtml" '
        'xmlns:epub="http://www.idpf.org/2007/ops">'
        f"<head>{head}</head><body{attrs}>{body_html}</body></html>"
    )
    item.set_content(document.encode("utf-8"))


def retitle(book: epub.EpubBook, suffix: str) -> None:
    titles = book.metadata.get(DC, {}).get("title") or []
    if titles:
        text, attrs = titles[0]
        book.metadata[DC]["title"] = [(f"{text}{suffix}", attrs)] + titles[1:]


def cover_image(book: epub.EpubBook):
    for item in book.get_items_of_type(ITEM_COVER):
        return item
    for _value, attrs in book.metadata.get(None, {}).get("meta", []):
        if attrs.get("name") == "cover":
            item = book.get_item_with_id(attrs.get("content"))
            if item is not None:
                return item
    for item in book.get_items_of_type(ITEM_IMAGE):
        if "cover" in item.get_name().lower() or "cover" in item.get_id().lower():
            return item
    return None


class _RawHtml(epub.EpubHtml):
    # EpubHtml.get_content() regenerates the document from a template on write,
    # discarding the original head (stylesheets) and body attributes
    def get_content(self, default=None):
        return self.content or default or b""


def save(book: epub.EpubBook, path: str | Path) -> None:
    # a nav doc without content (freshly built book) still needs generating
    for item in book.get_items_of_type(ITEM_DOCUMENT):
        if isinstance(item, epub.EpubNav):
            if item.content:
                if "nav" not in item.properties:
                    item.properties.append("nav")
                item.__class__ = _RawHtml
        elif type(item) is epub.EpubHtml:
            item.__class__ = _RawHtml
    epub.write_epub(str(path), book)
