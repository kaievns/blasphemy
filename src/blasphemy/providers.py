import os
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

# agent CLIs commonly install outside the PATH of cron/make/nohup shells
FALLBACK_DIRS = ("~/.local/bin", "/usr/local/bin", "/opt/homebrew/bin")


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

KIRO = Provider(
    name="kiro",
    binary="kiro",
    default_model="",
    base_args=("chat", "--no-interactive"),
    model_flag="--model",
)

REGISTRY = {provider.name: provider for provider in (CLAUDE, KIRO)}
ORDER = ("claude", "kiro")


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


def resolve(name: str = "auto") -> Provider:
    if name != "auto":
        if name not in REGISTRY:
            raise ProviderError(f"unknown provider: {name}")
        return REGISTRY[name]
    for candidate in ORDER:
        if available(REGISTRY[candidate]):
            return REGISTRY[candidate]
    raise ProviderError(f"no agent CLI found on PATH (looked for: {', '.join(ORDER)})")


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
    last_error = ""
    for attempt in range(retries + 1):
        if attempt:
            time.sleep(backoff * attempt)
        try:
            proc = subprocess.run(
                cmd, input=stdin, capture_output=True, text=True, timeout=timeout
            )
        except FileNotFoundError:
            raise ProviderError(f"{cmd[0]} not found on PATH") from None
        except subprocess.TimeoutExpired:
            last_error = f"timed out after {timeout}s"
            continue
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout.strip()
        last_error = (
            proc.stderr.strip() or proc.stdout.strip()[:200] or "empty output"
        )
    raise ProviderError(
        f"{provider.name} failed after {retries + 1} attempts: {last_error}"
    )
