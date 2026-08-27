import re

from blasphemy import epub, pipeline


def optimise(sample_epub, tmp_path, rewrite, **kwargs):
    out = tmp_path / "out.epub"
    workdir = tmp_path / "work"
    results = pipeline.optimise(sample_epub, out, rewrite, workdir, **kwargs)
    return out, workdir, results


def test_short_chapters_skipped_long_rewritten(sample_epub, tmp_path):
    calls = []

    def rewrite(md, chapter):
        calls.append(md)
        return "# Rewritten\n\n" + " ".join(["word"] * 100)

    out, _, results = optimise(sample_epub, tmp_path, rewrite)
    statuses = {r.item_id: r.status for r in results}
    assert statuses == {"cover": "skipped", "ch1": "rewritten", "ch2": "rewritten"}
    assert len(calls) == 2

    chapters = {c.item_id: c for c in epub.chapters(epub.load(out))}
    assert "Rewritten" in chapters["ch1"].html
    assert "Cover page" in chapters["cover"].html


def test_cache_reused_and_force(sample_epub, tmp_path):
    output = "# Cached\n\n" + " ".join(["word"] * 100)
    calls = []

    def rewrite(md, chapter):
        calls.append(md)
        return output

    workdir = tmp_path / "work"
    pipeline.optimise(sample_epub, tmp_path / "a.epub", rewrite, workdir)
    assert len(calls) == 2

    results = pipeline.optimise(sample_epub, tmp_path / "b.epub", rewrite, workdir)
    assert len(calls) == 2
    assert all(r.status == "cached" for r in results if r.item_id != "cover")

    pipeline.optimise(sample_epub, tmp_path / "c.epub", rewrite, workdir, force=True)
    assert len(calls) == 4


def test_skip_indices_pass_through(sample_epub, tmp_path):
    calls = []

    def rewrite(md, chapter):
        calls.append(md)
        return "# R\n\n" + " ".join(["word"] * 100)

    _, _, results = optimise(sample_epub, tmp_path, rewrite, skip={1})
    statuses = {r.item_id: r.status for r in results}
    assert statuses["ch1"] == "skipped"
    assert statuses["ch2"] == "rewritten"
    assert len(calls) == 1


def test_only_restricts_rewrites(sample_epub, tmp_path):
    calls = []

    def rewrite(md, chapter):
        calls.append(chapter.index)
        return "# R\n\n" + " ".join(["word"] * 100)

    _, _, results = optimise(sample_epub, tmp_path, rewrite, only={2})
    statuses = {r.item_id: r.status for r in results}
    assert statuses == {"cover": "skipped", "ch1": "skipped", "ch2": "rewritten"}
    assert calls == [2]


def test_failure_keeps_original(sample_epub, tmp_path):
    def rewrite(md, chapter):
        raise RuntimeError("claude exploded")

    out, _, results = optimise(sample_epub, tmp_path, rewrite)
    ch1 = next(r for r in results if r.item_id == "ch1")
    assert ch1.status == "failed"
    assert "claude exploded" in ch1.detail

    chapters = {c.item_id: c for c in epub.chapters(epub.load(out))}
    assert "quick brown fox" in chapters["ch1"].html


def test_sanity_check_rejects_tiny_output(sample_epub, tmp_path):
    _, workdir, results = optimise(sample_epub, tmp_path, lambda md, chapter: "ok")
    assert all(r.status == "failed" for r in results if r.item_id != "cover")
    assert not (workdir / "001.md").exists()
    assert (workdir / "001.failed.md").read_text() == "ok"


def test_source_markdown_written_for_inspection(sample_epub, tmp_path):
    rewrite = lambda md, chapter: "# R\n\n" + " ".join(["word"] * 100)
    _, workdir, _ = optimise(sample_epub, tmp_path, rewrite)
    assert "quick brown fox" in (workdir / "001.src.md").read_text()


def test_protected_math_restored_in_output(math_epub, tmp_path):
    def rewrite(md, chapter):
        token = re.search(r"⟦MATH[^⟧]*⟧", md).group()
        return "# M\n\n" + " ".join(["word"] * 100) + f"\n\n{token}"

    out, _, results = optimise(math_epub, tmp_path, rewrite)
    assert results[0].status == "rewritten"
    chapters = epub.chapters(epub.load(out))
    assert "<msup>" in chapters[0].html
    assert "⟦" not in chapters[0].html


def test_lost_protected_block_fails_chapter(math_epub, tmp_path):
    rewrite = lambda md, chapter: "# M\n\n" + " ".join(["word"] * 100)
    out, workdir, results = optimise(math_epub, tmp_path, rewrite)
    assert results[0].status == "failed"
    assert "MATH-0" in results[0].detail
    assert not (workdir / "000.md").exists()
    assert (workdir / "000.failed.md").exists()
    chapters = epub.chapters(epub.load(out))
    assert "quick brown fox" in chapters[0].html


def test_nav_document_never_rewritten(tmp_path):
    from test_epub import _nav_book

    path = _nav_book(tmp_path)
    rewrite = lambda md, chapter: "# R\n\n" + " ".join(["word"] * 100)
    results = pipeline.optimise(
        path, tmp_path / "out.epub", rewrite, tmp_path / "work", min_words=0
    )
    by_href = {}
    for r in results:
        by_href[r.item_id] = r.status
    assert by_href["nav"] == "skipped"


def test_output_retitled_and_cover_badged(sample_epub, tmp_path):
    rewrite = lambda md, chapter: "# R\n\n" + " ".join(["word"] * 100)
    out, _, _ = optimise(sample_epub, tmp_path, rewrite)

    book = epub.load(out)
    assert book.metadata[epub.DC]["title"][0][0] == "Sample Book (Optimised)"
    original_cover = epub.cover_image(epub.load(sample_epub)).get_content()
    assert epub.cover_image(book).get_content() != original_cover


def test_anchor_restored_when_token_kept(sample_epub, tmp_path):
    def rewrite(md, chapter):
        token = re.search(r"⟦ANCHOR:[^⟧]*⟧", md).group()
        return f"# R\n\n{token}\n\n" + " ".join(["word"] * 100)

    out, _, results = optimise(sample_epub, tmp_path, rewrite)
    ch1 = next(c for c in epub.chapters(epub.load(out)) if c.item_id == "ch1")
    assert '<a id="sec1"></a>' in ch1.html
    assert "⟦" not in ch1.html
    assert "anchors fell back" not in next(r for r in results if r.item_id == "ch1").detail


def test_anchor_fallback_when_dropped(sample_epub, tmp_path):
    rewrite = lambda md, chapter: "# R\n\n" + " ".join(["word"] * 100)
    out, _, results = optimise(sample_epub, tmp_path, rewrite)
    ch1_result = next(r for r in results if r.item_id == "ch1")
    assert ch1_result.status == "rewritten"
    assert "anchors fell back" in ch1_result.detail
    ch1 = next(c for c in epub.chapters(epub.load(out)) if c.item_id == "ch1")
    assert ch1.html.count('<a id="sec1"></a>') == 1


def test_referenced_anchors_from_links_and_toc(sample_epub):
    book = epub.load(sample_epub)
    refs = pipeline.referenced_anchors(book, epub.chapters(book))
    assert refs["ch1.xhtml"] == {"sec1"}


def test_pre_markup_restored_in_output(sample_epub, tmp_path):
    def rewrite(md, chapter):
        return "# R\n\n```\nprint('hello')\n```\n\n" + " ".join(["word"] * 100)

    out, _, results = optimise(sample_epub, tmp_path, rewrite)
    ch1 = next(c for c in epub.chapters(epub.load(out)) if c.item_id == "ch1")
    assert "<pre><code>print('hello')</code></pre>" in ch1.html
    ch1_result = next(r for r in results if r.item_id == "ch1")
    assert "count mismatch" not in ch1_result.detail


def test_pre_count_mismatch_reported(sample_epub, tmp_path):
    rewrite = lambda md, chapter: "# R\n\n" + " ".join(["word"] * 100)
    _, _, results = optimise(sample_epub, tmp_path, rewrite)
    ch1 = next(r for r in results if r.item_id == "ch1")
    assert "count mismatch" in ch1.detail


def test_sane_allows_apparatus_floor_on_small_reference_chapters():
    words = lambda n: " ".join(["w"] * n)
    # a 233w availability table kept verbatim + ~220w apparatus = ratio 2.2
    assert pipeline.sane(words(233), words(514))
    # but the allowance is flat: it cannot excuse runaway output at scale
    assert not pipeline.sane(words(2000), words(3400))


def test_sane_ratio_bounds():
    words = lambda n: " ".join(["w"] * n)
    assert pipeline.sane(words(100), words(50))
    assert not pipeline.sane(words(100), words(4))
    # ceiling = 1.5x + the flat apparatus allowance
    assert pipeline.sane(words(100), words(400))
    assert not pipeline.sane(words(100), words(401))


def test_workdir_for_is_content_addressed(sample_epub, tmp_path):
    first = pipeline.workdir_for(sample_epub, tmp_path)
    assert sample_epub.stem in first.name
    sample_epub.write_bytes(sample_epub.read_bytes() + b" ")
    assert pipeline.workdir_for(sample_epub, tmp_path) != first
