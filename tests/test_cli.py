from unittest.mock import patch

import pytest

from blasphemy import cli, providers


@pytest.fixture(autouse=True)
def providers_installed(monkeypatch):
    # keep the suite independent of which agent CLIs this machine has
    monkeypatch.setattr(providers.shutil, "which", lambda binary: f"/usr/bin/{binary}")


def test_check_providers_reports_each(capsys):
    assert cli.main(["--check-providers"]) == 0
    out = capsys.readouterr().out
    assert "claude" in out and "kiro" in out
    assert "missing" not in out


def test_check_providers_shows_kiro_defaults(capsys):
    cli.main(["--check-providers"])
    assert "claude-fable-5.1 @ high" in capsys.readouterr().out


def test_check_providers_fails_when_none_installed(monkeypatch, capsys):
    monkeypatch.setattr(providers.shutil, "which", lambda binary: None)
    assert cli.main(["--check-providers"]) == 1
    assert "missing" in capsys.readouterr().out


def test_epub_required_without_check():
    assert cli.main([]) == 2


def test_missing_binary_reports_error_and_alternative(sample_epub, monkeypatch, capsys):
    monkeypatch.setattr(providers, "FALLBACK_DIRS", ())
    monkeypatch.setattr(providers.shutil, "which", lambda binary: None)
    assert cli.main([str(sample_epub)]) == 1
    err = capsys.readouterr().err
    assert "claude not found" in err
    assert "--provider kiro" in err


def test_defaults_to_claude(sample_epub, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    body = "# R\n\n" + " ".join(["word"] * 100)
    with patch("blasphemy.providers.rewrite", return_value=body) as rewrite:
        cli.main([str(sample_epub), "-o", str(tmp_path / "o.epub"), "--no-primer"])
    assert rewrite.call_args.kwargs["provider"] is providers.CLAUDE


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
    assert "retention apparatus" in rewrite.call_args_list[2].args[1]

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


def test_body_retried_once_when_banned_word_slips(sample_epub, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    clean = "# R\n\n" + " ".join(["word"] * 100)
    dirty = "# R\n\nwe delve\n\n" + " ".join(["word"] * 100)
    responses = [dirty, clean, APPARATUS_RAW, clean, APPARATUS_RAW]
    with patch("blasphemy.providers.rewrite", side_effect=responses) as rewrite:
        assert cli.main([str(sample_epub), "-o", str(tmp_path / "o.epub"), "--no-primer"]) == 0
    retry = rewrite.call_args_list[1].args[0]
    assert "banned word(s): delve" in retry
    assert rewrite.call_count == 5


def test_default_prompts_carry_the_ban():
    assert "# Banned words" in cli.default_prompt("body")
    assert "# Banned words" in cli.default_prompt("apparatus")


def test_rebuild_never_calls_an_agent(sample_epub, tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    # no agent CLI installed at all: rebuild must not care
    monkeypatch.setattr(providers.shutil, "which", lambda binary: None)
    monkeypatch.setattr(providers, "FALLBACK_DIRS", ())
    out = tmp_path / "o.epub"
    with patch("blasphemy.providers.rewrite") as rewrite:
        code = cli.main([str(sample_epub), "-o", str(out), "--rebuild"])
    rewrite.assert_not_called()
    assert out.exists()
    # nothing cached, so every eligible chapter keeps its original text
    assert "not cached" in capsys.readouterr().out
    assert code == 1  # uncached chapters are reported as failed, honestly
