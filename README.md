# blasphemy

Rewrites an epub chapter by chapter with an agentic CLI, then reassembles an
optimised epub: compressed prose, preserved facts and terminology, plus study
apparatus (orientation, what to watch for, key points, self-check questions).

Built for one reader profile — Asperger-type autistic + medicated ADHD, senior
engineer — on the evidence in [`specs/reader-profile.md`](specs/reader-profile.md).
Retune the prompts in `src/blasphemy/prompts/` for anyone else.

## Requirements

- Python 3.12+
- One agent CLI, logged in: [Claude Code](https://claude.com/claude-code)
  (`claude`) or [Kiro](https://kiro.dev) (`kiro`)

## Quickstart

```sh
make setup                          # venv + install
make check                          # which agent CLIs are usable
make list BOOK=book.epub            # inspect chapters, no rewriting
make run  BOOK=book.epub            # → book.optimised.epub
make run  BOOK=book.epub PROVIDER=kiro ARGS='--force'
make test
```

Or call it directly: `.venv/bin/blasphemy book.epub --provider claude`.
Flags: [`docs/usage.md`](docs/usage.md).

## How it works

1. Walk the epub spine; skip front matter, nav, and reference pages.
2. One cheap pass builds a **book primer** (arc, chapter scopes, canonical
   terminology) that is prepended to every chapter call.
3. Per chapter, two calls: a **body pass** (re-express at 55–70% length) and an
   **apparatus pass** (study scaffolding under a word budget).
4. Assemble deterministically, then rebuild the epub with original styling,
   code markup, images, anchors, and metadata intact.

Fragile markup (MathML, inline SVG, link anchors) travels through the rewrite as
opaque tokens and is re-injected afterwards, so it cannot be paraphrased away.
Every chapter's input and output is cached under `.blasphemy/`, making runs
resumable and prompt changes diffable. Design notes live in [`specs/`](specs/),
operational notes in [`docs/`](docs/).

## License

[CC BY-SA 4.0](LICENSE) — use it, change it, share it; keep the attribution and
license the result the same way.
