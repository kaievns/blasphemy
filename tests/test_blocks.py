import re
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
    restored, unmatched = blocks.restore_pre(rewritten, originals)
    assert unmatched == 0
    assert "<b>typed input</b>" in restored
    assert 'class="CodeAnnotation"' in restored


def test_pre_dropped_by_model_costs_only_that_listing():
    originals = [
        "<pre><code><b>$ ls</b>\nout</code></pre>",
        "<pre><code><b>$ rm</b>\ngone</code></pre>",
        "<pre><code><b>$ cp</b>\ncopied</code></pre>",
    ]
    # the model merged the second listing away; the others are verbatim text
    rewritten = "<pre><code>$ ls\nout</code></pre><p>x</p><pre><code>$ cp\ncopied</code></pre>"
    restored, unmatched = blocks.restore_pre(rewritten, originals)
    assert unmatched == 0
    assert "<b>$ ls</b>" in restored and "<b>$ cp</b>" in restored
    assert "$ rm" not in restored


def test_pre_edited_code_paired_when_text_mostly_overlaps():
    originals = [
        "<pre><code><b>a</b> 1</code></pre>",
        "<pre><code><b>$ ls -l /dev</b>\nbrw-rw---- 1 root disk 8, 1 sda1</code></pre>",
    ]
    # the model trimmed one column of the listing output
    rewritten = (
        "<pre><code>a 1</code></pre>"
        "<pre><code>$ ls -l /dev\nbrw-rw---- 1 root disk sda1</code></pre>"
    )
    restored, unmatched = blocks.restore_pre(rewritten, originals)
    assert unmatched == 0
    assert "<b>$ ls -l /dev</b>" in restored  # the edited one got its original back


def test_pre_unrelated_single_leftover_is_not_paired():
    originals = ["<pre><code><b>$ ls</b></code></pre>"]
    rewritten = "<pre><code>fn main() { println!() }</code></pre>"
    restored, unmatched = blocks.restore_pre(rewritten, originals)
    assert unmatched == 1 and restored == rewritten


def test_pre_without_any_match_stays_fenced_and_is_counted():
    originals = ["<pre><code><b>a</b></code></pre>", "<pre><code><b>b</b></code></pre>"]
    rewritten = "<pre><code>something else entirely</code></pre>"
    restored, unmatched = blocks.restore_pre(rewritten, originals)
    assert unmatched == 1
    assert restored == rewritten


def test_no_pres_is_ok():
    restored, unmatched = blocks.restore_pre("<p>hello</p>", [])
    assert unmatched == 0


OPENER = (
    '<figure class="opener"><img src="art/chapterart.png" alt=""/></figure>'
    '<p class="ChapterIntro">At first glance...</p>'
)


def test_image_figure_is_protected_with_its_wrapper():
    html, protected = blocks.protect(OPENER)
    assert "⟦FIGURE-0: image⟧" in html
    assert "<figure" not in html
    assert protected["FIGURE-0"].startswith('<figure class="opener">')


def test_figure_gist_prefers_caption_then_alt():
    html, _ = blocks.protect(
        '<figure><figcaption>Figure 1-2: The kernel</figcaption>'
        '<img src="a.png"/></figure>'
    )
    assert "⟦FIGURE-0: Figure 1-2: The kernel⟧" in html
    html, _ = blocks.protect('<figure><img src="a.png" alt="a penguin"/></figure>')
    assert "⟦FIGURE-0: a penguin⟧" in html


def test_table_figures_stay_visible_to_the_model():
    source = (
        '<figure><figcaption class="TableTitle">Table 2-1</figcaption>'
        "<table><tr><td>x</td></tr></table></figure>"
    )
    html, protected = blocks.protect(source)
    assert protected == {}
    assert "<table>" in html


def test_figure_survives_round_trip_with_class():
    html, protected = blocks.protect(OPENER)
    md = convert.html_to_markdown(html)
    restored, missing = blocks.restore(convert.markdown_to_html(md), protected)
    assert missing == []
    assert '<figure class="opener">' in restored
    # a block element must not be left wrapped in <p>
    assert "<p><figure" not in restored.replace("\n", "")


def test_dropped_figure_token_is_rewrapped_by_src():
    _, protected = blocks.protect(OPENER)
    output = '<p><img alt="" src="art/chapterart.png"/></p><p>text</p>'
    restored, missing = blocks.restore(output, protected)
    assert missing == []
    assert '<figure class="opener">' in restored
    assert "<p><img" not in restored


def test_figure_missing_entirely_is_reported():
    _, protected = blocks.protect(OPENER)
    restored, missing = blocks.restore("<p>no image at all</p>", protected)
    assert missing == ["FIGURE-0"]


CAPTIONED = (
    '<figure><img src="f01.png" alt="f01"/>'
    '<figcaption><p><a id="figure1-1">Figure 1-1</a>: System organization</p>'
    "</figcaption></figure>"
)


def test_prose_caption_beside_restored_figure_is_dropped():
    _, protected = blocks.protect(CAPTIONED)
    # shape of a rewrite cached before figures were protected
    output = (
        '<p><img alt="f01" src="f01.png"/></p>'
        "<p>Figure 1-1: System organization</p><p>Body text.</p>"
    )
    restored, missing = blocks.restore(output, protected)
    assert missing == []
    assert restored.count("Figure 1-1") == 1
    assert "<figcaption>" in restored
    assert "Body text." in restored


def test_caption_kept_when_no_duplicate_exists():
    _, protected = blocks.protect(CAPTIONED)
    restored, _ = blocks.restore('<p><img alt="f01" src="f01.png"/></p>', protected)
    assert restored.count("Figure 1-1") == 1
    assert "<figcaption>" in restored


def test_anchor_inside_protected_figure_is_not_tokenised_twice():
    # blocks first, anchors second: the id travels inside the figure
    block_html, protected = blocks.protect(CAPTIONED)
    _, anchor_ids = blocks.protect_anchors(block_html, {"figure1-1"})
    assert anchor_ids == []
    restored, _ = blocks.restore(block_html, protected)
    assert restored.count('id="figure1-1"') == 1


def test_strip_tokens_removes_unrestorable_leftovers():
    assert blocks.strip_tokens("a ⟦ANCHOR:x⟧b ⟦FIGURE-9: y⟧c") == "a b c"


def test_classed_wrapper_is_protected_but_prose_sibling_is_not():
    source = (
        '<div class="section"><p><img src="eq.png" class="equation" id="eq7"/></p>'
        "<p>Prose the model must be able to rewrite.</p></div>"
    )
    html, protected = blocks.protect(source)
    assert list(protected) == ["P-0"]  # the image's own <p>, not the section
    assert "Prose the model must be able to rewrite." in html
    restored, missing = blocks.restore(html, protected)
    assert missing == []
    assert 'class="equation"' in restored and 'id="eq7"' in restored


def test_image_only_wrapper_with_class_is_kept():
    source = '<div class="mediaobject"><img src="f.png" style="width: 20em"/></div>'
    html, protected = blocks.protect(source)
    assert list(protected) == ["DIV-0"]
    restored, _ = blocks.restore(html, protected)
    assert 'class="mediaobject"' in restored and "width: 20em" in restored


def test_linked_image_keeps_its_anchor():
    html, protected = blocks.protect('<a href="big.png"><img src="small.png"/></a>')
    assert list(protected) == ["A-0"]
    restored, _ = blocks.restore(html, protected)
    assert '<a href="big.png">' in restored


def test_plain_images_stay_markdown():
    # nothing to preserve beyond src/alt: no token, no failure surface
    for source in (
        '<p>Before <img src="icon.png" alt="icon"/> after.</p>',
        '<div><img src="plain.png" alt="plain"/></div>',
    ):
        html, protected = blocks.protect(source)
        assert protected == {}
        assert "<img" in html


def test_nested_protected_node_inside_figure_not_double_counted():
    html, protected = blocks.protect(
        '<figure class="opener"><img src="a.png"/><svg><rect/></svg></figure>'
    )
    assert list(protected) == ["FIGURE-0"]
    assert "<svg>" in protected["FIGURE-0"]


def test_token_ids_do_not_collide_on_shared_prefix():
    protected = {"MATH-1": "<math>one</math>", "MATH-10": "<math>ten</math>"}
    restored, missing = blocks.restore("⟦MATH-10: ten⟧", protected)
    assert missing == ["MATH-1"]
    assert "<math>ten</math>" in restored


def test_token_survives_markdown_roundtrip():
    html, protected = blocks.protect(MATHML)
    md = convert.html_to_markdown(html)
    restored, missing = blocks.restore(convert.markdown_to_html(md), protected)
    assert missing == []
    assert "<msup>" in restored


# No Starch chapter opener: styled title in <header>, art that floats into
# the title's bottom margin, and a large-type lead paragraph
OPENER_HTML = (
    '<section><header><h1 class="chapter"><span class="ChapterNumber">1</span>'
    '<br/><span class="ChapterTitle">Foundations</span></h1></header>'
    '<figure class="opener"><img alt="" src="art.png"/></figure>'
    '<p class="ChapterIntro">As you dive into Rust, fundamentals matter.</p>'
    "<p>Read it top to bottom.</p></section>"
)


def test_styled_title_protected_with_readable_gist():
    html, protected = blocks.protect(OPENER_HTML)
    assert "<h1" not in html
    assert "⟦TITLE-0: 1 Foundations⟧" in html
    assert protected["TITLE-0"].startswith("<header>")
    # the token keeps its place as the first line of the markdown
    assert convert.html_to_markdown(html).startswith("⟦TITLE-0: 1 Foundations⟧")


def test_plain_title_is_left_to_markdown():
    html, protected = blocks.protect("<h1>Chapter One</h1><p>Text.</p>")
    assert "TITLE" not in " ".join(protected)
    assert "<h1>Chapter One</h1>" in html


def test_title_roundtrip_restores_header_markup_unwrapped():
    html, protected = blocks.protect(OPENER_HTML)
    md = convert.html_to_markdown(html)
    restored, missing = blocks.restore(convert.markdown_to_html(md), protected)
    assert missing == []
    assert '<h1 class="chapter"><span class="ChapterNumber">1</span>' in restored
    assert "<p><header>" not in restored.replace("\n", "")
    assert "<h1>1 Foundations</h1>" not in restored


def test_lead_paragraph_class_carried_to_rewrite():
    rewritten = (
        '<header><h1 class="chapter">1 Foundations</h1></header>'
        '<figure class="opener"><img src="art.png"/></figure>'
        '<p><a id="Page_1"></a></p>'
        "<p>Rewritten opening paragraph.</p><p>Second paragraph.</p>"
    )
    out = blocks.carry_lead_class(rewritten, OPENER_HTML)
    assert '<p class="ChapterIntro">Rewritten opening paragraph.</p>' in out
    assert "<p>Second paragraph.</p>" in out  # only the lead is styled


def test_lead_class_not_applied_when_original_has_none():
    plain = "<h1>T</h1><p>Plain lead.</p>"
    out = blocks.carry_lead_class("<h1>T</h1><p>New lead.</p>", plain)
    assert out == "<h1>T</h1><p>New lead.</p>"


def test_title_does_not_shift_other_token_ids():
    # caches written before titles were protected say FIGURE-0; keep it so
    _, protected = blocks.protect(OPENER_HTML)
    assert list(protected) == ["TITLE-0", "FIGURE-0"]


def test_cached_plain_heading_swapped_for_original_title():
    # a rewrite cached before titles were protected carries `# 1 Foundations`
    _, protected = blocks.protect(OPENER_HTML)
    cached = convert.markdown_to_html(
        "# 1 Foundations\n\nRewritten lead.\n\n⟦FIGURE-0: image⟧"
    )
    restored, missing = blocks.restore(cached, protected)
    assert missing == []
    assert '<h1 class="chapter"><span class="ChapterNumber">1</span>' in restored
    assert "<h1>1 Foundations</h1>" not in restored
    assert restored.count("<h1") == 1


def test_title_without_any_heading_goes_on_top_not_failure():
    _, protected = blocks.protect(OPENER_HTML)
    restored, missing = blocks.restore("<p>No heading at all.</p>", protected)
    assert "TITLE-0" not in missing
    assert restored.startswith("<header>")


CAPTIONED_HTML = (
    "<pre><code>ls</code></pre>"
    '<p class="CodeListingCaption"><a id="listing2-1">Listing 2-1</a>: Listing files</p>'
    '<figure><figcaption class="TableTitle"><p><a id="table2-1">Table 2-1</a>: '
    "Special Characters</p></figcaption>"
    '<table border="1"><tr><td>*</td></tr></table></figure>'
    "<p>Body text mentioning Table 2-1 in passing.</p>"
)


def test_listing_caption_class_restored_by_label():
    rewritten = (
        "<pre><code>ls</code></pre>"
        '<p><a id="listing2-1"></a>Listing 2-1: Listing files</p>'
        "<p>Prose.</p>"
    )
    out = blocks.restore_captions(rewritten, CAPTIONED_HTML)
    assert '<p class="CodeListingCaption"><a id="listing2-1">Listing 2-1</a>: Listing files</p>' in out
    assert "<p>Prose.</p>" in out


def test_table_title_rewrapped_into_figure():
    rewritten = (
        '<p><a id="table2-1"></a>Table 2-1: Special Characters</p>'
        "<table><tr><td>*</td></tr></table>"
        "<p>Body text mentioning Table 2-1 in passing.</p>"
    )
    out = blocks.restore_captions(rewritten, CAPTIONED_HTML)
    assert out.startswith('<figure><figcaption class="TableTitle">')
    assert "</figcaption><table>" in out.replace("\n", "")
    # the prose mention is not a caption: it does not start with the label
    assert "<p>Body text mentioning Table 2-1 in passing.</p>" in out


def test_captions_untouched_when_original_has_none():
    html = "<p>Table 1-1: something</p>"
    assert blocks.restore_captions(html, "<p>Table 1-1: something</p>") == html


def test_image_figure_captions_are_not_duplicated_from_prose():
    original = (
        '<figure><img src="a.png"/><figcaption><p><a id="figure1-1">Figure 1-1</a>: '
        "Overview</p></figcaption></figure>"
    )
    # older cache: the model also wrote the caption as a paragraph
    rewritten = original + "<p>Figure 1-1: Overview of the system</p>"
    assert blocks.restore_captions(rewritten, original) == rewritten


# No Starch callout, verbatim shape from Rust for Rustaceans
NOTE_HTML = (
    '<p>Before.</p><aside epub:type="sidebar"><div class="top hr"><hr/></div>'
    '<section class="note"><h2><span class="NoteHead">Note</span></h2>'
    "<p>Technically, the value of <code>string</code> also includes the length.</p>"
    '<div class="bottom hr"><hr/></div></section></aside><p>After.</p>'
)


def test_notes_are_not_protected_the_model_restructures_them():
    html, protected = blocks.protect(NOTE_HTML)
    assert "NOTE" not in " ".join(protected)
    # the model sees the note as ordinary content it may dissolve or keep
    assert "## Note" in convert.html_to_markdown(html)


def test_kept_note_is_reboxed_in_publisher_shell():
    rewritten = convert.markdown_to_html(
        "Before.\n\n## Note\n\nThe value of `string` also carries its length.\n\nAfter."
    )
    out = blocks.restyle_notes(rewritten, NOTE_HTML)
    assert '<span class="NoteHead">Note</span>' in out
    assert "carries its length" in out  # the model's text, not the original
    assert "also includes the length" not in out
    assert "<h2>Note</h2>" not in out
    assert "<p>Before.</p>" in out and "<p>After.</p>" in out


def test_dissolved_note_is_left_alone():
    rewritten = "<p>Before. Its value also carries the length. After.</p>"
    assert blocks.restyle_notes(rewritten, NOTE_HTML) == rewritten


def test_docbook_admonition_shell_is_recognised():
    original = '<div class="warning"><h3 class="title">Warning</h3><p>Careful.</p></div>'
    rewritten = "<h3>Warning</h3><p>Mind the gap.</p>"
    out = blocks.restyle_notes(rewritten, original)
    assert out.startswith('<div class="warning">')
    assert "Mind the gap." in out and "Careful." not in out


BOX_HTML = (
    '<aside epub:type="sidebar"><div class="top hr"><hr/></div><section class="box">'
    "<h2>What Is mkfs?</h2><p>Frontend.</p><p>Inspect the files:</p>"
    "<pre><code>$ ls -l /sbin/mkfs.*</code></pre><p>A symlink.</p>"
    '<div class="bottom hr"><hr/></div></section></aside>'
)


def test_reboxed_note_keeps_none_of_the_original_body():
    # How Linux Works ch4: the shell kept its listing, so it showed twice
    rewritten = "<h2>What Is mkfs?</h2><p>mkfs is a frontend.</p><pre><code>$ ls -l /sbin/mkfs.*</code></pre>"
    out = blocks.restyle_notes(rewritten, BOX_HTML)
    assert out.count("<pre>") == 1
    assert "Frontend." not in out and "A symlink." not in out
    assert out.index("mkfs is a frontend.") < out.index('<div class="bottom hr">')


def test_reboxed_note_takes_no_more_paragraphs_than_it_held():
    rewritten = convert.markdown_to_html("## Note\n\nThe note, rewritten.\n\nThe chapter goes on.")
    out = blocks.restyle_notes(rewritten, NOTE_HTML)
    box_end = out.index("</aside>")
    assert out.index("The note, rewritten.") < box_end < out.index("The chapter goes on.")


def test_prose_opening_with_a_label_is_not_a_caption():
    rewritten = (
        "<pre><code>ls</code></pre>"
        '<p><a id="Page_31"></a>Listing 2-1 shows the listing command in use, and more.</p>'
    )
    assert blocks.restore_captions(rewritten, CAPTIONED_HTML) == rewritten


def test_caption_away_from_its_listing_is_left_alone():
    rewritten = "<p>Intro.</p><p>Listing 2-1: Listing files</p><p>More prose.</p>"
    assert blocks.restore_captions(rewritten, CAPTIONED_HTML) == rewritten


def test_restored_caption_keeps_the_paragraphs_other_anchors():
    rewritten = '<pre><code>ls</code></pre><p><a id="Page_31"></a>Listing 2-1: Listing files</p>'
    out = blocks.restore_captions(rewritten, CAPTIONED_HTML)
    assert 'class="CodeListingCaption"' in out and 'id="Page_31"' in out
    assert out.count('id="listing2-1"') == 1


def test_table_title_without_its_table_is_not_a_bare_figcaption():
    rewritten = "<pre><code>x</code></pre><p>Table 2-1: Special Characters</p>"
    out = blocks.restore_captions(rewritten, CAPTIONED_HTML)
    assert "<figcaption" not in out


def test_block_beside_an_anchor_is_lifted_out_of_its_paragraph():
    # How Linux Works: a restored anchor and figure shared one paragraph
    out = blocks.lift_blocks('<p><a id="Page_83"></a><figure><img src="a.png"/></figure></p><p>Next.</p>')
    assert out == '<a id="Page_83"></a><figure><img src="a.png"/></figure><p>Next.</p>'


def test_text_around_a_lifted_block_stays_in_paragraphs():
    out = blocks.lift_blocks('<p class="lead">Before <table><tr><td>1</td></tr></table> after.</p>')
    assert out == '<p class="lead">Before </p><table><tr><td>1</td></tr></table><p> after.</p>'


def test_paragraphs_without_blocks_are_untouched():
    html = "<p>Plain <em>text</em>.</p>"
    assert blocks.lift_blocks(html) == html


def test_long_sidebar_title_is_reboxed():
    original = (
        '<aside epub:type="sidebar"><div class="top hr"><hr/></div><section class="box">'
        "<h2>Non-Generic Inner Functions</h2><p>Old body.</p>"
        '<div class="bottom hr"><hr/></div></section></aside>'
    )
    rewritten = "<hr/><h2>Non-Generic Inner Functions</h2><p>New body.</p><hr/><p>After.</p>"
    out = blocks.restyle_notes(rewritten, original)
    assert '<section class="box">' in out and "New body." in out
    assert out.count("<hr/>") == 2  # the shell's own two rules, not the bare ones


def test_rebox_keeps_ids_unique_and_the_headings_anchor():
    original = (
        '<aside epub:type="sidebar"><section class="note"><h2 id="n1">Note</h2>'
        "<p>Old.</p></section></aside>"
    )
    rewritten = '<p><a id="n1"></a>Elsewhere.</p><h2><a id="Page_9"></a>Note</h2><p>New.</p>'
    out = blocks.restyle_notes(rewritten, original)
    assert out.count('id="n1"') == 1
    assert 'id="Page_9"' in out


def test_restored_caption_does_not_duplicate_an_anchor_placed_elsewhere():
    rewritten = '<p><a id="listing2-1"></a>See below.</p><pre><code>ls</code></pre><p>Listing 2-1: Listing files</p>'
    out = blocks.restore_captions(rewritten, CAPTIONED_HTML)
    assert out.count('id="listing2-1"') == 1 and 'class="CodeListingCaption"' in out


def test_block_inside_a_heading_or_emphasis_is_unwrapped():
    out = blocks.lift_blocks("<h1><header><h1>1 Foundations</h1></header></h1><p><em><figure>F</figure></em></p>")
    assert out == "<header><h1>1 Foundations</h1></header><figure>F</figure>"


def test_docbook_title_block_is_protected_whole():
    html = ('<div class="chapter"><div class="titlepage"><div><div><h1 class="title"><a id="t"></a>Chapter 7</h1>'
            '</div></div></div><p>Text.</p></div>')
    out, blocks_ = blocks.protect(html)
    assert blocks_["TITLE-0"].startswith('<div class="titlepage">') and "Chapter 7" in blocks_["TITLE-0"]
    assert "⟦TITLE-0" in out and "titlepage" not in out


def test_docbook_figure_is_protected_with_its_caption():
    html = ('<div class="figure"><a id="f1"></a><div class="figure-contents"><div class="mediaobject">'
            '<img src="a.png" alt="A"/></div></div><p class="title"><b>Figure 2-1. </b>Coins</p></div><p>Text.</p>')
    out, blocks_ = blocks.protect(html)
    token = next(k for k in blocks_ if k.startswith("DIV"))
    assert blocks_[token].startswith('<div class="figure">') and "Figure 2-1" in blocks_[token]
    assert "Coins" not in out.replace(f"⟦{token}", "")[out.find("⟧"):]


SIDEBAR = ('<div class="sidebar"><a id="tips"></a><p class="title">Tips</p>'
           '<div class="itemizedlist"><ul class="itemizedlist"><li>Old tip.</li></ul></div></div>')


def test_sidebar_rewritten_as_heading_and_list_is_reboxed_with_its_anchor():
    rewritten = "<h2>Tips</h2><ul><li>New tip.</li></ul><p>After.</p>"
    out = blocks.restyle_notes(rewritten, "<p>x</p>" + SIDEBAR)
    assert out.startswith('<div class="sidebar"><a id="tips"></a><p class="title">Tips</p>')
    assert "New tip." in out and "Old tip." not in out and out.endswith("<p>After.</p>")


def test_note_kept_as_a_labelled_quote_is_reboxed():
    note = '<div class="note"><h3 class="title">Note</h3><p>Old.</p></div>'
    out = blocks.restyle_notes("<blockquote><p><strong>Note:</strong> New text.</p></blockquote>", note)
    assert out.startswith('<div class="note"><h3 class="title">Note</h3>') and "<p>New text.</p>" in out
    assert "<blockquote>" not in out and "Note:" not in out


def test_singly_wrapped_blocks_get_their_wrapper_back():
    original = ('<div class="footnote"><p><a id="ftn.1" href="#r1">1</a> A note.</p></div>'
                '<div class="blockquote"><blockquote class="blockquote"><p>To be or not to be, that is the question.</p></blockquote></div>')
    rewritten = ('<p><a id="ftn.1"></a><a href="#r1">1</a> A note.</p>'
                 '<blockquote><p>To be, or not to be: that is the question.</p></blockquote>')
    out = blocks.restore_wrappers(rewritten, original)
    assert '<div class="footnote"><p><a id="ftn.1"></a>' in out
    assert '<div class="blockquote"><blockquote class="blockquote"><p>To be, or not' in out
    assert blocks.restore_wrappers(out, original) == out  # never wraps twice


def test_paragraphs_are_only_rewrapped_on_an_anchor_or_identical_text():
    original = '<div class="epigraph"><p>A fairly long original sentence that was quoted.</p></div>'
    assert blocks.restore_wrappers("<p>A fairly long original sentence that got reworded.</p>", original).startswith("<p>")


def test_link_and_anchor_classes_come_back():
    original = '<a class="footnote" href="#ftn.1" id="r1">1</a><a class="xref" href="#s2">2</a><a class="indexterm" id="ix1"></a>'
    out = blocks.restore_link_classes('<a id="r1"></a><a href="#ftn.1">1</a> <a href="#s2">x</a><a id="ix1"></a>', original)
    assert '<a class="footnote" href="#ftn.1">' in out and '<a class="xref" href="#s2">' in out and '<a class="indexterm" id="ix1">' in out


def test_section_lead_class_follows_the_publishers_convention():
    original = '<h2>A</h2><p class="BodyFirst">x</p><p>y</p><h2>B</h2><p class="BodyFirst">z</p>'
    out = blocks.restore_section_leads("<h2>A</h2><p>new</p><p>more</p><h3>C</h3><p>deep</p>", original)
    assert out == '<h2>A</h2><p class="BodyFirst">new</p><p>more</p><h3>C</h3><p class="BodyFirst">deep</p>'
    mixed = '<h2>A</h2><p class="BodyFirst">x</p><h2>B</h2><p>z</p><h2>C</h2><p>w</p>'
    assert blocks.restore_section_leads("<h2>A</h2><p>new</p>", mixed) == "<h2>A</h2><p>new</p>"


ROOT_NOTE = (
    '<aside epub:type="sidebar"><section class="note"><h2>Note</h2>'
    "<p>Operating as root can be dangerous. It can be difficult to identify and correct "
    "mistakes because the system will let you do anything, even if it is harmful.</p></section></aside>"
)


def test_note_kept_near_word_for_word_as_a_paragraph_is_reboxed():
    rewritten = (
        "<p>Root may alter any process.</p>"
        "<p>Operating as root can be dangerous. Mistakes can be difficult to identify and correct, "
        "because the system will let you do anything, even if it is harmful.</p>"
        "<p>Groups are sets of users.</p>"
    )
    out = blocks.restyle_notes(rewritten, ROOT_NOTE)
    assert '<section class="note"><h2>Note</h2><p>Operating as root can be dangerous. Mistakes' in out
    assert out.startswith("<p>Root may alter any process.</p>")
    assert out.endswith("<p>Groups are sets of users.</p>")
    assert blocks.restyle_notes(out, ROOT_NOTE) == out  # never boxes twice


def test_note_folded_into_other_prose_stays_prose():
    rewritten = (
        "<p>Root is the superuser, and the kernel lets it terminate any process, read any file "
        "and change any setting; that power is why designers keep root access rare.</p>"
    )
    assert blocks.restyle_notes(rewritten, ROOT_NOTE) == rewritten


def test_note_kept_in_a_list_item_is_not_reboxed():
    rewritten = (
        "<ul><li><p>Operating as root can be dangerous. It can be difficult to identify and correct "
        "mistakes because the system will let you do anything, even if it is harmful.</p></li></ul>"
    )
    assert blocks.restyle_notes(rewritten, ROOT_NOTE) == rewritten


def test_note_kept_behind_a_bare_label_line_is_reboxed():
    sidebar = '<div class="sidebar"><p class="title">Tips</p><ul><li>Old tip.</li></ul></div>'
    rewritten = "<p>Regression fits it.</p><p>Tips</p><ul><li>Don't split variables.</li></ul>"
    out = blocks.restyle_notes(rewritten, sidebar)
    assert '<div class="sidebar"><p class="title">Tips</p><ul><li>Don\'t split variables.</li></ul></div>' in out
    assert out.startswith("<p>Regression fits it.</p>")


def test_one_paragraph_of_a_longer_sidebar_stays_prose():
    sidebar = (
        '<div class="box"><h2>What Is mkfs?</h2>'
        "<p>mkfs.ext4 is just a symbolic link to mke2fs, so remember it when a system lacks mkfs.</p>"
        "<p>The mkfs front end dispatches on the type argument and runs the matching builder program.</p>"
        "<p>Each builder has its own options, which the front end passes along unchanged.</p></div>"
    )
    rewritten = "<p>mkfs.ext4 is just a symbolic link to mke2fs, so remember it when a system lacks mkfs.</p>"
    assert blocks.restyle_notes(rewritten, sidebar) == rewritten


ANNOTATED = (
    '<p>The GRUB root is set to a default value for this configuration '
    '<span class="CodeAnnotation" aria-label="annotation1">1</span>. The first argument '
    '(<code>/boot/vmlinuz</code>) <span class="CodeAnnotation" aria-label="annotation3">3</span> '
    "is the kernel image.</p>"
    '<pre>set root=x <span class="CodeAnnotation" aria-label="annotation1">1</span></pre>'
)


def test_code_annotations_come_back_after_the_word_they_followed():
    rewritten = (
        "<p>GRUB first sets the root to a default for this configuration 1. Then "
        "<code>/boot/vmlinuz</code> 3 names the kernel image, which is 1.5 MB.</p>"
    )
    out = blocks.restore_code_annotations(rewritten, ANNOTATED)
    assert re.search(r'configuration <span [^>]*class="CodeAnnotation"[^>]*>1</span>\.', out)
    assert re.search(r'</code> <span [^>]*class="CodeAnnotation"[^>]*>3</span> names', out)
    assert "1.5 MB" in out
    assert blocks.restore_code_annotations(out, ANNOTATED) == out


def test_code_annotations_leave_numbers_and_code_alone():
    rewritten = "<p>This configuration 12 differs.</p><pre>configuration 1</pre><p>Section 1.</p>"
    assert blocks.restore_code_annotations(rewritten, ANNOTATED) == rewritten


def test_code_annotations_after_a_bracket_or_a_marked_reference():
    original = (
        '<p>The first device (<code>/dev/sda</code>) <span class="CodeAnnotation">1</span> uses MBR, '
        'and the mode <span class="CodeAnnotation">2</span> holds permissions.</p>'
    )
    rewritten = "<p>The first device (<code>/dev/sda</code>) 1 uses MBR. The field marked 2 is the mode.</p>"
    out = blocks.restore_code_annotations(rewritten, original)
    assert re.search(r'\) <span class="CodeAnnotation">1</span> uses', out)
    assert re.search(r'marked <span class="CodeAnnotation">2</span> is', out)
