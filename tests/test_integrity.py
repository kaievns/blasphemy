import zipfile

from blasphemy import integrity

CSS = "div.chapter h1 { font-size: 2em } p.first { text-indent: 0 } .sidebar { border: 1px }"


def doc(body, css=True):
    link = '<link rel="stylesheet" type="text/css" href="style.css"/>' if css else ""
    return f'<?xml version="1.0" encoding="utf-8"?><html xmlns="http://www.w3.org/1999/xhtml"><head><title>t</title>{link}</head><body>{body}</body></html>'


CH1 = '<div class="chapter"><h1 id="c1">One</h1><p class="first">Text <a href="ch2.xhtml#s2">see</a>.</p><img src="fig.png" alt="f"/><table><tr><td>x</td></tr></table></div>'
CH2 = '<h1 id="c2">Two</h1><h2 id="s2">Sub</h2><p>Body.</p>'


def book(path, docs=None, spine=("ch1.xhtml", "ch2.xhtml"), extra_items="", ncx_points=None):
    docs = {"ch1.xhtml": doc(CH1), "ch2.xhtml": doc(CH2), **(docs or {})}
    points = ncx_points if ncx_points is not None else [("One", "ch1.xhtml#c1"), ("Two", "ch2.xhtml"), ("Sub", "ch2.xhtml#s2")]
    manifest = "".join(f'<item id="d{i}" href="{name}" media-type="application/xhtml+xml"/>' for i, name in enumerate(docs))
    itemrefs = "".join(f'<itemref idref="d{list(docs).index(name)}"/>' for name in spine)
    nav = "".join(f'<navPoint id="n{i}"><navLabel><text>{label}</text></navLabel><content src="{src}"/></navPoint>' for i, (label, src) in enumerate(points))
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        z.writestr("META-INF/container.xml", '<container><rootfiles><rootfile full-path="OPS/p.opf" media-type="application/oebps-package+xml"/></rootfiles></container>')
        z.writestr("OPS/p.opf", f'<package xmlns="http://www.idpf.org/2007/opf" version="2.0"><manifest>{manifest}'
                   '<item id="css" href="style.css" media-type="text/css"/><item id="img" href="fig.png" media-type="image/png"/>'
                   f'<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>{extra_items}</manifest><spine toc="ncx">{itemrefs}</spine></package>')
        z.writestr("OPS/style.css", CSS)
        z.writestr("OPS/fig.png", b"png")
        z.writestr("OPS/toc.ncx", f'<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/"><navMap>{nav}</navMap></ncx>')
        for name, content in docs.items():
            z.writestr(f"OPS/{name}", content)
    return path


def kinds(findings):
    return {(f.level, f.kind) for f in findings}


def test_identical_books_have_no_findings(tmp_path):
    assert integrity.verify(book(tmp_path / "a.epub"), book(tmp_path / "b.epub")) == []


def test_rewritten_chapter_losing_its_structure_is_reported(tmp_path):
    rewritten = doc('<h1 id="c1">One</h1><p>Text ⟦ANCHOR:x⟧ <a href="ch2.xhtml#gone">see</a> **bold**.</p>')
    found = integrity.verify(book(tmp_path / "a.epub"), book(tmp_path / "b.epub", {"ch1.xhtml": rewritten}), rewritten={"ch1.xhtml"})
    assert {
        ("problem", "styled wrapper lost"), ("problem", "fewer <img>"), ("warning", "fewer <table>"),
        ("problem", "token left in text"), ("warning", "markdown left in text"), ("problem", "links broken"),
        ("warning", "styled classes lost"),
    } <= kinds(found)


def test_package_level_damage_is_reported(tmp_path):
    source = book(tmp_path / "a.epub")
    reordered = book(tmp_path / "b.epub", spine=("ch2.xhtml", "ch1.xhtml"))
    assert ("problem", "spine changed") in kinds(integrity.verify(source, reordered))
    unstyled = book(tmp_path / "c.epub", {"ch2.xhtml": doc(CH2, css=False)})
    assert ("problem", "stylesheet link lost") in kinds(integrity.verify(source, unstyled))
    broken = book(tmp_path / "d.epub", {"ch2.xhtml": "<html><body><p>unclosed</body></html>"})
    assert ("problem", "not well-formed XHTML") in kinds(integrity.verify(source, broken))


def test_untouched_documents_and_navigation_are_guarded(tmp_path):
    source = book(tmp_path / "a.epub")
    edited = book(tmp_path / "b.epub", {"ch2.xhtml": doc(CH2.replace("Body.", "Changed."))},
                  ncx_points=[("One", "ch1.xhtml#c1"), ("Two", "ch2.xhtml")])
    found = integrity.verify(source, edited, rewritten=set())
    assert ("warning", "untouched document changed") in kinds(found)
    assert ("problem", "NCX entries lost") in kinds(found)  # the NCX is this book's only navigation


def test_navigation_of_rewritten_chapters_may_change(tmp_path):
    relabelled = book(tmp_path / "b.epub", ncx_points=[("One", "ch1.xhtml#c1"), ("Two", "ch2.xhtml"), ("A New Sub", "ch2.xhtml#s2")])
    assert integrity.verify(book(tmp_path / "a.epub"), relabelled, rewritten={"ch2.xhtml"}) == []


def test_links_the_source_already_broke_are_not_blamed_on_the_rebuild(tmp_path):
    dangling = doc(CH2 + '<p><a href="nowhere.xhtml">x</a></p>')
    source = book(tmp_path / "a.epub", {"ch2.xhtml": dangling})
    assert integrity.verify(source, book(tmp_path / "b.epub", {"ch2.xhtml": dangling})) == []


def test_summary_counts_levels():
    found = [integrity.Finding("problem", "k", "w", "d"), integrity.Finding("warning", "k", "w", "d"), integrity.Finding("warning", "k", "w", "d")]
    assert integrity.summary(found) == "integrity: 1 problem, 2 warnings"


def test_the_nav_document_may_change_for_rewritten_chapters(tmp_path):
    nav = doc('<nav epub:type="toc"><ol><li><a href="ch1.xhtml#c1">One</a></li></ol></nav>').replace(
        '<html xmlns="http://www.w3.org/1999/xhtml">', '<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">')
    item = '<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>'
    source = book(tmp_path / "a.epub", {"nav.xhtml": nav}, extra_items=item)
    renamed = book(tmp_path / "b.epub", {"nav.xhtml": nav.replace(">One<", ">One, Rewritten<")}, extra_items=item)
    assert ("warning", "untouched document changed") not in kinds(integrity.verify(source, renamed, rewritten={"ch1.xhtml"}))
