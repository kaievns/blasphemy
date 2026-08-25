import subprocess
from unittest.mock import patch

import pytest

from blasphemy import claude


def completed(returncode=0, stdout="rewritten", stderr=""):
    return subprocess.CompletedProcess([], returncode, stdout, stderr)


def test_build_command():
    cmd = claude.build_command("opus", "high", "SYSTEM")
    assert cmd[:2] == ["claude", "-p"]
    assert cmd[cmd.index("--model") + 1] == "opus"
    assert cmd[cmd.index("--effort") + 1] == "high"
    assert cmd[cmd.index("--system-prompt") + 1] == "SYSTEM"
    assert cmd[cmd.index("--tools") + 1] == ""
    assert "--no-session-persistence" in cmd
    assert "--bare" not in cmd


def test_build_command_no_effort():
    assert "--effort" not in claude.build_command("opus", None, "SYSTEM")


def test_rewrite_success():
    with patch("subprocess.run", return_value=completed(stdout="out\n")) as run:
        assert claude.rewrite("chapter", "SYSTEM") == "out"
    assert run.call_args.kwargs["input"] == "chapter"
    assert run.call_args.kwargs["timeout"] == 1200


def test_rewrite_retries_then_succeeds():
    responses = [completed(1, "", "boom"), completed(0, "out")]
    with patch("subprocess.run", side_effect=responses), patch("time.sleep") as sleep:
        assert claude.rewrite("chapter", "SYSTEM", backoff=1) == "out"
    sleep.assert_called_once()


def test_rewrite_error_surfaces_stdout_message():
    with patch(
        "subprocess.run", return_value=completed(1, "session limit reached", "")
    ), patch("time.sleep"):
        with pytest.raises(claude.ClaudeError, match="session limit reached"):
            claude.rewrite("chapter", "SYSTEM", retries=1)


def test_rewrite_empty_output_is_failure():
    with patch("subprocess.run", return_value=completed(stdout="  ")), patch("time.sleep"):
        with pytest.raises(claude.ClaudeError, match="empty output"):
            claude.rewrite("chapter", "SYSTEM", retries=1)


def test_rewrite_timeout_retried_then_raises():
    with patch(
        "subprocess.run", side_effect=subprocess.TimeoutExpired([], 5)
    ), patch("time.sleep"):
        with pytest.raises(claude.ClaudeError, match="timed out"):
            claude.rewrite("chapter", "SYSTEM", retries=1)
