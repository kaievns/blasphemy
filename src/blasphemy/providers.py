import json
import os
import re
import shutil
import sqlite3
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

# agent CLIs commonly install outside the PATH of cron/make/nohup shells
FALLBACK_DIRS = ("~/.local/bin", "/usr/local/bin", "/opt/homebrew/bin")

ANSI = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
KIRO_FOOTER = re.compile(r"^[\s▸>]*Credits:.*?Time:.*$", re.M)
KIRO_MARKER = re.compile(r"\A> ")  # reply marker; later `> ` are blockquotes
CONTINUATION_OVERLAP_MAX = 4000


def strip_chrome(text: str) -> str:
    # kiro renders markdown with ANSI, opens the reply with a `> ` marker,
    # and may append a credits/time footer
    text = KIRO_FOOTER.sub("", ANSI.sub("", text)).strip()
    return KIRO_MARKER.sub("", text, count=1).strip()


class ProviderError(Exception):
    pass


def join_continuation(first: str, second: str) -> str:
    """Join a reply split mid-stream; the continuation often restarts the
    last partial line, so drop the longest line-aligned tail it repeats."""
    tail = max(len(first) - CONTINUATION_OVERLAP_MAX, 0)
    starts = [0] if tail == 0 else []
    starts += [i + 1 for i in range(tail, len(first)) if first[i] == "\n"]
    for start in starts:
        if second.startswith(first[start:]):
            return first[:start] + second
    return first + second


def claude_reply(stdout: str) -> str:
    """The whole reply from `claude -p --output-format stream-json`.

    Claude Code continues a reply that hits its output-token limit in a new
    message and its `result` keeps only the last one (docs/usage.md#claude).
    """
    texts: dict[str, list[str]] = {}
    parsed = False
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if not isinstance(event, dict):
            continue
        parsed = True
        if event.get("type") == "result" and event.get("is_error"):
            return ""
        if event.get("type") != "assistant":
            continue
        message = event.get("message") or {}
        blocks = texts.setdefault(message.get("id") or str(len(texts)), [])
        blocks += [
            block.get("text", "")
            for block in message.get("content") or []
            if block.get("type") == "text"
        ]
    if not parsed:
        return stdout.strip()
    reply = ""
    for blocks in texts.values():
        text = "".join(blocks)
        if text:
            reply = join_continuation(reply, text) if reply else text
    return reply.strip()


@dataclass(frozen=True)
class Provider:
    name: str
    binary: str
    default_model: str
    default_effort: str | None = None
    base_args: tuple[str, ...] = ()
    model_flag: str | None = None
    effort_flag: str | None = None
    system_flag: str | None = None  # None: system prompt is folded into stdin
    prompt_as_arg: bool = False  # True: user text is the last argv, not stdin
    env: tuple[tuple[str, str], ...] = ()
    sanitize: Callable[[str], str] = field(default=str.strip)
    # fetch(payload) returns the faithful response from outside stdout, or
    # None to fall back to sanitized stdout
    fetch: Callable[[str], str | None] | None = None


CLAUDE = Provider(
    name="claude",
    binary="claude",
    default_model="fable",
    base_args=(
        "-p",
        "--output-format",
        "stream-json",
        "--verbose",
        "--no-session-persistence",
        "--tools",
        "",
    ),
    model_flag="--model",
    effort_flag="--effort",
    system_flag="--system-prompt",
    sanitize=claude_reply,
)

# kiro-cli renders markdown for the terminal even when piped: ``` fences and
# inline backticks are consumed before stdout and cannot be recovered from it.
# The CLI does persist every chat verbatim in a local sqlite store, so the
# faithful response is fetched from there after each call; rendered stdout is
# only a fallback (and flagged downstream by the pre count-mismatch note).
KIRO_STORE_PATHS = (
    "~/Library/Application Support/kiro-cli/data.sqlite3",  # macOS
    "~/.local/share/kiro-cli/data.sqlite3",  # linux
)
KIRO_STORE_SCAN = 50  # newest conversations checked per fetch


def _kiro_forget(session_id: str) -> None:
    # keep the store from accumulating one session per rewritten chapter
    try:
        subprocess.run(
            [binary_for(KIRO), "chat", "-d", session_id],
            capture_output=True, timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        pass  # cleanup is best-effort; a stale session is harmless


def kiro_fetch(payload: str) -> str | None:
    """Raw assistant markdown for `payload` from kiro-cli's session store."""
    for candidate in KIRO_STORE_PATHS:
        store = Path(candidate).expanduser()
        if store.is_file():
            break
    else:
        return None
    try:
        db = sqlite3.connect(f"file:{store}?mode=ro", uri=True)
        try:
            rows = db.execute(
                "SELECT value FROM conversations_v2 WHERE key = ?"
                " ORDER BY rowid DESC LIMIT ?",
                (os.getcwd(), KIRO_STORE_SCAN),
            ).fetchall()
        finally:
            db.close()
    except sqlite3.Error:
        return None
    for (raw,) in rows:
        try:
            conversation = json.loads(raw)
        except ValueError:
            continue
        for entry in conversation.get("history") or []:
            user = (entry.get("user") or {}).get("content") or {}
            prompt = (user.get("Prompt") or {}).get("prompt") or ""
            if prompt.strip() != payload.strip():
                continue
            response = (entry.get("assistant") or {}).get("Response") or {}
            content = (response.get("content") or "").strip()
            if content:
                session_id = conversation.get("conversation_id")
                if session_id:
                    _kiro_forget(session_id)
                return content
    return None


# kiro-cli 2.x (verified on 2.19): `kiro` opens the IDE. No system-prompt,
# tools, or output-format flags — the system prompt rides on stdin, and stdin
# is only read when no positional prompt is given. `--trust-tools=` trusts
# nothing, so an attempted tool call aborts loudly instead of being
# auto-approved. No `--agent`: the profile configured as chat.defaultAgent
# applies. Auth is the `kiro-cli login` session (its token store is separate
# from the Kiro IDE's) — check with `kiro-cli whoami`; logged out, a headless
# call blocks on a browser login instead of failing fast.
KIRO = Provider(
    name="kiro",
    binary="kiro-cli",
    default_model="claude-fable-5.1",
    default_effort="high",
    base_args=("chat", "--no-interactive", "--trust-tools=", "--wrap", "never"),
    model_flag="--model",
    effort_flag="--effort",
    env=(("NO_COLOR", "1"), ("KIRO_ASCII_MODE", "1")),
    sanitize=strip_chrome,
    fetch=kiro_fetch,
)

REGISTRY = {provider.name: provider for provider in (CLAUDE, KIRO)}
DEFAULT = CLAUDE


def binary_for(provider: Provider) -> str:
    override = os.environ.get(f"BLASPHEMY_{provider.name.upper()}_BIN")
    if override:
        return override
    on_path = shutil.which(provider.binary)
    if on_path:
        return on_path
    for directory in FALLBACK_DIRS:
        candidate = Path(directory).expanduser() / provider.binary
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return provider.binary


def available(provider: Provider) -> bool:
    return shutil.which(binary_for(provider)) is not None


def resolve(name: str) -> Provider:
    if name not in REGISTRY:
        raise ProviderError(f"unknown provider: {name}")
    return REGISTRY[name]


def build_call(
    provider: Provider,
    user_text: str,
    system_prompt: str,
    model: str | None = None,
    effort: str | None = None,
) -> tuple[list[str], str | None]:
    cmd = [binary_for(provider), *provider.base_args]
    model = model or provider.default_model
    if model and provider.model_flag:
        cmd += [provider.model_flag, model]
    effort = effort or provider.default_effort
    if effort and provider.effort_flag:
        cmd += [provider.effort_flag, effort]

    if provider.system_flag:
        cmd += [provider.system_flag, system_prompt]
        payload = user_text
    else:
        payload = f"{system_prompt}\n\n---\n\n{user_text}"

    if provider.prompt_as_arg:
        return cmd + [payload], None
    return cmd, payload


def rewrite(
    user_text: str,
    system_prompt: str,
    provider: Provider = CLAUDE,
    model: str | None = None,
    effort: str | None = None,
    timeout: int = 1200,
    retries: int = 2,
    backoff: float = 30.0,
) -> str:
    cmd, stdin = build_call(provider, user_text, system_prompt, model, effort)
    env = {**os.environ, **dict(provider.env)} if provider.env else None
    last_error = ""
    for attempt in range(retries + 1):
        if attempt:
            time.sleep(backoff * attempt)
        try:
            proc = subprocess.run(
                cmd,
                input=stdin,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env,
            )
        except FileNotFoundError:
            raise ProviderError(f"{cmd[0]} not found on PATH") from None
        except subprocess.TimeoutExpired:
            last_error = f"timed out after {timeout}s"
            continue
        output = provider.sanitize(proc.stdout)
        if proc.returncode == 0:
            if provider.fetch:
                fetched = provider.fetch(stdin if stdin is not None else cmd[-1])
                if fetched:
                    return fetched
            if output:
                return output
        last_error = (
            strip_chrome(proc.stderr) or output[:200] or "empty output"
        )
    raise ProviderError(
        f"{provider.name} failed after {retries + 1} attempts: {last_error}"
    )
