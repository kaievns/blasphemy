import json
import os
import sqlite3
import subprocess
import time
from unittest.mock import patch

import pytest

from blasphemy import providers


def conversation(prompt, content, session="sess-1"):
    return {
        "conversation_id": session,
        "history": [{
            "user": {"content": {"Prompt": {"prompt": prompt}}},
            "assistant": {"Response": {"message_id": "m", "content": content}},
        }],
    }


def fake_store(tmp_path, conversations, key=None):
    db_path = tmp_path / "data.sqlite3"
    db = sqlite3.connect(db_path)
    db.execute("CREATE TABLE conversations_v2 (key TEXT, value TEXT)")
    for convo in conversations:
        db.execute(
            "INSERT INTO conversations_v2 VALUES (?, ?)",
            (key or os.getcwd(), json.dumps(convo)),
        )
    db.commit()
    db.close()
    return str(db_path)


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
    # Opus 5.5 at xhigh effort unless the caller overrides
    assert cmd[cmd.index("--model") + 1] == "claude-opus-5.5"
    assert cmd[cmd.index("--effort") + 1] == "xhigh"
    # no --agent: the default profile configured in kiro-cli applies
    assert "--agent" not in cmd
    # kiro has no system-prompt flag, and only reads stdin with no argv prompt
    assert stdin.startswith("SYSTEM") and stdin.endswith("CHAPTER")
    assert cmd[-1] != stdin


def test_kiro_defaults_overridable():
    cmd, _ = providers.build_call(
        providers.KIRO, "CHAPTER", "SYSTEM", model="claude-sonnet-5", effort="low"
    )
    assert cmd[cmd.index("--model") + 1] == "claude-sonnet-5"
    assert cmd[cmd.index("--effort") + 1] == "low"


def test_claude_defaults_to_opus_at_xhigh_effort():
    cmd, _ = providers.build_call(providers.CLAUDE, "CHAPTER", "SYSTEM")
    assert cmd[cmd.index("--model") + 1] == "claude-opus-5-5"
    assert cmd[cmd.index("--effort") + 1] == "xhigh"


def test_effort_omitted_when_provider_lacks_flag():
    provider = providers.Provider(name="x", binary="x", default_model="")
    cmd, _ = providers.build_call(provider, "CHAPTER", "SYSTEM", effort="high")
    assert "--effort" not in cmd


def test_strip_chrome_removes_ansi_and_credits_footer():
    raw = "\x1b[1mAnswer\x1b[0m text\n\n▸ Credits: 0.39 • Time: 22s\n"
    assert providers.strip_chrome(raw) == "Answer text"


def test_strip_chrome_drops_reply_marker_but_keeps_blockquotes():
    # observed kiro-cli 2.19 shape: ANSI-wrapped `> ` opens the reply
    raw = "\x1b[m> \x1b[0malpha\x1b[0m\x1b[0m\nline two\n\n> a real quote"
    assert providers.strip_chrome(raw) == "alpha\nline two\n\n> a real quote"


def test_kiro_output_is_sanitised_and_env_applied(monkeypatch):
    monkeypatch.setattr(providers, "KIRO_STORE_PATHS", ("/nonexistent",))
    noisy = completed(stdout="\x1b[32mclean\x1b[0m\n▸ Credits: 0.4 • Time: 3s\n")
    with patch("blasphemy.providers.run_process", return_value=noisy) as run:
        assert providers.rewrite(
            "chapter", "SYSTEM", provider=providers.KIRO
        ) == "clean"
    env = run.call_args.kwargs["env"]
    assert env["NO_COLOR"] == "1" and env["KIRO_ASCII_MODE"] == "1"


def test_kiro_fetch_returns_raw_markdown_and_forgets_session(tmp_path, monkeypatch):
    store = fake_store(tmp_path, [
        conversation("other payload", "wrong answer", session="sess-a"),
        conversation("the payload", "Use `Vec<i32>` — **fast**.", session="sess-b"),
    ])
    monkeypatch.setattr(providers, "KIRO_STORE_PATHS", (store,))
    forgotten = []
    monkeypatch.setattr(providers, "_kiro_forget", forgotten.append)
    assert providers.kiro_fetch("the payload") == "Use `Vec<i32>` — **fast**."
    assert forgotten == ["sess-b"]


def test_kiro_fetch_without_match_or_store_returns_none(tmp_path, monkeypatch):
    store = fake_store(tmp_path, [conversation("something else", "answer")])
    monkeypatch.setattr(providers, "KIRO_STORE_PATHS", (store,))
    assert providers.kiro_fetch("the payload") is None
    monkeypatch.setattr(providers, "KIRO_STORE_PATHS", ("/nonexistent",))
    assert providers.kiro_fetch("the payload") is None


def test_kiro_fetch_ignores_other_workdirs(tmp_path, monkeypatch):
    store = fake_store(
        tmp_path, [conversation("the payload", "answer")], key="/elsewhere"
    )
    monkeypatch.setattr(providers, "KIRO_STORE_PATHS", (store,))
    assert providers.kiro_fetch("the payload") is None


def test_rewrite_prefers_fetched_response_over_rendered_stdout():
    seen = []

    def fetch(payload):
        seen.append(payload)
        return "raw with `backticks` and\n\n```\nfences\n```"

    provider = providers.Provider(name="x", binary="x", default_model="", fetch=fetch)
    mangled = completed(stdout="raw with backticks and\nfences")
    with patch("blasphemy.providers.run_process", return_value=mangled):
        out = providers.rewrite("CHAPTER", "SYSTEM", provider=provider)
    assert out == "raw with `backticks` and\n\n```\nfences\n```"
    # fetch is matched against the full payload the model actually received
    assert seen[0].startswith("SYSTEM") and seen[0].endswith("CHAPTER")


def test_rewrite_falls_back_to_stdout_when_fetch_misses():
    provider = providers.Provider(
        name="x", binary="x", default_model="", fetch=lambda payload: None
    )
    with patch("blasphemy.providers.run_process", return_value=completed(stdout="rendered\n")):
        assert providers.rewrite("CHAPTER", "SYSTEM", provider=provider) == "rendered"


def test_kiro_provider_wires_store_fetch():
    assert providers.KIRO.fetch is providers.kiro_fetch


def test_claude_run_inherits_env_unchanged():
    with patch("blasphemy.providers.run_process", return_value=completed()) as run:
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
    with patch("blasphemy.providers.run_process", return_value=completed(stdout="out\n")) as run:
        assert providers.rewrite("chapter", "SYSTEM") == "out"
    assert run.call_args.kwargs["input"] == "chapter"
    assert run.call_args.kwargs["timeout"] == 1200


def test_rewrite_retries_then_succeeds():
    responses = [completed(1, "", "boom"), completed(0, "out")]
    with patch("blasphemy.providers.run_process", side_effect=responses), patch("time.sleep") as sleep:
        assert providers.rewrite("chapter", "SYSTEM", backoff=1) == "out"
    sleep.assert_called_once()


def test_rewrite_error_names_provider_and_surfaces_stdout():
    with patch(
        "blasphemy.providers.run_process", return_value=completed(1, "session limit reached", "")
    ), patch("time.sleep"):
        with pytest.raises(providers.ProviderError, match="kiro failed"):
            providers.rewrite(
                "chapter", "SYSTEM", provider=providers.KIRO, retries=1
            )


def test_rewrite_timeout_retried_then_raises():
    with patch(
        "blasphemy.providers.run_process", side_effect=subprocess.TimeoutExpired([], 5)
    ), patch("time.sleep"):
        with pytest.raises(providers.ProviderError, match="timed out"):
            providers.rewrite("chapter", "SYSTEM", retries=1)


def test_rewrite_missing_binary_is_clear():
    with patch("blasphemy.providers.run_process", side_effect=FileNotFoundError):
        with pytest.raises(providers.ProviderError, match="not found on PATH"):
            providers.rewrite("chapter", "SYSTEM")


def stream(*messages, error=False):
    events = [{"type": "system", "subtype": "init"}]
    for n, text in enumerate(messages):
        events.append({"type": "assistant", "message": {"id": f"m{n}", "content": [{"type": "thinking", "thinking": "..."}]}})
        events.append({"type": "assistant", "message": {"id": f"m{n}", "content": [{"type": "text", "text": text}]}})
        if n + 1 < len(messages):
            events.append({"type": "user", "message": {"content": [{"type": "text", "text": "Output token limit hit. Resume directly"}]}})
    events.append({"type": "result", "subtype": "success", "is_error": error, "result": messages[-1] if messages else ""})
    return "\n".join(json.dumps(e) for e in events)


def test_claude_call_streams_json():
    cmd, _ = providers.build_call(providers.CLAUDE, "CHAPTER", "SYSTEM")
    assert cmd[cmd.index("--output-format") + 1] == "stream-json"
    assert "--verbose" in cmd


def test_claude_reply_keeps_every_continued_message():
    first = "# Title\n\n| a | b |\n| --- | --- |\n| 1 | 2 |\n| "
    second = "| 3 | 4 |\n\nThe end."
    assert providers.claude_reply(stream(first, second)) == (
        "# Title\n\n| a | b |\n| --- | --- |\n| 1 | 2 |\n| 3 | 4 |\n\nThe end."
    )


def test_join_continuation_drops_a_restarted_code_line():
    first = "Bind it with\n\n```\n# ip address add <var>address/subnet</var>"
    second = "```\n# ip address add <var>address/subnet</var> dev <var>interface</var>\n```"
    assert providers.join_continuation(first, second) == (
        "Bind it with\n\n```\n# ip address add <var>address/subnet</var> dev <var>interface</var>\n```"
    )


def test_join_continuation_plain_when_nothing_repeats():
    assert providers.join_continuation("ends mid", "-word goes on") == "ends mid-word goes on"
    assert providers.join_continuation("para one.\n\n", "para two.") == "para one.\n\npara two."


def test_claude_reply_single_message_ignores_thinking():
    assert providers.claude_reply(stream("# T\n\nbody")) == "# T\n\nbody"


def test_claude_reply_error_result_is_empty():
    assert providers.claude_reply(stream("partial", error=True)) == ""


def test_claude_reply_passes_plain_text_through():
    assert providers.claude_reply("plain reply\n") == "plain reply"


def test_rewrite_returns_the_joined_stream_reply():
    out = stream("# T\n\nfirst half, ", "second half.")
    with patch("blasphemy.providers.run_process", return_value=completed(stdout=out)):
        assert providers.rewrite("chapter", "SYSTEM") == "# T\n\nfirst half, second half."


def test_run_process_passes_stdin_and_captures_output():
    proc = providers.run_process(["cat"], input="chapter", timeout=10)
    assert (proc.returncode, proc.stdout) == (0, "chapter")


def test_run_process_timeout_kills_the_launched_binary_too(tmp_path):
    launcher = tmp_path / "launcher"
    launcher.write_text('#!/bin/sh\nsleep 60 &\necho $! > "$1"\nwait\n')
    launcher.chmod(0o755)
    pidfile = tmp_path / "pid"
    with pytest.raises(subprocess.TimeoutExpired):
        providers.run_process([str(launcher), str(pidfile)], input=None, timeout=1)
    child = int(pidfile.read_text())
    for _ in range(50):
        try:
            os.kill(child, 0)
        except ProcessLookupError:
            return
        time.sleep(0.1)
    pytest.fail("the launched binary outlived the timeout")
