import os
import re
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

# agent CLIs commonly install outside the PATH of cron/make/nohup shells
FALLBACK_DIRS = ("~/.local/bin", "/usr/local/bin", "/opt/homebrew/bin")

ANSI = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
KIRO_FOOTER = re.compile(r"^[\s▸>]*Credits:.*?Time:.*$", re.M)


def strip_chrome(text: str) -> str:
    # kiro renders markdown with ANSI and appends a credits/time footer
    return KIRO_FOOTER.sub("", ANSI.sub("", text)).strip()


class ProviderError(Exception):
    pass


@dataclass(frozen=True)
class Provider:
    name: str
    binary: str
    default_model: str
    base_args: tuple[str, ...] = ()
    model_flag: str | None = None
    effort_flag: str | None = None
    system_flag: str | None = None  # None: system prompt is folded into stdin
    prompt_as_arg: bool = False  # True: user text is the last argv, not stdin
    env: tuple[tuple[str, str], ...] = ()
    auth_env: str | None = None
    sanitize: Callable[[str], str] = field(default=str.strip)


CLAUDE = Provider(
    name="claude",
    binary="claude",
    default_model="fable",
    base_args=(
        "-p",
        "--output-format",
        "text",
        "--no-session-persistence",
        "--tools",
        "",
    ),
    model_flag="--model",
    effort_flag="--effort",
    system_flag="--system-prompt",
)

# kiro-cli 2.x: `kiro` opens the IDE. No system-prompt, tools, or output-format
# flags — the system prompt rides on stdin, and stdin is only read when no
# positional prompt is given. `--trust-tools=` trusts nothing, so an attempted
# tool call aborts loudly instead of being auto-approved.
KIRO = Provider(
    name="kiro",
    binary="kiro-cli",
    default_model="",  # defer to `kiro-cli settings chat.defaultModel`
    base_args=("chat", "--no-interactive", "--trust-tools=", "--wrap", "never"),
    model_flag="--model",
    effort_flag="--effort",
    env=(("NO_COLOR", "1"), ("KIRO_ASCII_MODE", "1")),
    auth_env="KIRO_API_KEY",
    sanitize=strip_chrome,
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
        if proc.returncode == 0 and output:
            return output
        last_error = (
            strip_chrome(proc.stderr) or output[:200] or "empty output"
        )
    raise ProviderError(
        f"{provider.name} failed after {retries + 1} attempts: {last_error}"
    )
