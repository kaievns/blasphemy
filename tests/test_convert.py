from blasphemy import convert

HTML = (
    "<html><body><h1>Title</h1><p>Some <em>styled</em> text.</p>"
    "<pre><code>x = 1</code></pre><ul><li>a</li><li>b</li></ul></body></html>"
)


def test_html_to_markdown():
    md = convert.html_to_markdown(HTML)
    assert "# Title" in md
    assert "*styled*" in md
    assert "x = 1" in md
    assert "* a" in md or "- a" in md


def test_markdown_to_html():
    html = convert.markdown_to_html("# Title\n\nText with `code`.\n\n```\nx = 1\n```\n")
    assert "<h1>Title</h1>" in html
    assert "<code>" in html


def test_text_survives_roundtrip():
    md = convert.html_to_markdown(HTML)
    html = convert.markdown_to_html(md)
    for fragment in ("Title", "styled", "x = 1"):
        assert fragment in html
