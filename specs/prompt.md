# Prompt spec

## Reader profile

- 25 years in software engineering; deep technical background — never
  dumb down technical content.
- AuDHD: needs signal, hates noise. On point, logically structured,
  minimal repetition, no throat-clearing.
- Goal: **compress without losing meaning or useful information.**

## Prompt design principles

- The rewrite prompt is the `claude -p` system prompt; the chapter markdown
  is the user message. Output must be markdown only, no preamble/commentary
  (anything else corrupts the epub).
- Cut: repetition, filler anecdotes, marketing prose, rhetorical padding,
  restated points.
- Keep: every fact, number, name, argument step, code block, and any example
  that carries the point (condensed if long).
- Structure: headings for scannability, short paragraphs, bullets where the
  content is list-shaped, author's argument order preserved.

## Prompt files

Live in `src/blasphemy/prompts/`. Default: `rewrite.md`. Override with
`--prompt <path>` for experiments.

## Iteration log

Record notable prompt changes here with date + what/why.

- 2026-08-23: initial version.
- 2026-08-23: added protected-block token rule (⟦MATH-n⟧/⟦SVG-n⟧) — keep
  verbatim, gist after the colon supplies context for compression.
