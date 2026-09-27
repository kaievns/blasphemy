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


def roundtrip(html):
    return convert.markdown_to_html(convert.html_to_markdown(html))


def test_code_holding_a_fence_line_stays_one_listing():
    # Rust for Rustaceans ch6: doc-test examples inside a listing
    code = "/// ```\n/// let x = 1;\n/// ```\n```rust\nfn f() {}\n```"
    back = roundtrip(f"<pre><code>{code}</code></pre><p>After prose.</p>")
    assert back.count("<pre>") == 1
    assert "<p>After prose.</p>" in back
    assert "fn f() {}" in back.split("</pre>")[0]


def test_code_inside_list_items_stays_code():
    # How Linux Works: numbered steps with a listing under each
    html = "<ol><li><p>Run this:</p><pre><code>$ ls -l</code></pre></li><li><p>Then that.</p></li></ol>"
    back = roundtrip(html)
    assert "<pre><code>$ ls -l" in back
    assert back.count("<li>") == 2


def test_model_markdown_with_three_space_list_indent():
    md = "1. Run this:\n\n   ```\n   $ ls\n   ```\n\n2. Then that.\n"
    html = convert.markdown_to_html(md)
    assert "<pre><code>$ ls" in html and html.count("<li>") == 2


def test_definition_lists_survive():
    back = roundtrip("<dl><dt>Toil</dt><dd>Manual, repetitive work.</dd></dl>")
    assert "<dt>Toil</dt>" in back and "<dd>Manual, repetitive work.</dd>" in back
    assert ":   " not in back


def test_bare_placeholder_in_model_prose_is_text():
    html = convert.markdown_to_html("See /run/user/<uid> and <profile-name>, plus x<sup>2</sup>.")
    assert "/run/user/&lt;uid&gt;" in html
    assert "&lt;profile-name&gt;" in html
    assert "<sup>2</sup>" in html


def test_output_is_xhtml():
    html = convert.markdown_to_html("a  \nb\n\n---\n\n![alt](x.png)")
    assert "<br />" in html and "<hr />" in html and "/>" in html.split("<img")[1]


def test_placeholders_inside_code_stay_plain_code():
    # How Linux Works: $ cp <var>file1</var> <var>file2</var>
    back = roundtrip("<pre><code>$ cp <var>file1</var> <var>file2</var></code></pre>")
    assert "$ cp file1 file2" in back
    assert "&lt;var&gt;" not in back
    inline = roundtrip("<p>Run <code>ls <var>dir</var></code> now.</p>")
    assert "<code>ls dir</code>" in inline


def test_numbered_definition_terms_stay_terms():
    # Site Reliability Engineering ch7: "1) No automation" etc.
    back = roundtrip("<dl><dt>1) No automation</dt><dd><p>Manual failover.</p></dd>"
                     "<dt>2) Scripts</dt><dd><p>A script at home.</p></dd></dl>")
    assert back.count("<dt>") == 2 and "<ol" not in back
    assert "<dt>1) No automation</dt>" in back


def test_empty_definition_term_does_not_break_conversion():
    assert "Orphan definition." in roundtrip("<dl><dt></dt><dd>Orphan definition.</dd></dl>")


def test_pipe_inside_a_table_cell_stays_in_its_cell():
    # How Linux Works Table 2-1: | `|` | pipe | Command pipes |
    html = "<table><tr><th>Symbol</th><th>Name</th><th>Use</th></tr><tr><td><code>|</code></td><td>pipe</td><td>Command pipes</td></tr></table>"
    back = roundtrip(html)
    assert "<td><code>|</code></td>" in back and "<td>Command pipes</td>" in back


def test_split_emphasis_is_merged_not_starred():
    back = roundtrip("<p>you must <em>co</em><em>mpile</em> code, <strong>a</strong><strong>b</strong></p>")
    assert "<em>compile</em>" in back and "<strong>ab</strong>" in back and "*" not in back


def test_emphasis_touching_punctuation_and_letters_survives():
    back = roundtrip("<p><strong>Prioritize.</strong>Stop and <em>p &lt; 0.05</em>. Then x<em>.y</em>z.</p>")
    assert "<strong>Prioritize.</strong>Stop" in back
    assert "<em>p &lt; 0.05</em>." in back
    assert "*" not in back


def test_prose_opening_with_a_number_is_not_a_list():
    back = roundtrip("<p>1) No automation at all.</p><p>2021. That was the year.</p>")
    assert "<ol" not in back and "1) No automation" in back and "2021. That was" in back


def test_emphasised_definition_term_keeps_its_emphasis():
    back = roundtrip("<dl><dt><em>Toil</em></dt><dd><p>Manual work.</p></dd></dl>")
    assert "<dt><em>Toil</em></dt>" in back


def test_emphasis_wrapped_in_a_span_sees_the_text_outside_it():
    # Statistics Done Wrong: p &lt; 0.05<span class="emphasis"><em>. The ...</em></span>
    back = roundtrip('<p>at p &lt; 0.05<span class="emphasis"><em>. The probability</em></span> of x</p>')
    assert "*" not in back and "<em>. The probability</em>" in back
