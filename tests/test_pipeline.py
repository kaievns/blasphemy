import pytest

from blasphemy import epub, pipeline


def optimise(sample_epub, tmp_path, rewrite, **kwargs):
    out = tmp_path / "out.epub"
    workdir = tmp_path / "work"
    results = pipeline.optimise(sample_epub, out, rewrite, workdir, **kwargs)
    return out, workdir, results


def test_short_chapters_skipped_long_rewritten(sample_epub, tmp_path):
    calls = []

    def rewrite(md):
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

    def rewrite(md):
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


def test_failure_keeps_original(sample_epub, tmp_path):
    def rewrite(md):
        raise RuntimeError("claude exploded")

    out, _, results = optimise(sample_epub, tmp_path, rewrite)
    ch1 = next(r for r in results if r.item_id == "ch1")
    assert ch1.status == "failed"
    assert "claude exploded" in ch1.detail

    chapters = {c.item_id: c for c in epub.chapters(epub.load(out))}
    assert "quick brown fox" in chapters["ch1"].html


def test_sanity_check_rejects_tiny_output(sample_epub, tmp_path):
    _, workdir, results = optimise(sample_epub, tmp_path, lambda md: "ok")
    assert all(r.status == "failed" for r in results if r.item_id != "cover")
    assert not (workdir / "001.md").exists()
    assert (workdir / "001.failed.md").read_text() == "ok"


def test_source_markdown_written_for_inspection(sample_epub, tmp_path):
    rewrite = lambda md: "# R\n\n" + " ".join(["word"] * 100)
    _, workdir, _ = optimise(sample_epub, tmp_path, rewrite)
    assert "quick brown fox" in (workdir / "001.src.md").read_text()


def test_sane_ratio_bounds():
    words = lambda n: " ".join(["w"] * n)
    assert pipeline.sane(words(100), words(50))
    assert not pipeline.sane(words(100), words(4))
    assert not pipeline.sane(words(100), words(200))


def test_workdir_for_is_content_addressed(sample_epub, tmp_path):
    first = pipeline.workdir_for(sample_epub, tmp_path)
    assert sample_epub.stem in first.name
    sample_epub.write_bytes(sample_epub.read_bytes() + b" ")
    assert pipeline.workdir_for(sample_epub, tmp_path) != first
