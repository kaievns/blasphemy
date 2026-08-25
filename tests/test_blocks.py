from blasphemy import blocks, convert

MATHML = "<p>Energy: <math><mi>E</mi><mo>=</mo><mi>m</mi><msup><mi>c</mi><mn>2</mn></msup></math></p>"
SVG = '<svg viewBox="0 0 10 10"><title>request flow</title><rect/></svg>'


def test_protect_replaces_with_gist_token():
    html, protected = blocks.protect(MATHML)
    assert "<math>" not in html
    assert "⟦MATH-0: E = m c 2⟧" in html
    assert protected["MATH-0"].startswith("<math>")


def test_svg_gist_uses_title():
    html, protected = blocks.protect(f"<p>Flow:</p>{SVG}")
    assert "⟦SVG-0: request flow⟧" in html
    assert "SVG-0" in protected


def test_nested_protected_tags_kept_whole():
    html, protected = blocks.protect("<svg><title>t</title><svg><rect/></svg></svg>")
    assert len(protected) == 1
    assert protected["SVG-0"].count("<svg") == 2


def test_restore_roundtrip():
    html, protected = blocks.protect(MATHML)
    restored, missing = blocks.restore(html, protected)
    assert missing == []
    assert "<msup>" in restored


def test_restore_tolerates_edited_gist():
    _, protected = blocks.protect(MATHML)
    restored, missing = blocks.restore("before ⟦MATH-0⟧ after", protected)
    assert missing == []
    assert "<math>" in restored


def test_restore_reports_missing():
    _, protected = blocks.protect(MATHML)
    restored, missing = blocks.restore("no tokens here", protected)
    assert missing == ["MATH-0"]


def test_restore_deduplicates_repeated_token():
    _, protected = blocks.protect(MATHML)
    restored, missing = blocks.restore("⟦MATH-0⟧ mid ⟦MATH-0⟧", protected)
    assert missing == []
    assert restored.count("<math>") == 1


def test_protect_anchors_inserts_tokens():
    html, found = blocks.protect_anchors(
        '<h2 id="sec1">Title</h2><p id="other">x</p>', {"sec1"}
    )
    assert found == ["sec1"]
    assert "⟦ANCHOR:sec1⟧" in html
    assert "⟦ANCHOR:other⟧" not in html


def test_restore_anchors_in_place():
    html, missing = blocks.restore_anchors("before ⟦ANCHOR:sec1⟧ after", ["sec1"])
    assert missing == []
    assert 'before <a id="sec1"></a> after' == html


def test_restore_anchors_fallback_to_top():
    html, missing = blocks.restore_anchors("<p>no token</p>", ["sec1"])
    assert missing == ["sec1"]
    assert html.startswith('<a id="sec1"></a>')


def test_restore_anchors_tolerates_markdown_escapes():
    html, missing = blocks.restore_anchors(r"x ⟦ANCHOR:Page\_iv⟧ y", ["Page_iv"])
    assert missing == []
    assert '<a id="Page_iv"></a>' in html


PRE_HTML = '<h1>T</h1><pre><code><b>typed input</b> output <span class="CodeAnnotation">1</span></code></pre><p>x</p>'


def test_pre_restored_with_original_markup():
    originals = blocks.extract_pre(PRE_HTML)
    assert len(originals) == 1
    rewritten = "<h1>T</h1><pre><code>typed input output 1</code></pre><p>short</p>"
    restored, ok = blocks.restore_pre(rewritten, originals)
    assert ok
    assert "<b>typed input</b>" in restored
    assert 'class="CodeAnnotation"' in restored


def test_pre_count_mismatch_leaves_output_alone():
    originals = blocks.extract_pre(PRE_HTML)
    rewritten = "<p>model merged the code away</p>"
    restored, ok = blocks.restore_pre(rewritten, originals)
    assert not ok
    assert restored == rewritten


def test_no_pres_is_ok():
    restored, ok = blocks.restore_pre("<p>hello</p>", [])
    assert ok


def test_token_survives_markdown_roundtrip():
    html, protected = blocks.protect(MATHML)
    md = convert.html_to_markdown(html)
    restored, missing = blocks.restore(convert.markdown_to_html(md), protected)
    assert missing == []
    assert "<msup>" in restored
