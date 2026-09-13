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

- 2026-09-13: option L — pyramid/BLUF chapter structure (Kai's proposal:
  Orient and Pause felt repetitive, arriving two sentences before the body
  said the same thing). Body pass emits fixed layers: Bottom line (claims
  with their because) → Reasoning (structured case, may group items) →
  Detail (author's material in author's dependency order, self-contained
  `###` subsections) → Asides (optional, non-load-bearing) → Key points +
  Check yourself from the apparatus pass; Orient/Watch for/Pauses dropped.
  Research fit: BLUF is profile rules 3/4/6 pushed to chapter level and a
  Task-Support organisational scheme; Asides quarantine seductive details
  instead of interleaving them. Risk: three-layer repetition against rule
  17 — mitigated by "one canonical statement per claim, lower layers extend,
  never paraphrase" and verbatim-wording Key points. Fable ch1 samples:
  stats 75%, linux 67%, rust 65% (`experiments/ch1-*-option-l.md`,
  prompts `prompt-body-l.md`/`prompt-apparatus-l.md`). Not in production;
  awaiting Kai's read against J.
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
- 2026-08-25: full library regenerated with production pipeline (J body +
  apparatus + assembly): Stats 90%, HLW 85%, SRE 88%, Rust 77%; total 453k
  -> 386k (85%). 0 content failures (2 SRE reference appendices correctly
  kept originals via sanity guard). Production-vs-experiment gap traced to
  generation variance (prompt byte-identical, looser draws). Known items:
  tiny chapters can grow (apparatus minimum) -> skip apparatus below ~1,200
  words; 4 chapters fell back to fenced code (count mismatch); 2 anchor
  top-fallbacks.
- 2026-08-25: Kai read K vs J: J reads better — K's density rule reverted;
  J locked as production body prompt. Full-library regeneration with the
  production pipeline; front matter (prefaces/forewords/acknowledgments)
  now skipped per Kai ("I never read those").
- 2026-08-25: Kai approved J (linear, comprehensible, apparatus on point);
  asked for more even density/cadence — no mid-flight filler triage. K =
  J + uniform-density rule (every sentence carries load, one-clause
  transitions, even paragraphs). Same lengths (84/84/89), visibly tighter
  prose; promoted to production prompts/body.md. Architecture productionized
  (apparatus.py, two-pass cli flow).
- 2026-08-25: H/I/J iteration from Kai's G feedback + weighting answers
  (core-supporting specifics, adaptive apparatus, comprehension-first w/ 75%
  cap). Finding: OBJECTIVE FRAMING DOMINATES NUMBERS — comprehension-first
  framing (H) yields ~78-81% bodies and ignores numeric targets entirely
  (I: adding "aim 55-70%" changed nothing); compression-primary framing with
  comprehension override (J) restores 73-74% on stats/linux (rust stayed
  81%). Apparatus discipline fixed by adaptive value/time bar (~275-500w).
  Formatting preservation (pre-markup restoration, sup/sub/u passthrough)
  landed in pipeline with tests. H-vs-J judge panel pending (session limit).
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
