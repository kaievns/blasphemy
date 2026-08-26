# Usage

## Setup

```sh
make setup          # venv + editable install
make check          # which agent CLIs are usable
make test
```

## Run

```sh
make run  BOOK=book.epub                          # → book.optimised.epub
make run  BOOK=book.epub PROVIDER=kiro
make run  BOOK=book.epub ARGS='--force --only 8'
make list BOOK=book.epub                          # inspect chapters, no rewriting
```

Equivalent direct calls:

```sh
.venv/bin/blasphemy book.epub
.venv/bin/blasphemy book.epub --provider claude --model opus
.venv/bin/blasphemy book.epub --list
```

Key flags: `--provider` (`claude` default, or `kiro`), `--model` (provider-specific,
defaults per provider), `-o` output path, `--prompt` alternate body-prompt file,
`--min-words` skip threshold (default 200), `--skip`/`--only` chapter indices,
`--effort` (claude only), `--timeout` seconds per call (default 1200),
`--no-primer`, `--force` to ignore cached rewrites.

Progress prints per chapter; interrupted runs resume from the `.blasphemy/`
cache, so re-running after a quota exhaustion only redoes what is missing.

## Providers

The rewrite calls shell out to an agent CLI: `claude` unless you pass
`--provider kiro`. If the chosen binary is missing, the run stops immediately
with the binary name and the alternative, rather than failing mid-book.

Binaries are located via `PATH`, then `~/.local/bin`, `/usr/local/bin`,
`/opt/homebrew/bin` — cron, `make`, and `nohup` shells often lack the login
PATH. Override explicitly with `BLASPHEMY_CLAUDE_BIN` / `BLASPHEMY_KIRO_BIN`.

### claude (default)

`claude -p` with the system prompt on `--system-prompt`, content on stdin,
tools disabled. Models: `fable` (default), `opus`, `sonnet`, `haiku`.
Never pass `--bare`: it forces API-key auth and bypasses the subscription.

### kiro

`kiro-cli chat --no-interactive` (the bare `kiro` command opens the IDE).
Install with `curl -fsSL https://cli.kiro.dev/install | bash`. Constraints that
shape the integration:

- **Auth:** headless requires `export KIRO_API_KEY=ksk_…`, available on paid
  plans only. `make check` warns when it is unset.
- **No system-prompt flag.** The system prompt is prepended to stdin.
- **stdin is read only when no prompt argument is passed** — so nothing is ever
  passed positionally, and chapters travel on stdin.
- **No way to disable tools.** `--trust-tools=` trusts none, so an attempted
  tool call fails loudly rather than being silently approved. `--trust-all-tools`
  is deliberately never used.
- **No plain-text output mode.** Responses arrive with ANSI styling and a
  `Credits: … Time: …` footer, both stripped before use.
- **Pin 2.x.** Kiro CLI 3.0 drops the non-TUI path that headless mode uses.
- `--model` is undocumented on 2.x but accepted; omitted unless you pass
  `--model`, in which case `kiro-cli settings chat.defaultModel` applies.
  List valid ids with `kiro-cli chat --list-models --format json`.

## Quota exhaustion

Long runs outlast a quota window. Failed chapters keep their original text and
the run continues, so the simplest recovery is to re-run the same command once
quota returns — cached chapters are skipped. `--check-providers` (or
`make check`) is a cheap way to see whether a CLI is usable at all.

## Tests

```sh
make test           # or: .venv/bin/pytest -q
```

## Iterating on prompts

Edit `src/blasphemy/prompts/body.md` (or pass `--prompt`), then re-run with
`--force`. Inspect `.blasphemy/<book>/NNN.src.md` vs `NNN.md` to judge rewrites
without opening the epub. Log changes in `specs/prompt.md`.
