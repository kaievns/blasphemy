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


def test_sup_sub_u_survive_roundtrip():
    html = "<p>x<sup>2</sup> and H<sub>2</sub>O and <u>underlined</u>.</p>"
    md = convert.html_to_markdown(html)
    assert "<sup>2</sup>" in md
    back = convert.markdown_to_html(md)
    assert "<sup>2</sup>" in back
    assert "<sub>2</sub>" in back
    assert "<u>underlined</u>" in back


def test_var_placeholder_text_is_not_swallowed_as_a_tag():
    # Rust for Rustaceans ch5: [profile.<profile-name>.package.<crate-name>]
    html = (
        "<p><code>[profile.</code><var>&lt;profile-name&gt;</var>"
        "<code>.package.</code><var>x_y</var></p>"
    )
    back = convert.markdown_to_html(convert.html_to_markdown(html))
    assert "<var>&lt;profile-name&gt;</var>" in back
    assert "<var>x_y</var>" in back
    assert "<profile-name>" not in back


def test_text_survives_roundtrip():
    md = convert.html_to_markdown(HTML)
    html = convert.markdown_to_html(md)
    for fragment in ("Title", "styled", "x = 1"):
        assert fragment in html
