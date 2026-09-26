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
make rebuild BOOK=book.epub                       # reassemble from cache, no agent calls
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
`--effort` (kiro defaults to `high`), `--timeout` seconds per call (default 2400),
`--no-primer`, `--force` to ignore cached rewrites.

Progress prints per chapter; interrupted runs resume from the `.blasphemy/`
cache, so re-running after a quota exhaustion only redoes what is missing.

`--rebuild` reassembles the epub from cached rewrites and never calls an
agent: it is the way to pick up a pipeline fix (markup restoration, styling)
on an already-processed book without paying for the rewrites again. Uncached
chapters keep their original text and are reported as failed, and the cache
is never evicted in this mode.

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

Output is read from `--output-format stream-json --verbose`, not `text`.
When a reply hits Claude Code's output-token limit, the CLI injects "Output
token limit hit. Resume directly…" and the model continues in a second
message; the text/json `result` holds only that last message. Long chapters
hit this often: 7 of 10 HLW ch9 bodies (17,942 words) came back as a tail
fragment in text mode (2026-09-26, `CLAUDE_CODE_MAX_OUTPUT_TOKENS=64000`
did not prevent it). `providers.claude_reply` joins the text of every
assistant message; the continuation often repeats the last partial line, so
the longest line-aligned tail it repeats is dropped at the seam. An error
result counts as empty output and is retried.

### kiro

`kiro-cli chat --no-interactive` (the bare `kiro` command opens the IDE).
Install with `curl -fsSL https://cli.kiro.dev/install | bash`. Defaults to
`claude-fable-5.1` at `high` effort; override with `--model` / `--effort`,
list valid ids with `kiro-cli chat --list-models` (which flags fable as an
internal preview). Constraints that shape the integration, verified against
kiro-cli 2.19:

- **Auth is the `kiro-cli login` session**, not an API key. The CLI keeps its
  own token store, separate from the Kiro IDE's — a logged-in IDE does not
  cover the CLI. Check with `kiro-cli whoami`; when the session expires,
  re-login with `kiro-cli login --use-device-flow`. Logged out, a headless
  call blocks trying to open a browser instead of failing fast.
- **The default profile applies.** No `--agent` is passed, so the profile
  named by `kiro-cli settings chat.defaultAgent` handles every call.
- **No system-prompt flag.** The system prompt is prepended to stdin.
- **stdin is read only when no prompt argument is passed** — so nothing is ever
  passed positionally, and chapters travel on stdin.
- **No way to disable tools.** `--trust-tools=` trusts none, so an attempted
  tool call fails loudly rather than being silently approved. `--trust-all-tools`
  is deliberately never used.
- **No plain-text output mode — stdout is a rendered picture.** The terminal
  renderer consumes markdown structure (``` fences and inline backticks never
  reach stdout) and adds ANSI styling, a `> ` reply marker, and sometimes a
  `Credits: … Time: …` footer. So the response is not taken from stdout: the
  CLI persists each chat verbatim in a local sqlite store
  (`~/Library/Application Support/kiro-cli/data.sqlite3`, `conversations_v2`),
  and after every call the faithful markdown is fetched from there, matched
  by exact payload, then the session is deleted to keep the store tidy.
  Sanitized stdout remains as a fallback: if a kiro update ever changes the
  store schema, runs keep working but code-bearing chapters will show the
  `code block(s) left fenced` note — that's the signal to revisit this
  integration.
- **Pin 2.x.** Kiro CLI 3.0 drops the non-TUI path that headless mode uses.

## Quota exhaustion

Long runs outlast a quota window. Failed chapters keep their original text and
the run continues, so the simplest recovery is to re-run the same command once
quota returns — cached chapters are skipped. Drop `--force` for the recovery
run: with it every chapter is rewritten and billed again. A chapter whose
apparatus call failed keeps its body in `NNN.body.md` and reruns only the
apparatus. `--check-providers` (or `make check`) is a cheap way to see
whether a CLI is usable at all.

## Tests

```sh
make test           # or: .venv/bin/pytest -q
```

## Iterating on prompts

Edit `src/blasphemy/prompts/body.md` (or pass `--prompt`), then re-run with
`--force`. Inspect `.blasphemy/<book>/NNN.src.md` vs `NNN.md` to judge rewrites
without opening the epub. `NNN.src.md` is rewritten on every run, so after a
converter change it no longer shows what a cached `NNN.md` was made from. Log
changes in `specs/prompt.md`.
