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

Key flags: `--provider` (`auto`|`claude`|`kiro`), `--model` (provider-specific,
defaults per provider), `-o` output path, `--prompt` alternate body-prompt file,
`--min-words` skip threshold (default 200), `--skip`/`--only` chapter indices,
`--effort` (claude only), `--timeout` seconds per call (default 1200),
`--no-primer`, `--force` to ignore cached rewrites.

Progress prints per chapter; interrupted runs resume from the `.blasphemy/`
cache, so re-running after a quota exhaustion only redoes what is missing.

## Providers

The rewrite calls shell out to an agent CLI. `--provider auto` picks the first
one installed, in the order `claude`, `kiro`.

Binaries are located via `PATH`, then `~/.local/bin`, `/usr/local/bin`,
`/opt/homebrew/bin` — cron, `make`, and `nohup` shells often lack the login
PATH. Override explicitly with `BLASPHEMY_CLAUDE_BIN` / `BLASPHEMY_KIRO_BIN`.

Never pass claude's `--bare`: it forces API-key auth and bypasses the
subscription.

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
