import pytest
from ebooklib import epub as eb

LONG_PARAGRAPH = "The quick brown fox jumps over the lazy dog again and again. " * 40


def make_book(tmp_path, name="sample.epub"):
    book = eb.EpubBook()
    book.set_identifier("test-id")
    book.set_title("Sample Book")
    book.set_language("en")

    cover = eb.EpubHtml(title="Cover", file_name="cover.xhtml", uid="cover")
    cover.set_content(b"<html><body><p>Cover page</p></body></html>")

    ch1 = eb.EpubHtml(title="One", file_name="ch1.xhtml", uid="ch1")
    ch1.set_content(
        f"<html><body><h1>Chapter One</h1><p>{LONG_PARAGRAPH}</p>"
        f"<pre><code>print('hello')</code></pre></body></html>".encode()
    )

    ch2 = eb.EpubHtml(title="Two", file_name="ch2.xhtml", uid="ch2")
    ch2.set_content(
        f"<html><body><h1>Chapter Two</h1><p>{LONG_PARAGRAPH}</p></body></html>".encode()
    )

    for item in (cover, ch1, ch2):
        book.add_item(item)
    book.toc = (ch1, ch2)
    book.spine = [cover, ch1, ch2]
    book.add_item(eb.EpubNcx())
    book.add_item(eb.EpubNav())

    path = tmp_path / name
    eb.write_epub(str(path), book)
    return path


@pytest.fixture
def sample_epub(tmp_path):
    return make_book(tmp_path)
