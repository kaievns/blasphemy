from unittest.mock import patch

from blasphemy import cli, providers


def test_check_providers_reports_each(monkeypatch, capsys):
    monkeypatch.setattr(providers.shutil, "which", lambda binary: "/x")
    assert cli.main(["--check-providers"]) == 0
    out = capsys.readouterr().out
    assert "claude" in out and "kiro" in out
    assert "missing" not in out


def test_check_providers_fails_when_none_installed(monkeypatch, capsys):
    monkeypatch.setattr(providers.shutil, "which", lambda binary: None)
    assert cli.main(["--check-providers"]) == 1
    assert "missing" in capsys.readouterr().out


def test_epub_required_without_check():
    assert cli.main([]) == 2


def test_unresolvable_provider_reports_error(sample_epub, monkeypatch, capsys):
    monkeypatch.setattr(providers.shutil, "which", lambda binary: None)
    assert cli.main([str(sample_epub)]) == 1
    assert "no agent CLI" in capsys.readouterr().err


def test_provider_selection_reaches_rewrite(sample_epub, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    body = "# R\n\n" + " ".join(["word"] * 100)
    with patch("blasphemy.providers.rewrite", return_value=body) as rewrite:
        cli.main([
            str(sample_epub), "-o", str(tmp_path / "o.epub"),
            "--provider", "kiro", "--no-primer",
        ])
    assert rewrite.call_args.kwargs["provider"] is providers.KIRO


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


APPARATUS_RAW = """=== ORIENT ===
Skeleton sentence.

=== KEY POINTS ===
- Claim.

=== CHECK YOURSELF ===
1. Why?

=== ANSWERS ===
1. Because.
"""


def test_run_wires_pipeline(sample_epub, tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    out = tmp_path / "out.epub"
    body = "# R\n\n" + " ".join(["word"] * 100)
    responses = ["PRIMER"] + [body, APPARATUS_RAW] * 2
    with patch("blasphemy.providers.rewrite", side_effect=responses) as rewrite:
        code = cli.main([str(sample_epub), "-o", str(out), "--provider", "claude", "--model", "sonnet"])
    assert code == 0
    assert out.exists()
    assert rewrite.call_args.kwargs["model"] == "sonnet"
    assert "rewritten" in capsys.readouterr().out

    # call order: primer, then body + apparatus per chapter
    primer_system = rewrite.call_args_list[0].args[1]
    assert "book primer" in primer_system.lower()
    body_system = rewrite.call_args_list[1].args[1]
    assert "# Book context" in body_system
    assert "Current chapter" in body_system
    assert "[Length contract:" in rewrite.call_args_list[1].args[0]
    assert "[Apparatus word cap:" in rewrite.call_args_list[2].args[0]
    assert "study apparatus" in rewrite.call_args_list[2].args[1]

    from blasphemy import epub as bp

    chapters = {c.item_id: c for c in bp.chapters(bp.load(out))}
    assert "Orient." in chapters["ch1"].html
    assert "Key points" in chapters["ch1"].html


def test_no_primer_flag(sample_epub, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    rewritten = "# R\n\n" + " ".join(["word"] * 100)
    with patch("blasphemy.providers.rewrite", return_value=rewritten) as rewrite:
        cli.main([str(sample_epub), "-o", str(tmp_path / "o.epub"), "--provider", "claude", "--no-primer"])
    assert all("# Book context" not in c.args[1] for c in rewrite.call_args_list)
