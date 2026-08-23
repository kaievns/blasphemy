# Usage

## Setup

```sh
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
```

## Run

```sh
.venv/bin/blasphemy book.epub                 # → book.optimised.epub
.venv/bin/blasphemy book.epub --list          # inspect chapters, no rewriting
.venv/bin/blasphemy book.epub --model sonnet  # cheaper/faster model
.venv/bin/blasphemy book.epub --force         # ignore cached rewrites
```

Key flags: `-o` output path, `--prompt` alternate prompt file, `--min-words`
skip threshold (default 200), `--effort` claude effort level, `--timeout`
seconds per chapter (default 1200).

Requires the `claude` CLI logged in (subscription auth). Progress prints per
chapter; interrupted runs resume from the `.blasphemy/` cache.

## Tests

```sh
.venv/bin/pytest
```

## Iterating on prompts

Edit `src/blasphemy/prompts/rewrite.md` (or pass `--prompt`), then re-run with
`--force`. Inspect `.blasphemy/<book>/NNN.src.md` vs `NNN.md` to judge
rewrites without opening the epub. Log changes in `specs/prompt.md`.
