from blasphemy import epub, primer


def chapters_of(path):
    return epub.chapters(epub.load(path))


def test_excerpts_skip_short_and_nav(sample_epub):
    text = primer.excerpts(chapters_of(sample_epub))
    assert "Chapter One" in text
    assert "Chapter Two" in text
    assert "Cover page" not in text


def test_build_caches_and_force(sample_epub, tmp_path):
    calls = []

    def generate(text):
        calls.append(text)
        return "PRIMER"

    chapters = chapters_of(sample_epub)
    assert primer.build(chapters, generate, tmp_path) == "PRIMER"
    assert primer.build(chapters, generate, tmp_path) == "PRIMER"
    assert len(calls) == 1
    assert (tmp_path / "primer.md").read_text() == "PRIMER"

    primer.build(chapters, generate, tmp_path, force=True)
    assert len(calls) == 2


def test_chapter_context(sample_epub):
    chapter = chapters_of(sample_epub)[1]
    context = primer.chapter_context("THE-PRIMER", chapter)
    assert "THE-PRIMER" in context
    assert "chapter 1" in context
    assert "Chapter One" in context
