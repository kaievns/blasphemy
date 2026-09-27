# blasphemy

Rewrites an epub chapter by chapter with an agentic CLI, then reassembles an
optimised epub: each chapter restructured by depth (the answer, then the
shape of the problem, then the detail) with facts, terminology and code
preserved.

Built for one reader profile — Asperger-type autistic + medicated ADHD, senior
engineer — on the evidence in [`specs/reader-profile.md`](specs/reader-profile.md).
Retune the prompts in `src/blasphemy/prompts/` for anyone else.

## Requirements

- Python 3.12+
- [Claude Code](https://claude.com/claude-code) (`claude`), logged in — the
  default backend
- Optional alternative: [Kiro CLI](https://kiro.dev) 2.x (`kiro-cli`), selected
  with `--provider kiro`; rides your `kiro-cli login` session and defaults to
  `claude-fable-5.1` at `high` effort ([details](docs/usage.md#providers))

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

1. Walk the epub spine. Skip nav, documents under 200 words, reference
   pages (index, glossary, bibliography, contents), front and back matter,
   part dividers and appendices.
2. One cheap pass builds a **book primer** (arc, chapter scopes, canonical
   terminology) that is prepended to every chapter call.
3. Per chapter, a **body pass** (a depth-ordered restructure against a
   55–70% length target), then an **opening check** that corrects the
   answer and first sections wherever they say more than the original.
4. Assemble deterministically, then rebuild the epub with original styling,
   code markup, images, and anchors restored. The title gains an
   "(Optimised)" suffix and the cover an OPTIMISED banner.

Fragile markup (MathML, inline SVG, figures, chapter titles, link anchors)
travels through the rewrite as opaque tokens and is re-injected afterwards,
so it cannot be paraphrased away.
Every chapter's input and output is cached under `.blasphemy/`, making runs
resumable and prompt changes diffable. Design notes live in [`specs/`](specs/),
operational notes in [`docs/`](docs/).

## License

[CC BY-SA 4.0](LICENSE) — use it, change it, share it; keep the attribution and
license the result the same way.
