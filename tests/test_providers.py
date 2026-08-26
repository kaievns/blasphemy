import subprocess
from unittest.mock import patch

import pytest

from blasphemy import providers


def completed(returncode=0, stdout="rewritten", stderr=""):
    return subprocess.CompletedProcess([], returncode, stdout, stderr)


def test_claude_call_uses_flags_and_stdin():
    cmd, stdin = providers.build_call(
        providers.CLAUDE, "CHAPTER", "SYSTEM", model="opus", effort="high"
    )
    assert cmd[0].endswith("claude")
    assert cmd[cmd.index("--model") + 1] == "opus"
    assert cmd[cmd.index("--effort") + 1] == "high"
    assert cmd[cmd.index("--system-prompt") + 1] == "SYSTEM"
    assert cmd[cmd.index("--tools") + 1] == ""
    assert "--no-session-persistence" in cmd
    assert "--bare" not in cmd
    assert stdin == "CHAPTER"


def test_default_model_applied_when_unset():
    cmd, _ = providers.build_call(providers.CLAUDE, "CHAPTER", "SYSTEM")
    assert cmd[cmd.index("--model") + 1] == providers.CLAUDE.default_model


def test_kiro_call_shape():
    cmd, stdin = providers.build_call(providers.KIRO, "CHAPTER", "SYSTEM")
    assert cmd[0].endswith("kiro-cli")  # bare `kiro` opens the IDE
    assert cmd[1:3] == ["chat", "--no-interactive"]
    assert "--trust-tools=" in cmd  # trust nothing; never --trust-all-tools
    assert "--trust-all-tools" not in cmd
    # no --model unless asked: kiro's own default model stands
    assert "--model" not in cmd
    # kiro has no system-prompt flag, and only reads stdin with no argv prompt
    assert stdin.startswith("SYSTEM") and stdin.endswith("CHAPTER")
    assert cmd[-1] != stdin


def test_effort_omitted_when_provider_lacks_flag():
    provider = providers.Provider(name="x", binary="x", default_model="")
    cmd, _ = providers.build_call(provider, "CHAPTER", "SYSTEM", effort="high")
    assert "--effort" not in cmd


def test_strip_chrome_removes_ansi_and_credits_footer():
    raw = "\x1b[1mAnswer\x1b[0m text\n\n▸ Credits: 0.39 • Time: 22s\n"
    assert providers.strip_chrome(raw) == "Answer text"


def test_kiro_output_is_sanitised_and_env_applied():
    noisy = completed(stdout="\x1b[32mclean\x1b[0m\n▸ Credits: 0.4 • Time: 3s\n")
    with patch("subprocess.run", return_value=noisy) as run:
        assert providers.rewrite(
            "chapter", "SYSTEM", provider=providers.KIRO
        ) == "clean"
    env = run.call_args.kwargs["env"]
    assert env["NO_COLOR"] == "1" and env["KIRO_ASCII_MODE"] == "1"


def test_claude_run_inherits_env_unchanged():
    with patch("subprocess.run", return_value=completed()) as run:
        providers.rewrite("chapter", "SYSTEM")
    assert run.call_args.kwargs["env"] is None


def test_system_prompt_folded_into_stdin_without_flag():
    provider = providers.Provider(name="x", binary="x", default_model="")
    cmd, stdin = providers.build_call(provider, "CHAPTER", "SYSTEM")
    assert cmd == ["x"]
    assert stdin.startswith("SYSTEM")
    assert stdin.endswith("CHAPTER")


def test_prompt_as_arg_provider_sends_no_stdin():
    provider = providers.Provider(
        name="x", binary="x", default_model="", prompt_as_arg=True
    )
    cmd, stdin = providers.build_call(provider, "CHAPTER", "SYSTEM")
    assert stdin is None
    assert cmd[-1].endswith("CHAPTER")


def test_binary_override_from_env(monkeypatch):
    monkeypatch.setenv("BLASPHEMY_KIRO_BIN", "/opt/kiro/bin/kiro")
    cmd, _ = providers.build_call(providers.KIRO, "CHAPTER", "SYSTEM")
    assert cmd[0] == "/opt/kiro/bin/kiro"


def test_binary_found_in_fallback_dir_when_not_on_path(monkeypatch, tmp_path):
    installed = tmp_path / "claude"
    installed.write_text("#!/bin/sh\n")
    installed.chmod(0o755)
    monkeypatch.setattr(providers, "FALLBACK_DIRS", (str(tmp_path),))
    monkeypatch.setattr(providers.shutil, "which", lambda binary: None)
    assert providers.binary_for(providers.CLAUDE) == str(installed)


def test_binary_falls_back_to_bare_name_when_nowhere(monkeypatch):
    monkeypatch.setattr(providers, "FALLBACK_DIRS", ())
    monkeypatch.setattr(providers.shutil, "which", lambda binary: None)
    assert providers.binary_for(providers.CLAUDE) == "claude"


def test_resolve_named_and_unknown():
    assert providers.resolve("claude") is providers.CLAUDE
    assert providers.resolve("kiro") is providers.KIRO
    with pytest.raises(providers.ProviderError, match="unknown provider"):
        providers.resolve("gpt")


def test_claude_is_the_default_provider():
    assert providers.DEFAULT is providers.CLAUDE


def test_rewrite_success_passes_stdin():
    with patch("subprocess.run", return_value=completed(stdout="out\n")) as run:
        assert providers.rewrite("chapter", "SYSTEM") == "out"
    assert run.call_args.kwargs["input"] == "chapter"
    assert run.call_args.kwargs["timeout"] == 1200


def test_rewrite_retries_then_succeeds():
    responses = [completed(1, "", "boom"), completed(0, "out")]
    with patch("subprocess.run", side_effect=responses), patch("time.sleep") as sleep:
        assert providers.rewrite("chapter", "SYSTEM", backoff=1) == "out"
    sleep.assert_called_once()


def test_rewrite_error_names_provider_and_surfaces_stdout():
    with patch(
        "subprocess.run", return_value=completed(1, "session limit reached", "")
    ), patch("time.sleep"):
        with pytest.raises(providers.ProviderError, match="kiro failed"):
            providers.rewrite(
                "chapter", "SYSTEM", provider=providers.KIRO, retries=1
            )


def test_rewrite_timeout_retried_then_raises():
    with patch(
        "subprocess.run", side_effect=subprocess.TimeoutExpired([], 5)
    ), patch("time.sleep"):
        with pytest.raises(providers.ProviderError, match="timed out"):
            providers.rewrite("chapter", "SYSTEM", retries=1)


def test_rewrite_missing_binary_is_clear():
    with patch("subprocess.run", side_effect=FileNotFoundError):
        with pytest.raises(providers.ProviderError, match="not found on PATH"):
            providers.rewrite("chapter", "SYSTEM")
