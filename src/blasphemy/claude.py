import subprocess
import time


class ClaudeError(Exception):
    pass


def build_command(
    model: str, effort: str | None, system_prompt: str
) -> list[str]:
    cmd = [
        "claude",
        "-p",
        "--output-format",
        "text",
        "--no-session-persistence",
        "--tools",
        "",
        "--model",
        model,
        "--system-prompt",
        system_prompt,
    ]
    if effort:
        cmd += ["--effort", effort]
    return cmd


def rewrite(
    chapter_md: str,
    system_prompt: str,
    model: str = "opus",
    effort: str | None = None,
    timeout: int = 1200,
    retries: int = 2,
    backoff: float = 10.0,
) -> str:
    cmd = build_command(model, effort, system_prompt)
    last_error = ""
    for attempt in range(retries + 1):
        if attempt:
            time.sleep(backoff * attempt)
        try:
            proc = subprocess.run(
                cmd,
                input=chapter_md,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            last_error = f"timed out after {timeout}s"
            continue
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout.strip()
        last_error = proc.stderr.strip() or "empty output"
    raise ClaudeError(f"claude failed after {retries + 1} attempts: {last_error}")
