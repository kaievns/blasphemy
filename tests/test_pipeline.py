import json
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
    output = "# Cached\n\n" + " ".join(["word"] * 300)
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


def test_unmatched_pre_reported_not_failed(sample_epub, tmp_path):
    # the model regenerated code that matches no original listing
    rewrite = lambda md, chapter: "# R\n\n```\nnot the original code\n```\n\n" + " ".join(["word"] * 100)
    _, _, results = optimise(sample_epub, tmp_path, rewrite)
    ch1 = next(r for r in results if r.item_id == "ch1")
    assert ch1.status == "rewritten"
    assert "1 code block(s) left fenced" in ch1.detail


def test_sane_ratio_bounds():
    words = lambda n: " ".join(["w"] * n)
    assert pipeline.sane(words(100), words(50))
    assert not pipeline.sane(words(100), words(4))
    assert pipeline.sane(words(100), words(150))
    assert not pipeline.sane(words(100), words(151))


def test_workdir_for_is_content_addressed(sample_epub, tmp_path):
    first = pipeline.workdir_for(sample_epub, tmp_path)
    assert sample_epub.stem in first.name
    sample_epub.write_bytes(sample_epub.read_bytes() + b" ")
    assert pipeline.workdir_for(sample_epub, tmp_path) != first


def test_banned_words_reported_in_detail(sample_epub, tmp_path):
    rewrite = lambda md, chapter: "# R\n\nwe delve\n\n" + " ".join(["word"] * 100)
    _, _, results = optimise(sample_epub, tmp_path, rewrite)
    ch1 = next(r for r in results if r.item_id == "ch1")
    assert ch1.status == "rewritten"
    assert "banned words: delve" in ch1.detail


def test_rebuild_never_evicts_cache_on_unrestorable_chapter(math_epub, tmp_path):
    # first run caches a rewrite that drops the MATH token
    out, workdir, _ = optimise(
        math_epub, tmp_path, lambda md, ch: "# M\n\n" + " ".join(["w"] * 300)
    )
    (workdir / "000.md").write_text("# M\n\n" + " ".join(["w"] * 300))
    before = sorted(p.name for p in workdir.iterdir())
    _, _, results = optimise(
        math_epub, tmp_path, lambda md, ch: (_ for _ in ()).throw(AssertionError),
        rebuild=True,
    )
    assert results[0].status == "failed" and "MATH-0" in results[0].detail
    assert sorted(p.name for p in workdir.iterdir()) == before


def test_unclosed_token_detected():
    assert pipeline.unclosed_token("text\n\n### ⟦AN")
    assert pipeline.unclosed_token("⟦ANCHOR:a⟧ ok ⟦MATH-0: x")
    assert pipeline.unclosed_token("⟦MATH-0: x ⟦ANCHOR:a⟧")
    assert not pipeline.unclosed_token("⟦ANCHOR:a⟧ ok ⟦MATH-0: x⟧ fine")
    assert not pipeline.unclosed_token("no tokens at all")


def test_body_problem_flags_cut_off_and_refused_bodies():
    source = " ".join(["w"] * 1000)
    whole = "# T\n\n" + " ".join(["w"] * 600)
    assert pipeline.body_problem(source, whole) == ""
    assert "token" in pipeline.body_problem(source, whole + "\n\n### ⟦AN")
    assert "heading" in pipeline.body_problem(source, whole + "\n\n## Next part\n")
    assert "1%" in pipeline.body_problem(source, "I can't help with that chapter, sorry.")


def test_body_problem_flags_a_tail_fragment():
    source = "⟦TITLE-0: 9 Networks⟧\n\n" + " ".join(["w"] * 1000)
    fragment = "ections*: hardware devices plus " + " ".join(["w"] * 700)
    assert "title" in pipeline.body_problem(source, fragment)
    whole = "⟦TITLE-0: 9 Networks⟧\n\n" + " ".join(["w"] * 700)
    assert pipeline.body_problem(source, whole) == ""


def test_body_problem_skips_leading_anchors_before_the_title():
    source = "⟦ANCHOR:ch3⟧\n\n# Chapter 3\n\n" + " ".join(["w"] * 100)
    body = "⟦ANCHOR:ch3⟧\n\n# Chapter 3\n\n" + " ".join(["w"] * 60)
    assert pipeline.body_problem(source, body) == ""
    assert "title" in pipeline.body_problem(source, "⟦ANCHOR:ch3⟧\n\n" + " ".join(["w"] * 60))


def test_body_problem_allows_a_closing_code_fence():
    source = " ".join(["w"] * 100)
    body = " ".join(["w"] * 60) + "\n\n```\n# a shell comment\n```"
    assert pipeline.body_problem(source, body) == ""


def test_cut_off_output_fails_and_is_not_cached(sample_epub, tmp_path):
    rewrite = lambda md, ch: "# R\n\n" + " ".join(["word"] * 100) + "\n\n### ⟦AN"
    _, workdir, results = optimise(sample_epub, tmp_path, rewrite, only={1})
    ch1 = next(r for r in results if r.item_id == "ch1")
    assert ch1.status == "failed" and "cut off" in ch1.detail
    assert not pipeline.chapter_file(workdir, 1).exists()
    assert pipeline.chapter_file(workdir, 1, "failed").exists()


def test_cut_off_cache_is_rewritten_not_shipped(sample_epub, tmp_path):
    workdir = tmp_path / "work"
    workdir.mkdir()
    pipeline.chapter_file(workdir, 1).write_text("# R\n\n" + " ".join(["w"] * 100) + "\n\n### ⟦AN")
    calls = []

    def rewrite(md, ch):
        calls.append(ch.index)
        return "# R\n\n" + " ".join(["word"] * 100)

    results = pipeline.optimise(sample_epub, tmp_path / "o.epub", rewrite, workdir, only={1})
    assert calls == [1]
    assert next(r for r in results if r.item_id == "ch1").status == "rewritten"
    assert "⟦AN" not in pipeline.chapter_file(workdir, 1).read_text()


def test_cut_off_cache_fails_on_rebuild_and_stays(sample_epub, tmp_path):
    workdir = tmp_path / "work"
    workdir.mkdir()
    cut = "# R\n\n" + " ".join(["w"] * 100) + "\n\n### ⟦AN"
    pipeline.chapter_file(workdir, 1).write_text(cut)

    def rewrite(md, ch):
        raise RuntimeError("not cached; rerun without --rebuild to rewrite")

    results = pipeline.optimise(
        sample_epub, tmp_path / "o.epub", rewrite, workdir, only={1}, rebuild=True
    )
    ch1 = next(r for r in results if r.item_id == "ch1")
    assert ch1.status == "failed" and "cut off" in ch1.detail
    assert pipeline.chapter_file(workdir, 1).read_text() == cut


def test_chapter_file_names():
    assert pipeline.chapter_file("w", 7).name == "007.md"
    assert pipeline.chapter_file("w", 7, "failed").name == "007.failed.md"


WHOLE = "# Chapter One\n\n" + " ".join(["word"] * 300)
LEGACY = WHOLE + "\n\n## Key points\n\n- A claim.\n\n## Check yourself\n\n1. Why?\n\n**Answers**\n\n1. Because."


def test_opening_line_sees_a_title_behind_an_anchor_on_the_same_line():
    assert pipeline.opening_line("⟦ANCHOR:c1⟧ ⟦TITLE-0: 1 Foundations⟧\n\nx") == "⟦TITLE-0: 1 Foundations⟧"
    assert pipeline.opening_line("\n⟦ANCHOR:a⟧ ⟦ANCHOR:b⟧\n\n# T\n") == "# T"


def test_upgrade_cached_strips_the_retired_apparatus():
    assert pipeline.upgrade_cached("# Chapter One\n\nsrc", LEGACY) == WHOLE
    key_points_only = WHOLE + "\n\n## Key points\n\n- Front matter only."
    assert pipeline.upgrade_cached("# Chapter One\n\nsrc", key_points_only) == WHOLE


def test_upgrade_cached_keeps_a_books_own_key_points():
    own = WHOLE + "\n\n## Key Points\n\n- The author's summary."
    assert pipeline.upgrade_cached("# Chapter One\n\n## Key Points\n\nsrc", own) == own


def test_upgrade_cached_removes_the_doubled_pandoc_title():
    doubled = "# Chapter 1 - Introduction\n\n⟦ANCHOR:chapter-1⟧\n\n# Chapter 1 - Introduction\n\nBody."
    assert pipeline.upgrade_cached("x", doubled) == "⟦ANCHOR:chapter-1⟧\n\n# Chapter 1 - Introduction\n\nBody."


def test_upgrade_cached_leaves_current_output_alone():
    assert pipeline.upgrade_cached("# Chapter One\n\nsrc", WHOLE) == WHOLE


def seed_cache(tmp_path, text):
    workdir = tmp_path / "work"
    workdir.mkdir()
    pipeline.chapter_file(workdir, 1).write_text(text)
    return workdir


def test_legacy_cache_is_cleaned_in_place_for_free(sample_epub, tmp_path):
    workdir = seed_cache(tmp_path, LEGACY)
    calls = []
    results = pipeline.optimise(
        sample_epub, tmp_path / "o.epub", lambda md, ch: calls.append(1), workdir, only={1}
    )
    assert calls == []
    assert next(r for r in results if r.item_id == "ch1").status == "cached"
    assert pipeline.chapter_file(workdir, 1).read_text() == WHOLE
    ch1 = next(c for c in epub.chapters(epub.load(tmp_path / "o.epub")) if c.item_id == "ch1")
    assert "Key points" not in ch1.html


def test_legacy_cache_is_cleaned_but_not_written_on_rebuild(sample_epub, tmp_path):
    workdir = seed_cache(tmp_path, LEGACY)
    pipeline.optimise(
        sample_epub, tmp_path / "o.epub", lambda md, ch: None, workdir, only={1}, rebuild=True
    )
    assert pipeline.chapter_file(workdir, 1).read_text() == LEGACY
    ch1 = next(c for c in epub.chapters(epub.load(tmp_path / "o.epub")) if c.item_id == "ch1")
    assert "Key points" not in ch1.html


def test_cached_tail_fragment_is_rewritten(sample_epub, tmp_path):
    workdir = seed_cache(tmp_path, "ections: the second half only " + " ".join(["w"] * 300))
    calls = []

    def rewrite(md, ch):
        calls.append(ch.index)
        return WHOLE

    results = pipeline.optimise(sample_epub, tmp_path / "o.epub", rewrite, workdir, only={1})
    assert calls == [1]
    assert next(r for r in results if r.item_id == "ch1").status == "rewritten"


def test_failed_force_run_never_serves_the_old_rewrite_again(sample_epub, tmp_path):
    workdir = seed_cache(tmp_path, WHOLE)

    def quota(md, ch):
        raise RuntimeError("quota")

    pipeline.optimise(sample_epub, tmp_path / "a.epub", quota, workdir, only={1}, force=True)
    assert not pipeline.chapter_file(workdir, 1).exists()
    assert pipeline.chapter_file(workdir, 1, "stale").read_text() == WHOLE
    calls = []
    pipeline.optimise(
        sample_epub, tmp_path / "b.epub", lambda md, ch: calls.append(1) or WHOLE, workdir, only={1}
    )
    assert calls == [1]


def test_check_note_sums_passes_and_reports_failures(tmp_path):
    record = tmp_path / "001.check.json"
    record.write_text(json.dumps({"passes": [{"applied": [1, 2], "rejected": []}, {"applied": [3], "rejected": []}]}))
    assert pipeline.check_note(record) == "opening check: 3 fixed (2 + 1)"
    record.write_text(json.dumps({"passes": [{"applied": [1], "rejected": []}, {"error": "quota"}]}))
    assert pipeline.check_note(record) == "opening check: 1 fixed (1 + 0), a pass failed: quota"
    record.write_text(json.dumps({"passes": [{"error": "quota"}]}))
    assert pipeline.check_note(record) == "opening check failed: quota"
    record.write_text(json.dumps({"applied": [1], "rejected": []}))
    assert pipeline.check_note(record) == "opening check: 1 fixed"
