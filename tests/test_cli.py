import json
from unittest.mock import patch

import pytest

from blasphemy import cli, providers


# a body above the refusal floor for the ~490-word sample chapters
BODY = "# R\n\n" + " ".join(["word"] * 300)
NO_FIXES = '{"fixes": []}'


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
    out = capsys.readouterr().out
    assert "claude-opus-5.5 @ xhigh" in out and "claude-opus-5-5 @ xhigh" in out


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




def test_run_wires_pipeline(sample_epub, tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    out = tmp_path / "out.epub"
    responses = ["PRIMER", BODY, BODY, NO_FIXES, NO_FIXES, BODY, BODY, NO_FIXES, NO_FIXES]
    with patch("blasphemy.providers.rewrite", side_effect=responses) as rewrite:
        code = cli.main([str(sample_epub), "-o", str(out), "--provider", "claude", "--model", "sonnet"])
    assert code == 0
    assert out.exists()
    assert rewrite.call_args.kwargs["model"] == "sonnet"
    assert "rewritten" in capsys.readouterr().out

    # call order: primer, then a body, a second-pass and two check calls per chapter
    assert rewrite.call_count == 9
    primer_system = rewrite.call_args_list[0].args[1]
    assert "book primer" in primer_system.lower()
    body_system = rewrite.call_args_list[1].args[1]
    assert "# Book context" in body_system
    assert "Current chapter" in body_system
    assert "[Length contract:" in rewrite.call_args_list[1].args[0]



def test_no_primer_flag(sample_epub, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    rewritten = "# R\n\n" + " ".join(["word"] * 100)
    with patch("blasphemy.providers.rewrite", return_value=rewritten) as rewrite:
        cli.main([str(sample_epub), "-o", str(tmp_path / "o.epub"), "--provider", "claude", "--no-primer"])
    assert all("# Book context" not in c.args[1] for c in rewrite.call_args_list)


def test_body_retried_once_when_banned_word_slips(sample_epub, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    clean = BODY
    dirty = "# R\n\nwe delve\n\n" + " ".join(["word"] * 300)
    responses = [dirty, clean, clean, NO_FIXES, NO_FIXES, clean, clean, NO_FIXES, NO_FIXES]
    with patch("blasphemy.providers.rewrite", side_effect=responses) as rewrite:
        assert cli.main([str(sample_epub), "-o", str(tmp_path / "o.epub"), "--no-primer"]) == 0
    retry = rewrite.call_args_list[1].args[0]
    assert "banned word(s): delve" in retry
    assert rewrite.call_count == 9


def test_body_prompt_keeps_hedges_and_adds_no_links():
    body = cli.default_prompt("body")
    assert "never delete or strengthen a hedge" in body
    assert "never add a cause, ranking, count or superlative" in body
    assert "literal and flat" not in body


def test_body_prompt_carries_the_ban():
    assert "# Banned words" in cli.default_prompt("body")


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


def test_cut_off_body_fails_and_is_kept_for_inspection(sample_epub, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cut = BODY + "\n\n### ⟦AN"
    out = tmp_path / "o.epub"
    with patch("blasphemy.providers.rewrite", side_effect=[cut]) as rewrite:
        code = cli.main([str(sample_epub), "-o", str(out), "--no-primer", "--only", "1"])
    assert code == 1
    assert rewrite.call_count == 1
    from blasphemy import pipeline

    workdir = pipeline.workdir_for(sample_epub)
    assert pipeline.chapter_file(workdir, 1, "failed").read_text() == cut
    assert not pipeline.chapter_file(workdir, 1).exists()


OPENING = "# R\n\nThe answer: quick brown foxes always win.\n\n" + " ".join(["word"] * 300)
FIX = json.dumps({"fixes": [{
    "sentence": "The answer: quick brown foxes always win.",
    "source": "The quick brown fox jumps over the lazy dog",
    "problem": "invented claim",
    "replacement": "The answer: the quick brown fox jumps over the lazy dog.",
}]})


def check_run(sample_epub, tmp_path, responses, *extra):
    out = tmp_path / "o.epub"
    with patch("blasphemy.providers.rewrite", side_effect=responses) as rewrite:
        code = cli.main([str(sample_epub), "-o", str(out), "--no-primer", "--only", "1", *extra])
    from blasphemy import pipeline

    workdir = pipeline.workdir_for(sample_epub)
    record = pipeline.check_record(workdir, 1)
    return code, rewrite, pipeline.chapter_file(workdir, 1), record


def test_opening_check_patches_the_body_and_records_it(sample_epub, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    code, rewrite, cached, record = check_run(sample_epub, tmp_path, [OPENING, OPENING, FIX, NO_FIXES])
    assert code == 0 and rewrite.call_count == 4
    assert "TOP:" in rewrite.call_args_list[2].args[0]
    assert "jumps over the lazy dog." in rewrite.call_args_list[3].args[0]  # the second check reads the fixed opening
    assert "always win" not in cached.read_text()
    assert "jumps over the lazy dog." in cached.read_text()
    passes = json.loads(record.read_text())["passes"]
    assert passes[0]["applied"][0]["problem"] == "invented claim" and passes[1]["applied"] == []


def test_opening_check_failure_keeps_the_body(sample_epub, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    code, _, cached, record = check_run(sample_epub, tmp_path, [OPENING, OPENING, RuntimeError("quota")])
    assert code == 0 and "always win" in cached.read_text()
    assert "quota" in json.loads(record.read_text())["passes"][0]["error"]


def test_no_check_skips_the_pass(sample_epub, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    code, rewrite, cached, record = check_run(sample_epub, tmp_path, [OPENING, OPENING], "--no-check")
    assert code == 0 and rewrite.call_count == 2 and not record.exists()


def test_opening_check_outcome_is_in_the_chapter_result(sample_epub, tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    check_run(sample_epub, tmp_path, [OPENING, OPENING, FIX, NO_FIXES])
    assert "opening check: 1 fixed (1 + 0)" in capsys.readouterr().out


REVISED = OPENING.replace("The answer: quick brown foxes always win.", "The answer, in the author's words: quick brown foxes always win.")


def polish_record(sample_epub):
    from blasphemy import pipeline

    return pipeline.polish_record(pipeline.workdir_for(sample_epub), 1)


def test_second_pass_revises_the_body_before_the_check(sample_epub, tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    code, rewrite, cached, _ = check_run(sample_epub, tmp_path, [OPENING, REVISED, NO_FIXES, NO_FIXES])
    assert code == 0 and rewrite.call_count == 4
    payload, system = rewrite.call_args_list[1].args
    assert "REWRITE:" in payload and "The answer: quick brown foxes" in payload
    assert system == cli.default_prompt("polish")
    assert "in the author's words" in rewrite.call_args_list[2].args[0]  # the check reads the revision
    assert "in the author's words" in cached.read_text()
    assert json.loads(polish_record(sample_epub).read_text()) == {"attempts": 1, "rejected": []}
    assert "second pass applied" in capsys.readouterr().out


def test_second_pass_that_breaks_the_guards_keeps_the_body(sample_epub, tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    broken = "Sure, here is the chapter.\n\n" + OPENING
    code, rewrite, cached, _ = check_run(sample_epub, tmp_path, [OPENING, broken, broken, NO_FIXES, NO_FIXES])
    assert code == 0 and rewrite.call_count == 5
    assert cached.read_text().startswith("# R") and "Sure, here" not in cached.read_text()
    assert json.loads(polish_record(sample_epub).read_text())["kept_body"]
    assert "second pass rejected" in capsys.readouterr().out


def test_second_pass_failure_keeps_the_body_and_still_checks(sample_epub, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    code, rewrite, cached, record = check_run(sample_epub, tmp_path, [OPENING, RuntimeError("quota"), FIX, NO_FIXES])
    assert code == 0 and rewrite.call_count == 4
    assert "quota" in json.loads(polish_record(sample_epub).read_text())["error"]
    assert json.loads(record.read_text())["passes"][0]["applied"]


def test_no_polish_skips_the_second_pass(sample_epub, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    code, rewrite, _, _ = check_run(sample_epub, tmp_path, [OPENING, NO_FIXES, NO_FIXES], "--no-polish")
    assert code == 0 and rewrite.call_count == 3 and not polish_record(sample_epub).exists()


def test_polish_prompt_keeps_readability_and_quotes_only_the_author():
    prompt = cli.default_prompt("polish")
    assert "under 30 words" in prompt and "Never add a flourish of your own" in prompt
    assert "Reasons are not repeats" in prompt
    assert "When cutting a repeat would cost any reasoning, keep the repeat" in prompt
    assert "Takeaways are not repeats either" in prompt
    assert "Every back-reference must still point at something" in prompt
    assert "# Banned words" in prompt


def test_every_run_ends_with_an_integrity_report(sample_epub, tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    out = tmp_path / "o.epub"
    with patch("blasphemy.providers.rewrite", side_effect=[OPENING, OPENING, NO_FIXES, NO_FIXES]):
        code = cli.main([str(sample_epub), "-o", str(out), "--no-primer", "--only", "1"])
    from blasphemy import pipeline

    record = pipeline.integrity_record(pipeline.workdir_for(sample_epub))
    assert record.exists() and "integrity:" in capsys.readouterr().out
    problems = [f for f in json.loads(record.read_text()) if f["level"] == "problem"]
    assert code == (1 if problems else 0)


def test_verify_checks_a_built_book_without_agent_calls(sample_epub, tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    out = tmp_path / "o.epub"
    cli.main([str(sample_epub), "-o", str(out), "--rebuild"])
    capsys.readouterr()
    with patch("blasphemy.providers.rewrite") as rewrite:
        code = cli.main([str(sample_epub), "-o", str(out), "--verify"])
    rewrite.assert_not_called()
    assert code == 0 and "integrity: 0 problems" in capsys.readouterr().out


def test_verify_fails_on_problems_and_on_a_missing_output(sample_epub, tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert cli.main([str(sample_epub), "-o", str(tmp_path / "none.epub"), "--verify"]) == 1
    from blasphemy import integrity

    out = tmp_path / "o.epub"
    cli.main([str(sample_epub), "-o", str(out), "--rebuild"])
    broken = [integrity.Finding("problem", "links broken", "ch.xhtml", "1: x.xhtml")]
    with patch("blasphemy.integrity.verify", return_value=broken):
        assert cli.main([str(sample_epub), "-o", str(out), "--verify"]) == 1
    assert "problem: links broken" in capsys.readouterr().out
