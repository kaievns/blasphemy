import copy
import posixpath
import re
from urllib.parse import unquote

from bs4 import BeautifulSoup
from ebooklib import ITEM_NAVIGATION
from ebooklib import epub as eb

from .blocks import is_callout

SECTION_HEADINGS = ["h1", "h2", "h3", "h4"]
SLUG = re.compile(r"[^a-z0-9]+")


def _in_callout(node) -> bool:
    return any(is_callout(p) for p in node.find_parents(["aside", "div", "section"]))


def number_headings(html: str) -> tuple[str, list[tuple[int, str, str]]]:
    """Give the rewritten chapter's section headings ids and list them as
    (depth, id, text), depth 1 or 2 below the chapter title."""
    soup = BeautifulSoup(html, "html.parser")
    headings = [h for h in soup.find_all(SECTION_HEADINGS) if not _in_callout(h)]
    title = headings[0] if headings else None
    if title is not None and title.find_parent("header") is not None:
        headings = [h for h in headings if h.find_parent("header") is None]
    else:
        headings = headings[1:]
    headings = [h for h in headings if h.get_text(strip=True)]
    if not headings:
        return html, []
    top = min(int(h.name[1]) for h in headings)
    taken = {node["id"] for node in soup.find_all(id=True)}
    entries = []
    for heading in headings:
        depth = int(heading.name[1]) - top + 1
        if depth > 2:
            continue
        label = copy.copy(heading)
        for marker in label.find_all("sup") + label.find_all("a", attrs={"epub:type": re.compile("noteref")}):
            marker.decompose()
        text = " ".join(label.get_text(" ", strip=True).split()) or " ".join(heading.get_text(" ", strip=True).split())
        if not heading.get("id"):
            base = "sec-" + (SLUG.sub("-", text.lower()).strip("-")[:40] or "x")
            candidate, n = base, 2
            while candidate in taken:
                candidate, n = f"{base}-{n}", n + 1
            heading["id"] = candidate
            taken.add(candidate)
        entries.append((depth, heading["id"], text))
    return str(soup), entries


def _file(href: str) -> str:
    return posixpath.basename(href.split("#", 1)[0])


def _uid(href: str) -> str:
    return "toc-" + re.sub(r"[^\w-]", "-", href)


def _children(prefix: str, headings) -> list:
    groups = []
    for depth, hid, text in headings:
        href = f"{prefix}#{hid}"
        if depth == 1 or not groups:
            groups.append((text, href, []))
        else:
            groups[-1][2].append(eb.Link(href, text, _uid(href)))
    return [
        (eb.Section(text, href=href), kids) if kids else eb.Link(href, text, _uid(href))
        for text, href, kids in groups
    ]


def _into(href: str, base: str, file_href: str) -> bool:
    path = unquote((href or "").split("#", 1)[0])
    return bool(path) and posixpath.normpath(posixpath.join(base, path)) == posixpath.normpath(file_href)


def _only_into(items, base: str, file_href: str) -> bool:
    for item in items:
        node, kids = item if isinstance(item, tuple) else (item, [])
        if getattr(node, "href", "") and not _into(node.href, base, file_href):
            return False
        if not _only_into(kids, base, file_href):
            return False
    return True


def rebuild_toc(entries, file_href: str, headings, base: str = "") -> list:
    """`book.toc` with the chapter's own entry holding the rewritten
    headings. An entry counts as the chapter's only if everything under it
    points into the chapter file, so a part entry that links its first
    chapter keeps its other chapters; later entries into the file go."""
    done = False

    def walk(items):
        nonlocal done
        out = []
        for item in items:
            node, kids = item if isinstance(item, tuple) else (item, None)
            if _into(getattr(node, "href", ""), base, file_href) and _only_into(kids or [], base, file_href):
                if done:
                    continue
                done = True
                prefix = node.href.split("#", 1)[0]
                children = _children(prefix, headings)
                out.append((eb.Section(node.title, href=node.href), children) if children else node)
            elif kids is not None:
                out.append((node, walk(kids)))
            else:
                out.append(item)
        return out

    return walk(entries)


def _resolves(href: str, nav_dir: str, file_href: str) -> bool:
    return _into(href, nav_dir, file_href)


def rebuild_nav(nav: str, nav_name: str, rewritten: dict[str, list]) -> str:
    """The EPUB 3 nav document with each rewritten chapter's entry holding
    its new headings, and page-list entries into rewritten chapters dropped:
    their print page positions no longer exist."""
    soup = BeautifulSoup(nav, "xml")
    nav_dir = posixpath.dirname(nav_name)
    toc = soup.find("nav", attrs={"epub:type": re.compile(r"\btoc\b")})
    for file_href, headings in rewritten.items():
        if toc is None:
            break
        link = next(
            (
                a for a in toc.find_all("a", href=True)
                if _resolves(a["href"], nav_dir, file_href)
                and a.parent.name == "li"
                and all(_resolves(x["href"], nav_dir, file_href) for x in a.parent.find_all("a", href=True))
            ),
            None,
        )
        if link is None or link.parent.name != "li":
            continue
        item = link.parent
        old = item.find("ol", recursive=False)
        classes = [li.get("class") for li in old.find_all("li", recursive=False)] if old else []
        if old is not None:
            old.decompose()
        if not headings:
            continue
        prefix = link["href"].split("#", 1)[0]
        ol = soup.new_tag("ol")
        parent = None
        for depth, hid, text in headings:
            li = soup.new_tag("li")
            if classes and classes[0]:
                li["class"] = classes[0]
            a = soup.new_tag("a", href=f"{prefix}#{hid}")
            a.string = text
            li.append(a)
            if depth == 1 or parent is None:
                ol.append(li)
                parent = li
            else:
                sub = parent.find("ol", recursive=False)
                if sub is None:
                    sub = soup.new_tag("ol")
                    parent.append(sub)
                sub.append(li)
        item.append(ol)
    pages = soup.find("nav", attrs={"epub:type": re.compile(r"\bpage-list\b")})
    if pages is not None:
        for a in pages.find_all("a", href=True):
            if any(_resolves(a["href"], nav_dir, f) for f in rewritten):
                a.parent.decompose()
        if not pages.find("li"):
            pages.decompose()
    return str(soup)


def apply(book, rewritten: dict[str, list]) -> None:
    """Point the book's navigation (NCX and nav document) at the rewritten
    chapters' headings."""
    if not rewritten:
        return
    ncx = next((i for i in book.get_items() if i.get_type() == ITEM_NAVIGATION), None)
    base = posixpath.dirname(ncx.get_name()) if ncx is not None else ""
    for file_href, headings in rewritten.items():
        book.toc = rebuild_toc(book.toc, file_href, headings, base)
    for item in book.get_items():
        if isinstance(item, eb.EpubNav) and item.content:
            item.content = rebuild_nav(
                item.content.decode("utf-8"), item.get_name(), rewritten
            ).encode("utf-8")
