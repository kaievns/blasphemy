# Prompt spec

## Reader profile

- 25 years in software engineering; deep technical background — never
  dumb down technical content.
- AuDHD: needs signal, hates noise. On point, logically structured,
  minimal repetition, no throat-clearing.
- Goal: **compress without losing meaning or useful information.**

## Locked rules

- **Original terminology is preserved verbatim.** Never replaced with
  simplified versions for readability — simplify around terms, never
  the terms. (Locked 2026-08-23.)

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
- 2026-08-23: terminology-preservation rule locked.
- 2026-08-23: full rewrite from deep research (see `reader-profile.md`):
  language rules (referent resolution, explicit connectives, no unmarked
  irony, flat positions), fixed chapter skeleton, retention apparatus
  (prequestions, pause prompts, key points, retrieval questions), anchor
  tokens, book-primer context. First test run: Statistics Done Wrong.
- 2026-08-23: first test run showed growth instead of compression (preface
  +22%, ch1 +7% vs old prompt's -34%/-44%): explicitness + keep-rules +
  apparatus swamped the cut rules. Added hard compression budget (output =
  40-65% of input, apparatus paid from the budget), credits carve-out for
  acknowledgment/blurb name-lists, light apparatus for front matter.
- 2026-08-23: 12-chapter/4-book sample experiment: single-pass avg 83% vs
  contract, shrink pass recovered only 4-9%. Split into two passes:
  compress.md (single objective) + enhance.md (apparatus, growth-capped).
- 2026-08-25: D/E/F/G iteration cycle on ch1 samples (3 books), each
  judged by 6-agent workflow against Kai's five feedback points + 15-fact
  preservation sweep. D: register/grounding fixed, length failed (87-96%).
  E: cut mandate + enforcement (80-93%); apparatus pass overshot its cap in
  3/3 books. F: apparatus generated standalone + mechanically inserted into
  frozen body (80-88%); bodies judged at D texture level, defects moved to
  assembler. G: assembler fixed (H1, front-matter placement, Q/A separation,
  pause guards) — 80-86%, structure checks green. Learned: full-rework
  register floor is ~68-73% body; apparatus adds ~10%; pause-locator
  protocol still loses pauses when guards reject placements (linux G: 0
  inserted).
- 2026-08-25: Kai reviewed A/B/C chapter-1 samples of all three books.
  Verdict: full-rework register (B) wins over compress+patch (A) — more
  logical, linear, no re-reading needed. Keep Orient. Replace prequestions
  with a "Watch for" reading briefing. Keep Pause entries but ground them
  (B's felt half-hallucinated). Fix B's flaws: steam-rolled texture,
  over-explanation, expanded shorthand ("asynchronous input and output" for
  "async IO"), too much scaffolding. → version D prompts (experiments/,
  versions kept as *-d/*-e for comparison, per Kai's standing rule).
- 2026-08-23: research re-scoped to Asperger-type + medicated ADHD
  (reader-profile.md v2). Layered split: rigid uniform scaffolding, varied
  interest-dense content. Dropped ~25-word sentence cap (choppy prose
  destroys connectives), added keep-specifics rule (edge cases, exceptions,
  exact values), systemizing structure (cases/invariants/if-then tables),
  marked-recap rule, plausibility flagging, skippability in Orient.
