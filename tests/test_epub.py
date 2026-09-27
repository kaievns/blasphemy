from ebooklib import epub as eb

from blasphemy import epub
from conftest import png_bytes


def _nav_book(tmp_path):
    book = eb.EpubBook()
    book.set_identifier("nav-id")
    book.set_title("Nav Book")
    book.set_language("en")
    nav = eb.EpubNav()
    nav.set_content(
        b'<html xmlns:epub="http://www.idpf.org/2007/ops"><head></head><body>'
        b'<nav epub:type="toc"><h1>ORIGINAL-NAV</h1>'
        b'<ol><li><a href="ch1.xhtml">One</a></li></ol></nav></body></html>'
    )
    ch = eb.EpubHtml(title="One", file_name="ch1.xhtml", uid="ch1")
    ch.set_content(b"<html><body><h1>One</h1><p>text</p></body></html>")
    book.add_item(nav)
    book.add_item(ch)
    book.toc = (ch,)
    book.spine = [nav, ch]
    book.add_item(eb.EpubNcx())
    path = tmp_path / "nav.epub"
    epub.save(book, path)
    return path


def test_chapters_in_spine_order(sample_epub):
    chapters = epub.chapters(epub.load(sample_epub))
    assert [c.item_id for c in chapters] == ["cover", "ch1", "ch2"]
    assert [c.index for c in chapters] == [0, 1, 2]


def test_chapter_metadata(sample_epub):
    chapters = epub.chapters(epub.load(sample_epub))
    cover, ch1, _ = chapters
    assert cover.words < 10
    assert ch1.words > 300
    assert ch1.title == "Chapter One"
    assert "print('hello')" in ch1.html


def test_replace_content_preserves_head_and_body_attrs(sample_epub, tmp_path):
    book = epub.load(sample_epub)
    epub.replace_content(book, "ch1", "<p>new</p>")
    out = tmp_path / "out.epub"
    epub.save(book, out)
    ch1 = next(c for c in epub.chapters(epub.load(out)) if c.item_id == "ch1")
    assert 'href="style.css"' in ch1.html
    assert 'class="chapter"' in ch1.html


def test_retitle(sample_epub):
    book = epub.load(sample_epub)
    epub.retitle(book, " (Optimised)")
    titles = book.metadata[epub.DC]["title"]
    assert len(titles) == 1
    assert titles[0][0] == "Sample Book (Optimised)"


def test_cover_image_found(sample_epub):
    book = epub.load(sample_epub)
    item = epub.cover_image(book)
    assert item is not None
    assert item.get_content()[:8] == b"\x89PNG\r\n\x1a\n"


def test_cover_image_found_by_item_id():
    book = eb.EpubBook()
    image = eb.EpubImage(
        uid="cover-image", file_name="front.png",
        media_type="image/png", content=png_bytes(),
    )
    book.add_item(image)
    assert epub.cover_image(book) is image


def test_nav_flagged_and_content_preserved(tmp_path):
    path = _nav_book(tmp_path)
    book = epub.load(path)
    chapters = {c.href: c for c in epub.chapters(book)}
    assert chapters["nav.xhtml"].is_nav
    assert not chapters["ch1.xhtml"].is_nav
    assert "ORIGINAL-NAV" in chapters["nav.xhtml"].html

    out = tmp_path / "roundtrip.epub"
    epub.save(book, out)
    again = {c.href: c for c in epub.chapters(epub.load(out))}
    assert "ORIGINAL-NAV" in again["nav.xhtml"].html


def test_replace_content_roundtrip(sample_epub, tmp_path):
    book = epub.load(sample_epub)
    epub.replace_content(book, "ch1", "<h1>Rewritten</h1><p>short and sharp</p>")
    out = tmp_path / "out.epub"
    epub.save(book, out)

    chapters = epub.chapters(epub.load(out))
    ch1 = next(c for c in chapters if c.item_id == "ch1")
    assert "short and sharp" in ch1.html
    assert "quick brown fox" not in ch1.html
    ch2 = next(c for c in chapters if c.item_id == "ch2")
    assert "quick brown fox" in ch2.html



def _doc(tmp_path, body, name):
    book = eb.EpubBook()
    book.set_identifier("ref-id")
    book.set_title("Ref Book")
    book.set_language("en")
    ch = eb.EpubHtml(title="x", file_name=f"{name}.xhtml", uid=name)
    ch.set_content(body.encode())
    book.add_item(ch)
    book.toc = (ch,)
    book.spine = [ch]
    book.add_item(eb.EpubNcx())
    book.add_item(eb.EpubNav())
    path = tmp_path / f"{name}.epub"
    epub.save(book, path)
    return epub.chapters(epub.load(path))[0]


def test_reference_documents_detected_by_title_type_or_class(tmp_path):
    by_title = _doc(tmp_path, "<html><body><h1>Index</h1><p>a, 1</p></body></html>", "a")
    by_type = _doc(
        tmp_path,
        '<html><body><section epub:type="bibliography"><h1>Works</h1></section></body></html>',
        "b",
    )
    by_class = _doc(
        tmp_path, '<html><body><div class="index"><h1>Terms</h1></div></body></html>', "c"
    )
    assert by_title.is_reference and by_type.is_reference and by_class.is_reference
    assert all(c.passthrough for c in (by_title, by_type, by_class))


def test_ordinary_chapter_and_appendix_are_not_reference(tmp_path):
    chapter = _doc(
        tmp_path,
        '<html><body epub:type="backmatter"><h1>Appendix A</h1><p>text</p></body></html>',
        "d",
    )
    intro = _doc(
        tmp_path,
        "<html><body><h1>Introduction</h1><ul><li>a</li><li>b</li></ul></body></html>",
        "e",
    )
    assert not chapter.is_reference and not intro.is_reference


def _page(tmp_path, name, body):
    return _doc(tmp_path, f"<html><body>{body}</body></html>", name)


def test_front_and_back_matter_detected_by_type_class_or_title(tmp_path):
    # No Starch marks epub:type, DocBook uses classes, Pandoc has only titles
    cases = {
        "ns_foreword": '<section epub:type="frontmatter"><h1>Foreword</h1><p>x</p></section>',
        "ns_copy": '<section epub:type="frontmatter copyright-page"><p>x</p></section>',
        "db_preface": '<div class="preface"><h1>Praise for the book</h1><p>x</p></div>',
        "db_colophon": '<div class="colophon"><p>x</p></div>',
        "db_appendix": '<div class="appendix"><h1>Appendix A. Notes</h1><p>x</p></div>',
        "pd_part": "<h1>Part II - Principles</h1><p>x</p>",
        "pd_appendix": "<h1>Appendix D - Example Postmortem</h1><p>x</p>",
        "rights": "<p>Copyright 2021. All rights reserved. ISBN 978</p>",
    }
    for name, body in cases.items():
        chapter = _page(tmp_path, name, body)
        assert chapter.is_matter and chapter.passthrough, name


def test_introductions_and_chapters_are_not_matter(tmp_path):
    cases = {
        "ns_intro": '<section epub:type="frontmatter introduction"><h1>Introduction</h1><p>x</p></section>',
        "intro": '<div class="preface"><h1>Introduction</h1><p>x</p></div>',
        "chapter_intro": "<h1>Chapter 1 - Introduction</h1><p>x</p>",
        "participation": "<h1>Participation and Its Limits</h1><p>x</p>",
        "parting": "<h1>Parting Words</h1><p>x</p>",
        "chapter": '<section epub:type="bodymatter chapter"><h1>1 Foundations</h1><p>x</p></section>',
    }
    for name, body in cases.items():
        assert not _page(tmp_path, name, body).is_matter, name
