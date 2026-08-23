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
