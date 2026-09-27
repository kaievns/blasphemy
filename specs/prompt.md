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
- **Banned words: "gate", "provenance", "delve"** in any form, unless the
  author's own term in that chapter. Enforced by prompt, one body retry,
  and a `banned words:` note in the chapter result. (Locked 2026-09-15.)

## Prompt design principles
- The rewrite prompt plus the book primer is the system prompt
  (`--system-prompt` on claude, folded into stdin on kiro). The chapter
  markdown plus the length contract is the user message. Output must be
  markdown only, no preamble/commentary (anything else corrupts the epub).
- Cut: repetition, filler anecdotes, marketing prose, rhetorical padding,
  restated points.
- Keep: every fact, number, name, argument step, code block, and any example
  that carries the point (condensed if long).
- Structure (hologram, approved 2026-09-15): ordered by depth, not by the
  author's presentation — the answer under the title, the shape of the
  problem as narrative, then depth sections with contextual headings, then
  asides. Every layer continues the one above and adds; nothing is said
  twice. The author's section order and boundaries do not survive; terms,
  claims, specifics, code and figures do. Measured output differs on two
  points: the depths keep the author's order (Kendall tau median 0.995),
  and the 8 audited chapters hold 52 restatements
  (`docs/review-2026-09-25.md`).

## Prompt files

Live in `src/blasphemy/prompts/`: `body.md` (hologram body pass, option O),
`check.md` (opening check) and `primer.md`. Override the body
prompt with `--prompt <path>` for experiments.

## Iteration log

Record notable prompt changes here with date + what/why. Newest first.
Entries on the same day are not in time order. Sample and prompt files
named below lived in `experiments/`, which is gitignored, so they are not in
the repo.

- 2026-09-27: options P and P2 — fractal structure, from Kai's read of O:
  the answer-first opening "feels rushed", bottom-line facts without
  reasoning, "like an answer from googling", no author texture; wanted
  instead the same shape at every level (problem, reasoned answer, detail;
  each section nesting it), reasoning at every level, no duplication
  between levels, knowledge building into context. P: the chapter opens
  with the author's problem, then the answer with the author's reasons,
  each pointing to the section that develops it; each section opens with
  the question the level above left open; asides last; questions allowed
  only as the problem a level answers. P2 = P plus explicit "never open a
  section by restating the level above" and no section numbers or
  examples at the top. Chapter 1 of 4 books, judged blind against Kai's
  stated criteria (1-5 each, summed over 4 books): P beat O in 4 of 4 —
  problem-first 20 vs 7, texture 17 vs 12, not rushed 16 vs 10, context
  before detail 16 vs 11, opening errors 9 vs 13 — at 79-85% length vs
  72-79%. P vs P2 split 2-2 with near-equal totals; restatements 27 vs 26,
  so the no-repeat wording does not stop repetition (O had 52 in 8
  audited chapters). Prompts `experiments/prompts/body-p.md`, `body-p2.md`;
  samples `experiments/ch1-2026-09-27-P*/`. Awaiting Kai's read.
- 2026-09-27: opening check added (`check.md`): a fresh call checks the
  answer layer and first two sections against the original and returns
  sentence-level fixes, applied only when their quoted evidence exists in
  the original. On 12 correctly split drafts judged blind with and without
  it: opening errors 6.0 → 3.9 per 1k words (8/12 better). On 6 SRE
  drafts where a split bug checked the whole chapter, every measure
  improved 6/6 (recall 31.8 → 35.5 of 40, depth errors 8.0 → 5.7 of 20).
  The body prompt alone had left the opening unchanged (8.1 → 7.7).
- 2026-09-26: end-of-chapter apparatus removed (Kai: "i never read those").
  `apparatus.md` and the apparatus pass are gone; `body.md` now says "No
  summaries, recaps or questions" instead of deferring them to a later
  pass; the primer context no longer mentions cumulative questions. The
  retention review had found the apparatus could not work as built
  (answers on the same screen as the questions, cumulative questions
  answered by the current chapter) and that it repeated top-layer
  overstatements.
- 2026-09-25: `body.md` explicitness rules patched after the review (Kai
  approved). Connectives only where the author states or clearly implies
  the link, never an added cause, ranking, count or superlative. "Literal
  and flat" replaced: keep every hedge and quantifier, put the author's
  named exceptions next to it, never delete or strengthen one. Validated
  2026-09-26 by a paired A/B against the previous prompt: 6 chapters × 3
  draws per arm, scored blind (40 frozen claims per chapter, known-error
  patterns, top-layer and depth precision) with a skeptic re-check.
  Hedges dropped 6.6 → 3.1 (fewer in 6/6 chapters), hedged claims kept
  68% → 82%, claims kept 31.8 → 35.3 of 40, load-bearing claims altered
  3.1 → 1.9, known errors recurring 3.6 → 2.2, depth errors 6.6 → 4.4 of
  20. Unchanged: top-layer errors (8.1 → 7.7 per 1k words, noise: draw SD
  2.6), high-severity errors, added causes. Bodies 4 points longer (0.72 →
  0.76). Draw-to-draw SD within a chapter is about 1.8 claims, so
  "generation variance" is real and about half the size of this effect.
  Harness and data are local in `experiments/validation-2026-09-25/`.
- 2026-09-25: review of the 4 sample books (`docs/review-2026-09-25.md`).
  Recall holds (0 of 126 load-bearing claims missing). Precision does not:
  hedge words kept 52% against 68% of prose, and the answer and shape
  layers hold 53% of located errors in 17% of the words. `body.md` lines on
  connectives and "literal and flat" are the suspected cause.
- 2026-09-16: `body.md` told that a ⟦TITLE-…⟧ token is the chapter title:
  keep it as the first line, alone, no heading of its own.
- 2026-09-15: Kai approved O ("significantly better than all previous
  versions"). Promoted to production: `body.md` = O prompt, `apparatus.md`
  = Key points + Check yourself only (Orient/Watch for/Pauses retired).
  Added the banned-word rule (gate, provenance, delve) with mechanical
  enforcement in `style.py`.
- 2026-09-14: option O — hologram, from Kai's rejection of M/N ("a summary
  then the rest intact") and of L's bullet-list second layer. Flat
  depth-ordered restructure in narrative form: the answer under the title
  (no heading), then one or two sections giving the shape of the problem
  in the chapter's own terms, then depth sections with contextual
  headings, then asides; no fixed layer titles; the author's section
  order and boundaries are unpacked and repacked; every layer continues
  the one above and adds — the per-sentence test is "would a reader who
  has read everything above learn something from it". Fable ch1 bodies:
  stats 72%, linux 66%, rust 66% (81/74/73% with apparatus). Stats and
  rust produced a genuine shape layer; linux (a taxonomy chapter) went
  from the answer straight into renamed author sections. Rust key points
  ran to 12 bullets. Fable's safeguard refused the apparatus pass 9/9
  times with a one-phrase change to the apparatus prompt ("depth-ordered
  form … then the depths"); reverting the phrase fixed it — the generator
  now caches the body before the apparatus call. Samples
  `experiments/ch1-*-option-o.md`, prompt `prompt-body-o.md`.
- 2026-09-14: options M/N — nested pyramids, chosen over L's flat pyramid
  after Kai asked which fits multi-point vs sequential chapters. Flat L
  makes three passes over the whole chapter (redundancy against rule 17)
  and separates each detail from its reasoning; nested keeps one chapter
  Bottom line, then every author section as claim → case → detail in the
  author's order, so each fact lives in one place and any section can be
  entered cold. Bold first-sentence claims give a second reading depth
  (bottom line + bold claims) to recover L's stop-early property. M:
  claims ran 30-53 words (rule 12) and the bottom line regrew into a
  section preview. N: claim ≤20 words with the because as the next
  sentence; bottom line 1-3 paragraphs under 60 words each, conclusions
  only. N Fable ch1: stats 69%, linux 72%, rust 66%; claims avg 16-17
  words; bottom lines 156-185 words; all tokens/anchors/fences intact.
  Kai on length: not obsessed, comprehension, absorption speed and
  friction first — the numeric contract stays only as the compression
  driver. Samples `experiments/ch1-*-option-{m,n}.md`. Superseded by O
  (2026-09-15).
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
  superseded by O (2026-09-15).
- 2026-08-25: full library regenerated with production pipeline (J body +
  apparatus + assembly): Stats 90%, HLW 85%, SRE 88%, Rust 77%; total 453k
  -> 386k (85%). 0 content failures (2 SRE reference appendices correctly
  kept originals via sanity guard). Production-vs-experiment gap attributed
  to generation variance (prompt byte-identical, looser draws), never
  measured. Known items: tiny chapters can grow (apparatus minimum) -> skip
  apparatus below ~1,200 words (proposed, not implemented); 4 chapters fell back to fenced code (count mismatch); 2 anchor
  top-fallbacks.
- 2026-08-25: Kai read K vs J: J reads better — K's density rule reverted;
  J locked as production body prompt. Full-library regeneration with the
  production pipeline. Kai asked for front matter
  (prefaces/forewords/acknowledgments) to be skipped ("I never read
  those"). No skip rule existed in code until 2026-09-27 (only `--skip`),
  so the 2026-09-16 samples rewrote 22 non-chapter documents; see
  `specs/pipeline.md#reference-documents` for the rule now.
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
  landed in pipeline with tests. H-vs-J judge panel superseded by Kai's J
  approval.
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
- 2026-08-23: 12-chapter/4-book sample experiment: single-pass avg 83% vs
  contract, shrink pass recovered only 4-9%. Split into two passes:
  compress.md (single objective) + enhance.md (apparatus, growth-capped).
- 2026-08-23: first test run showed growth instead of compression (preface
  +22%, ch1 +7% vs old prompt's -34%/-44%): explicitness + keep-rules +
  apparatus swamped the cut rules. Added hard compression budget (output =
  40-65% of input, apparatus paid from the budget), credits carve-out for
  acknowledgment/blurb name-lists, light apparatus for front matter.
- 2026-08-23: full rewrite from deep research (see `reader-profile.md`):
  language rules (referent resolution, explicit connectives, no unmarked
  irony, flat positions), fixed chapter skeleton, retention apparatus
  (prequestions, pause prompts, key points, retrieval questions), anchor
  tokens, book-primer context. First test run: Statistics Done Wrong.
- 2026-08-23: terminology-preservation rule locked.
- 2026-08-23: added protected-block token rule (⟦MATH-n⟧/⟦SVG-n⟧) — keep
  verbatim, gist after the colon supplies context for compression.
- 2026-08-23: initial version.
