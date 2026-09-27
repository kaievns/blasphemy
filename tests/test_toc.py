from ebooklib import epub as eb

from blasphemy import epub, pipeline, toc

CHAPTER = (
    "<h1>1 Foundations</h1><p>Answer.</p>"
    "<h2>How memory is laid out</h2><p>x</p>"
    "<h3>Stack</h3><p>x</p><h3>Heap</h3><p>x</p>"
    '<aside epub:type="sidebar"><section class="note"><h2>Note</h2><p>n</p></section></aside>'
    "<h2>How memory is laid out</h2><p>again</p>"
    '<h2 id="kept">Asides</h2><h4>Too deep</h4>'
)


def test_number_headings_skips_title_and_callouts_and_dedupes():
    html, headings = toc.number_headings(CHAPTER)
    assert [(d, t) for d, _, t in headings] == [
        (1, "How memory is laid out"), (2, "Stack"), (2, "Heap"),
        (1, "How memory is laid out"), (1, "Asides"),
    ]
    ids = [h for _, h, _ in headings]
    assert len(set(ids)) == len(ids) and "kept" in ids
    assert all(f'id="{h}"' in html for h in ids)


def test_number_headings_uses_h1_sections_when_the_book_does():
    # Statistics Done Wrong titles its sections with h1
    _, headings = toc.number_headings("<h1>Chapter 1</h1><h1>First</h1><h1>Second</h1>")
    assert [(d, t) for d, _, t in headings] == [(1, "First"), (1, "Second")]


def test_number_headings_skips_a_header_wrapped_title():
    _, headings = toc.number_headings("<header><h1><span>1</span> T</h1></header><h2>Part</h2>")
    assert [t for _, _, t in headings] == ["Part"]


def test_rebuild_toc_replaces_only_the_chapter_entry():
    old = [
        (eb.Section("Chapter 3", href="c03.xhtml"), [eb.Link("c03.xhtml#old-1", "3.1 Old", "n1")]),
        eb.Link("c04.xhtml", "Chapter 4", "n2"),
    ]
    new = toc.rebuild_toc(old, "c03.xhtml", [(1, "sec-a", "A"), (2, "sec-b", "B"), (1, "sec-c", "C")])
    section, kids = new[0]
    assert section.title == "Chapter 3"
    first, sub = kids[0]
    assert (first.title, first.href) == ("A", "c03.xhtml#sec-a")
    assert [(k.title, k.href) for k in sub] == [("B", "c03.xhtml#sec-b")]
    assert (kids[1].title, kids[1].href) == ("C", "c03.xhtml#sec-c")
    assert new[1] is old[1]


def test_rebuild_toc_upgrades_a_leaf_and_drops_later_entries_for_the_file():
    old = [eb.Link("ch005.xhtml#chapter-1", "Chapter 1", "a"), eb.Link("ch005.xhtml#s2", "stale", "b")]
    new = toc.rebuild_toc(old, "ch005.xhtml", [(1, "sec-x", "X")])
    assert len(new) == 1
    section, kids = new[0]
    assert section.href == "ch005.xhtml#chapter-1" and kids[0].href == "ch005.xhtml#sec-x"


NAV = (
    '<?xml version="1.0" encoding="utf-8"?><html xmlns="http://www.w3.org/1999/xhtml" '
    'xmlns:epub="http://www.idpf.org/2007/ops"><body>'
    '<nav epub:type="toc"><ol>'
    '<li class="TOCChapter"><a href="c03.xhtml">Chapter 3</a><ol>'
    '<li class="TOCH2"><a href="c03.xhtml#old">Old</a></li></ol></li>'
    '<li class="TOCChapter"><a href="c04.xhtml">Chapter 4</a></li></ol></nav>'
    '<nav epub:type="page-list"><ol><li><a href="c03.xhtml#Page_1">1</a></li>'
    '<li><a href="c04.xhtml#Page_2">2</a></li></ol></nav></body></html>'
)


def test_rebuild_nav_rewrites_the_chapter_list_and_prunes_its_pages():
    out = toc.rebuild_nav(NAV, "toc.xhtml", {"c03.xhtml": [(1, "sec-a", "A"), (2, "sec-b", "B")]})
    assert 'href="c03.xhtml#old"' not in out
    assert '<li class="TOCH2"><a href="c03.xhtml#sec-a">A</a><ol><li class="TOCH2"><a href="c03.xhtml#sec-b">B</a></li></ol></li>' in out
    assert 'href="c04.xhtml">Chapter 4' in out
    assert "Page_1" not in out and "Page_2" in out


def test_rebuild_nav_resolves_hrefs_relative_to_the_nav():
    nav = NAV.replace('href="c03.xhtml', 'href="../Text/c03.xhtml')
    out = toc.rebuild_nav(nav, "Nav/toc.xhtml", {"Text/c03.xhtml": [(1, "sec-a", "A")]})
    assert 'href="../Text/c03.xhtml#sec-a"' in out


def test_pipeline_points_the_toc_at_rewritten_headings(sample_epub, tmp_path):
    body = "# R\n\n## First part\n\n" + " ".join(["w"] * 200) + "\n\n## Second part\n\nmore"
    rewrite = lambda md, ch: body
    out = tmp_path / "o.epub"
    pipeline.optimise(sample_epub, out, rewrite, tmp_path / "w", only={1})
    book = epub.load(out)
    entry = next(e for e in book.toc if isinstance(e, tuple) and e[0].href.startswith("ch1.xhtml"))
    hrefs = [k.href for k in entry[1]]
    assert hrefs == ["ch1.xhtml#sec-first-part", "ch1.xhtml#sec-second-part"]
    ch1 = next(c for c in epub.chapters(book) if c.item_id == "ch1")
    assert 'id="sec-first-part"' in ch1.html and 'id="sec-second-part"' in ch1.html
    nav = next(i for i in book.get_items() if isinstance(i, eb.EpubNav))
    assert b"ch1.xhtml#sec-first-part" in nav.content
