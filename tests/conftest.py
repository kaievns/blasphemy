import io

import pytest
from ebooklib import epub as eb
from PIL import Image

from blasphemy import epub as bp

LONG_PARAGRAPH = "The quick brown fox jumps over the lazy dog again and again. " * 40


def png_bytes(color=(20, 80, 160), size=(200, 300)):
    buffer = io.BytesIO()
    Image.new("RGB", size, color).save(buffer, format="PNG")
    return buffer.getvalue()


def make_book(tmp_path, name="sample.epub"):
    book = eb.EpubBook()
    book.set_identifier("test-id")
    book.set_title("Sample Book")
    book.set_language("en")
    book.set_cover("cover-img.png", png_bytes(), create_page=False)

    css = eb.EpubItem(
        uid="css", file_name="style.css", media_type="text/css",
        content=b"h1 { color: navy; }",
    )
    book.add_item(css)

    cover = eb.EpubHtml(title="Cover", file_name="cover.xhtml", uid="cover")
    cover.set_content(b"<html><body><p>Cover page</p></body></html>")

    ch1 = eb.EpubHtml(title="One", file_name="ch1.xhtml", uid="ch1")
    ch1.set_content(
        '<html><head><link rel="stylesheet" href="style.css"/></head>'
        f'<body class="chapter" epub:type="bodymatter"><h1>Chapter One</h1>'
        f"<p>{LONG_PARAGRAPH}</p>"
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
    bp.save(book, path)
    return path


@pytest.fixture
def sample_epub(tmp_path):
    return make_book(tmp_path)


@pytest.fixture
def math_epub(tmp_path):
    book = eb.EpubBook()
    book.set_identifier("math-id")
    book.set_title("Math Book")
    book.set_language("en")
    ch = eb.EpubHtml(title="Math", file_name="math.xhtml", uid="math")
    ch.set_content(
        f"<html><body><h1>Math</h1><p>{LONG_PARAGRAPH}</p>"
        "<p>Energy: <math><mi>E</mi><mo>=</mo><msup><mi>c</mi><mn>2</mn></msup>"
        "</math></p></body></html>".encode()
    )
    book.add_item(ch)
    book.toc = (ch,)
    book.spine = [ch]
    book.add_item(eb.EpubNcx())
    book.add_item(eb.EpubNav())
    path = tmp_path / "math.epub"
    eb.write_epub(str(path), book)
    return path
