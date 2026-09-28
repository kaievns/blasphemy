import re
import zipfile
from dataclasses import dataclass
from html import escape as html_escape
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
MATTER_TITLES = re.compile(
    r"^(foreword|preface|acknowledge?ments?|praise\b|reviews for|about the authors?|"
    r"dedication|colophon|copyright( page)?$|"
    r"part\s+([ivxlcdm]+|\d+|one|two|three|four|five|six|seven|eight|nine|ten)\b|appendix\b)",
    re.I,
)
MATTER_TYPES = re.compile(
    r"\b(frontmatter|backmatter|copyright-page|titlepage|halftitlepage|dedication|"
    r"epigraph|foreword|preface|acknowledgments|colophon|imprint|contributors|"
    r"other-credits|errata|endnotes|rearnotes|appendix|part)\b",
    re.I,
)
MATTER_CLASSES = re.compile(r"^(preface|colophon|dedication|acknowledgments|appendix|copyright)$", re.I)
CHAPTER_TYPES = re.compile(r"\b(introduction|prologue|chapter|bodymatter)\b", re.I)


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
    is_matter: bool = False  # front/back matter, part dividers, appendices

    @property
    def passthrough(self) -> bool:
        return self.is_nav or self.is_reference or self.is_matter


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


def _is_matter(soup: BeautifulSoup, title: str, words: int) -> bool:
    """Front and back matter, part dividers and appendices: passed through,
    because the reader skips them (specs/prompt.md, 2026-08-25)."""
    title = title.strip()
    body = soup.body or soup
    typed = [node["epub:type"] for node in body.find_all(["section", "div"], attrs={"epub:type": True}, limit=3)]
    if soup.body is not None and soup.body.get("epub:type"):
        typed.append(soup.body["epub:type"])
    if re.match(r"introduction\b", title, re.I) or any(CHAPTER_TYPES.search(t) for t in typed):
        return False
    if MATTER_TITLES.match(title) or any(MATTER_TYPES.search(t) for t in typed):
        return True
    for node in body.find_all(["div", "section"], class_=True, limit=3):
        if any(MATTER_CLASSES.fullmatch(cls) for cls in node["class"]):
            return True
    return words < 1000 and "all rights reserved" in body.get_text(" ").lower()


def package_prefixes(path: str | Path) -> list[tuple[str, str]]:
    """The `prefix` declarations on the source package; ebooklib rewrites the
    OPF with only its own, leaving e.g. ibooks: meta properties undeclared."""
    with zipfile.ZipFile(path) as archive:
        container = archive.read("META-INF/container.xml").decode("utf-8", "replace")
        opf = re.search(r'full-path="([^"]+)"', container)
        head = archive.read(opf.group(1)).decode("utf-8", "replace") if opf else ""
    package = re.search(r"<package\b[^>]*>", head, re.S)
    declared = re.search(r"\bprefix\s*=\s*([\"'])(.*?)\1", package.group(), re.S) if package else None
    return re.findall(r"([\w-]+):\s+(\S+)", declared.group(2)) if declared else []


def load(path: str | Path) -> epub.EpubBook:
    book = epub.read_epub(str(path))
    _ensure_toc_uids(book.toc)
    for name, uri in package_prefixes(path):
        if name != "rendition":  # ebooklib always writes this one
            book.add_prefix(name, uri)
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
        # spans a publisher separates with CSS ("1" "The Big Picture") need a space
        title = " ".join(heading.get_text(" ", strip=True).split()) if heading else ""
        words = len(soup.get_text().split())
        result.append(
            Chapter(
                index, item_id, item.get_name(), title, html, words,
                is_nav=isinstance(item, epub.EpubNav),
                is_reference=_is_reference(soup, title),
                is_matter=_is_matter(soup, title, words),
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
        attrs = _attrs(original.body.attrs)
        body_html = _rewrap(original.body, body_html)
    document = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<html xmlns="http://www.w3.org/1999/xhtml" '
        'xmlns:epub="http://www.idpf.org/2007/ops">'
        f"<head>{head}</head><body{attrs}>{body_html}</body></html>"
    )
    item.set_content(document.encode("utf-8"))


def _attrs(attrs: dict, skip: set[str] = frozenset()) -> str:
    out = ""
    for name, value in attrs.items():
        if name in skip:
            continue
        joined = " ".join(value) if isinstance(value, list) else value
        out += f' {name}="{html_escape(str(joined), quote=True)}"'
    return out


def _rewrap(body, body_html: str) -> str:
    """Put the rewritten body back inside the elements that alone held the
    original body (DocBook's div.chapter), which the book's CSS keys on."""
    opening, closing, node = "", "", body
    ids = set(re.findall(r'\bid="([^"]+)"', body_html))
    while True:
        children = [c for c in node.children if getattr(c, "name", None)]
        text = [c for c in node.children if not getattr(c, "name", None) and str(c).strip()]
        if len(children) != 1 or text:
            break
        node = children[0]
        opening += f"<{node.name}{_attrs(node.attrs, {'id'} if node.get('id') in ids else set())}>"
        closing = f"</{node.name}>" + closing
    return opening + body_html + closing


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
    if str(getattr(book, "version", None) or "").startswith("2"):
        _as_epub2(Path(path))


def _as_epub2(path: Path) -> None:
    # ebooklib always writes a 3.0 package; an EPUB 2 book's content only
    # validates against 2.0, so its package goes back to 2.0 as well
    tmp = path.with_suffix(".tmp")
    with zipfile.ZipFile(path) as src, zipfile.ZipFile(tmp, "w") as out:
        for info in src.infolist():
            data = src.read(info.filename)
            if info.filename.endswith(".opf"):
                opf = data.decode("utf-8")
                opf = re.sub(r'(<package\b[^>]*?)\bversion="3\.0"', r'\1version="2.0"', opf, count=1)
                opf = re.sub(r'(<package\b[^>]*?)\s+prefix="[^"]*"', r"\1", opf, count=1)
                opf = re.sub(r"\s*<meta\s+property=\"[^\"]*\"[^>]*>[^<]*</meta>", "", opf)
                opf = re.sub(r'(<item\b[^>]*?)\s+properties="[^"]*"', r"\1", opf)
                data = opf.encode("utf-8")
            stored = info.filename == "mimetype"
            out.writestr(info, data, compress_type=zipfile.ZIP_STORED if stored else zipfile.ZIP_DEFLATED)
    tmp.replace(path)
