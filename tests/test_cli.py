from unittest.mock import patch

from blasphemy import cli


def test_list_prints_chapters(sample_epub, capsys):
    assert cli.main([str(sample_epub), "--list"]) == 0
    out = capsys.readouterr().out
    assert "ch1.xhtml" in out
    assert "Chapter One" in out


def test_missing_file():
    assert cli.main(["nope.epub"]) == 1


def test_default_prompt_loads():
    prompt = cli.default_prompt()
    assert "markdown" in prompt.lower()


def test_run_wires_pipeline(sample_epub, tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    out = tmp_path / "out.epub"
    rewritten = "# R\n\n" + " ".join(["word"] * 100)
    with patch("blasphemy.claude.rewrite", return_value=rewritten) as rewrite:
        code = cli.main([str(sample_epub), "-o", str(out), "--model", "sonnet"])
    assert code == 0
    assert out.exists()
    assert rewrite.call_args.kwargs["model"] == "sonnet"
    assert "rewritten" in capsys.readouterr().out

    # call order: primer, then compress + enhance per chapter
    primer_system = rewrite.call_args_list[0].args[1]
    assert "book primer" in primer_system.lower()
    compress_system = rewrite.call_args_list[1].args[1]
    assert "# Book context" in compress_system
    assert "Current chapter" in compress_system
    assert "[Length contract:" in rewrite.call_args_list[1].args[0]
    assert "[Growth contract:" in rewrite.call_args_list[2].args[0]
    assert "APPARATUS pass" in rewrite.call_args_list[2].args[1]


def test_shrink_pass_on_oversized_draft(sample_epub, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    oversized = "# R\n\n" + " ".join(["word"] * 450)
    shrunk = "# R\n\n" + " ".join(["word"] * 200)
    enhanced = "# R\n\n" + " ".join(["word"] * 240)
    with patch(
        "blasphemy.claude.rewrite", side_effect=[oversized, shrunk, enhanced] * 2
    ) as rewrite:
        code = cli.main([str(sample_epub), "-o", str(tmp_path / "o.epub"), "--no-primer"])
    assert code == 0
    assert rewrite.call_count == 6
    assert "[The draft above is" in rewrite.call_args_list[1].args[0]
    assert "[Growth contract:" in rewrite.call_args_list[2].args[0]


def test_no_primer_flag(sample_epub, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    rewritten = "# R\n\n" + " ".join(["word"] * 100)
    with patch("blasphemy.claude.rewrite", return_value=rewritten) as rewrite:
        cli.main([str(sample_epub), "-o", str(tmp_path / "o.epub"), "--no-primer"])
    assert all("# Book context" not in c.args[1] for c in rewrite.call_args_list)
