"""Book-level check that reassembly kept the source book's structure intact."""
import posixpath
import re
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import unquote, urlsplit

from bs4 import BeautifulSoup
from lxml import etree

XHTML = {"application/xhtml+xml", "text/html"}
CSS_CLASS = re.compile(r"\.([A-Za-z_][\w-]*)")
MARKDOWN = re.compile(r"(?m)^#{1,6}\s|\*\*\S[^*]*\*\*|```|\]\([^)\s]+\)|^\|\s*-{3}")
CONTENT = ("img", "table", "pre", "math", "svg", "figure")
PROTECTED = {"img", "math", "svg", "figure"}


@dataclass
class Finding:
    level: str  # problem | warning
    kind: str
    where: str
    detail: str


class Package:
    def __init__(self, path: str | Path):
        self.zip = zipfile.ZipFile(path)
        container = self.zip.read("META-INF/container.xml").decode("utf-8", "replace")
        self.opf = re.search(r'full-path="([^"]+)"', container).group(1)
        self.base = posixpath.dirname(self.opf)
        opf = BeautifulSoup(self.zip.read(self.opf), "xml")
        self.items = {
            item["id"]: (self._norm(self.base, item["href"]), item.get("media-type", ""), item.get("properties", ""))
            for item in opf.find_all("item") if item.get("id") and item.get("href")
        }
        self.spine = [self.items[ref["idref"]][0] for ref in opf.find_all("itemref") if ref.get("idref") in self.items]
        self.hrefs = {href for href, _, _ in self.items.values()}
        self.docs = {href: self._soup(href) for href, media, _ in self.items.values() if media in XHTML}
        self.ids = {href: {node["id"] for node in soup.find_all(id=True)} for href, soup in self.docs.items()}
        ncx = next((href for href, media, _ in self.items.values() if media == "application/x-dtbncx+xml"), None)
        self.ncx = BeautifulSoup(self.read(ncx), "xml") if ncx else None
        self.ncx_href = ncx
        nav = next((href for href, _, props in self.items.values() if "nav" in props.split()), None)
        self.nav_href = nav
        css = [self.read(href).decode("utf-8", "replace") for href, media, _ in self.items.values() if media == "text/css"]
        self.css_classes = set(CSS_CLASS.findall("\n".join(css)))

    @staticmethod
    def _norm(base: str, href: str) -> str:
        return posixpath.normpath(posixpath.join(base, unquote(href))) if base else posixpath.normpath(unquote(href))

    def read(self, href: str) -> bytes:
        return self.zip.read(href)

    def _soup(self, href: str) -> BeautifulSoup:
        return BeautifulSoup(self.read(href), "html.parser")

    def resolve(self, doc: str, href: str) -> tuple[str, str] | None:
        """(target file, fragment) for an internal reference, None for external ones."""
        parts = urlsplit(href)
        if parts.scheme or parts.netloc or href.startswith(("mailto:", "data:")):
            return None
        target = self._norm(posixpath.dirname(doc), parts.path) if parts.path else doc
        return target, unquote(parts.fragment)

    def resolves(self, doc: str, href: str) -> bool:
        target, fragment = self.resolve(doc, href)
        if target not in self.hrefs:
            return False
        return not fragment or fragment in self.ids.get(target, set())


def _rel(package: Package, href: str) -> str:
    return posixpath.relpath(href, package.base) if package.base else href


def _links(package: Package, doc: str) -> list[str]:
    soup = package.docs[doc]
    refs = [a["href"] for a in soup.find_all(["a", "area"], href=True)]
    refs += [img["src"] for img in soup.find_all("img", src=True)]
    refs += [link["href"] for link in soup.find_all("link", href=True)]
    return [r for r in refs if package.resolve(doc, r) is not None]


def _nav_refs(package: Package) -> list[tuple[str, str, str, str]]:
    """(container, document the reference sits in, href, label) for every NCX and nav document entry."""
    refs = []
    if package.ncx is not None:
        for point in package.ncx.find_all(["navPoint", "pageTarget"]):
            content = point.find("content", recursive=False)
            label = point.find("text")
            if content is not None and content.get("src"):
                refs.append(("NCX", package.ncx_href, content["src"], label.get_text(strip=True) if label else ""))
    if package.nav_href:
        for a in package.docs[package.nav_href].find_all("a", href=True):
            refs.append(("nav", package.nav_href, a["href"], a.get_text(" ", strip=True)))
    return refs


def _wrappers(soup: BeautifulSoup) -> list[str]:
    """tag.class of each element that alone holds the whole body, outermost first."""
    chain, node = [], soup.body
    while node is not None:
        children = [c for c in node.children if getattr(c, "name", None)]
        texts = [c for c in node.children if not getattr(c, "name", None) and str(c).strip()]
        if len(children) != 1 or texts:
            break
        node = children[0]
        chain.append(".".join([node.name, *node.get("class", [])]))
    return chain


def _prose(soup: BeautifulSoup) -> str:
    body = soup.body or soup
    clone = BeautifulSoup(str(body), "html.parser")
    for node in clone.find_all(["pre", "code", "script", "style"]):
        node.decompose()
    return clone.get_text("\n")


def _classes(soup: BeautifulSoup) -> set[str]:
    return {c for node in soup.find_all(class_=True) for c in node.get("class", [])}


def _stylesheets(package: Package, doc: str) -> list[str]:
    head = package.docs[doc].head
    links = head.find_all("link", href=True) if head else []
    return sorted(package.resolve(doc, link["href"])[0] for link in links if "stylesheet" in " ".join(link.get("rel", [])))


def _xml_error(data: bytes) -> str:
    try:
        etree.fromstring(data)
    except etree.XMLSyntaxError as error:
        return str(error)[:160]
    return ""


def _level_jumps(soup: BeautifulSoup) -> int:
    levels = [int(h.name[1]) for h in soup.find_all(re.compile(r"^h[1-6]$"))]
    return sum(1 for a, b in zip(levels, levels[1:]) if b > a + 1)


def verify(source: str | Path, output: str | Path, rewritten: set[str] | None = None) -> list[Finding]:
    """Compare the output epub with its source. `rewritten` holds the hrefs (relative
    to the package) of rewritten documents; any other document is expected unchanged."""
    src, out = Package(source), Package(output)
    findings: list[Finding] = []

    def add(level, kind, where, detail):
        findings.append(Finding(level, kind, where, detail))

    src_spine = [_rel(src, h) for h in src.spine]
    out_spine = [_rel(out, h) for h in out.spine]
    if src_spine != out_spine:
        lost = [h for h in src_spine if h not in out_spine]
        added = [h for h in out_spine if h not in src_spine]
        add("problem", "spine changed", "package",
            f"lost {lost[:5]}, added {added[:5]}" if lost or added else "same documents, different order")
    src_files = {_rel(src, h) for h in src.hrefs}
    out_files = {_rel(out, h) for h in out.hrefs}
    for missing in sorted(src_files - out_files):
        add("problem", "resource lost", missing, "in the source manifest, missing from the output")

    by_rel = {_rel(out, h): h for h in out.docs}
    src_by_rel = {_rel(src, h): h for h in src.docs}
    changed = set(rewritten) if rewritten is not None else set()
    for rel, out_doc in sorted(by_rel.items()):
        src_doc = src_by_rel.get(rel)
        error = _xml_error(out.read(out_doc))
        if error and not (src_doc and _xml_error(src.read(src_doc))):
            add("problem", "not well-formed XHTML", rel, error)
        if src_doc is None:
            continue
        s, o = src.docs[src_doc], out.docs[out_doc]
        lost_sheets = sorted({_rel(src, h) for h in _stylesheets(src, src_doc)} - {_rel(out, h) for h in _stylesheets(out, out_doc)})
        if lost_sheets:
            add("problem", "stylesheet link lost", rel, ", ".join(lost_sheets))
        if (s.body and o.body) and s.body.attrs != o.body.attrs:
            add("warning", "body attributes changed", rel, f"{s.body.attrs} -> {o.body.attrs}")
        is_rewritten = rel in changed if rewritten is not None else _prose(s) != _prose(o)
        if not is_rewritten:
            if out_doc != out.nav_href and _prose(s) != _prose(o):
                add("warning", "untouched document changed", rel, "text differs from the source")
            continue
        lost_wrappers = [w for w in _wrappers(s) if w not in _wrappers(o) and set(w.split(".")[1:]) & out.css_classes]
        if lost_wrappers:
            add("problem", "styled wrapper lost", rel, ", ".join(lost_wrappers))
        wrapper_classes = {c for w in lost_wrappers for c in w.split(".")[1:]}
        styled = sorted((_classes(s) - _classes(o)) & out.css_classes - wrapper_classes)
        if styled:
            add("warning", "styled classes lost", rel, ", ".join(styled[:12]) + (" …" if len(styled) > 12 else ""))
        for tag in CONTENT:
            before, after = len(s.find_all(tag)), len(o.find_all(tag))
            if after < before:
                add("problem" if tag in PROTECTED else "warning", f"fewer <{tag}>", rel, f"{before} -> {after}")
        text = _prose(o)
        if "⟦" in text:
            add("problem", "token left in text", rel, re.search(r"⟦[^⟧\n]{0,40}", text).group())
        stray = len(MARKDOWN.findall(text)) - len(MARKDOWN.findall(_prose(s)))
        if stray > 0:
            add("warning", "markdown left in text", rel, f"{stray} marker(s), e.g. {MARKDOWN.search(text).group()!r}")
        if _level_jumps(o) > _level_jumps(s):
            add("warning", "heading levels skip", rel, f"{_level_jumps(s)} -> {_level_jumps(o)} jumps")
        ids = [node["id"] for node in o.find_all(id=True)]
        dupes = sorted({i for i in ids if ids.count(i) > 1})
        if dupes:
            add("problem", "duplicate ids", rel, ", ".join(dupes[:8]))

    # a link the source already shipped broken is the publisher's; one that
    # resolved there, or is new, must resolve here
    src_links = {(_rel(src, d), h): src.resolves(d, h) for d in src.docs for h in _links(src, d)}
    for doc in sorted(out.docs):
        rel = _rel(out, doc)
        broken = [h for h in _links(out, doc) if not out.resolves(doc, h) and src_links.get((rel, h)) is not False]
        if broken:
            add("problem", "links broken", rel, f"{len(broken)}: {', '.join(broken[:5])}")

    def target(package, doc, href):
        path, fragment = package.resolve(doc, href)
        return _rel(package, path), fragment

    rewritten_rel = changed if rewritten is not None else {r for r in by_rel if r in src_by_rel and _prose(src.docs[src_by_rel[r]]) != _prose(out.docs[by_rel[r]])}
    primary = "nav" if out.nav_href else "NCX"
    for container in ("NCX", "nav"):
        src_refs = [(target(src, d, h), label) for c, d, h, label in _nav_refs(src) if c == container and src.resolves(d, h)]
        out_refs = [(target(out, d, h), label, h) for c, d, h, label in _nav_refs(out) if c == container]
        home = out.nav_href if container == "nav" else out.ncx_href
        unresolved = [(label, h) for _, label, h in out_refs if not out.resolves(home, h)]
        for label, href in unresolved[:20]:
            add("problem", f"{container} entry unresolved", label or href, href)
        kept = {(t, label) for t, label, _ in out_refs}
        lost = [label or f"{t[0]}#{t[1]}" for t, label in src_refs if t[0] not in rewritten_rel and (t, label) not in kept]
        if lost:
            level = "problem" if container == primary else "warning"
            add(level, f"{container} entries lost", "navigation",
                f"{len(lost)} of {len(src_refs)} (outside rewritten chapters): " + "; ".join(lost[:6]))
    return findings


def summary(findings: list[Finding]) -> str:
    problems = sum(f.level == "problem" for f in findings)
    warnings = len(findings) - problems
    return f"integrity: {problems} problem{'s' * (problems != 1)}, {warnings} warning{'s' * (warnings != 1)}"


def to_json(findings: list[Finding]) -> list[dict]:
    return [asdict(f) for f in findings]
