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
- Structure (fractal, option P, approved 2026-09-27): the same shape at
  every level, each zooming in on the one above — the author's problem,
  the answer with the author's reasons (each pointing to the section that
  develops it), then sections that each open with the question the level
  above left open, answer it one level deeper and give the detail, nesting
  the same shape; asides last. Reasoning at every level is the author's;
  knowledge builds into context. Each level is meant to add, never repeat;
  measured output still restates (24 restatements over 4 chapter 1s), and
  prompt wording alone did not reduce it (P2).

## Prompt files

Live in `src/blasphemy/prompts/`: `body.md` (fractal body pass, option P),
`polish.md` (second pass), `check.md` (opening check) and `primer.md`. Override the body
prompt with `--prompt <path>` for experiments.

## Iteration log

Record notable prompt changes here with date + what/why. Newest first.
Entries on the same day are not in time order. Sample and prompt files
named below lived in `experiments/`, which is gitignored, so they are not in
the repo.

- 2026-09-30: body prompt asides example. P's example heading "Two things
  the author notes in passing" was copied near verbatim into 8 of the 65
  chapters of the 2026-09-29 full conversions (HLW 5, Rust 3; "Three
  Things the Author Notes in Passing", "Two Things Noted in Passing"), a
  meta heading the second pass forbids in prose, and in HLW ch1 it
  swallowed the author's own closing section, 1.6 Looking Forward. The
  example is now a topic heading ("Where the Name *grep* Comes From"), with
  "never one about the author or the book" and "a section of the chapter's
  own is never an aside". Not re-measured: a wording fix to an example,
  with nothing else in the prompt changed.
- 2026-09-28: body prompt P3 = P + "reasoning outranks this rule" (keep a
  restatement when removing it would cost a level its reason or takeaway)
  + carrying a claim up to the opening never strengthens it (its
  qualifiers and scope come with it) + a claim heading says no more than
  its section. Full production pipeline (second pass v3, opening check x2)
  on the 18 chapter-draws, blind against P in one batch. Fidelity: top-layer
  errors 16 -> 13 (1.50 -> 1.02 per 1k; fewer in 7 drafts, more in 5, p =
  0.77), known errors 0.50 -> 0.31, claims kept 39.72 / 39.78. Structure,
  36 pair judgments in two label orders: P3 preferred in 15 (p = 0.41);
  top errors 1.28 -> 0.72, reasoning at the top 4.11 -> 3.97, restatements
  4.17 -> 4.75, flow 3.64 -> 3.78, gaps 2.00 -> 1.86. The reasoning priority
  added repetition without adding reasoning; the accuracy gain is small and
  the opening check (twice, with heading fixes) now covers it. Not
  shipped. Samples `experiments/body2-2026-09-28/`, prompt
  `experiments/prompts/body-p3.md`.
- 2026-09-28: the opening check sees the chapter's headings and may
  correct a claim heading that says more than the original, with the
  same quoted evidence, carrying the rename to every `*heading*`
  reference. On the 18 v3 second-pass outputs (check run twice), an audit
  against the original of every heading fix: first wording 65 fixes, 59
  real (91%), 3 dropped a load-bearing specific ("A Router Is a Linux
  Machine with IP Forwarding" -> "A Linux Machine Can Act as a Router"), 2
  needless weakenings; after adding "change only what overstates, keep
  every term, mechanism, number and yardstick, judge against the whole
  section": 73 fixes, 69 real (95%), 0 dropped specifics, 3 needless
  weakenings ("Also a Ceiling" -> "Also a Soft Ceiling"), 1 incomplete.
  Samples `experiments/check3-2026-09-28/`, `check4-2026-09-28/`.
- 2026-09-28: opening check run twice. Tracing top-layer errors showed
  they come from the body pass and survive because each check call
  catches a different subset. A second call on the 18 shipped v3 outputs
  applied 22 fixes in 14 drafts (first call: 4.1 per chapter); an audit
  against the original rated 21 real overstatements corrected, 1
  incomplete (it still cites an overclaiming heading, which no pass may
  edit), 0 errors introduced. Judged blind in one batch, one call vs two:
  confirmed top-layer errors 20 → 16, 2.29 → 1.48 per 1k (better in 7
  drafts, worse in 3, p = 0.34; the judge scored 4 unchanged drafts 3 vs
  1), claims kept 39.61 → 39.67. Cost 101 s and $0.48 per chapter.
  Samples `experiments/check2-2026-09-28/`.
- 2026-09-28: second pass v3 = v2 + "takeaways are not repeats" (a
  sentence stating a principle or conclusion the author emphasizes stays
  in the section that argues it) + "every back-reference must still point
  at something the reader has read", from the panel's learn/explain split
  (entry below). Prompt examples are generic, none from the test
  chapters. Panel round 2, same design with v3 in Fable's place (original
  / `xhigh` / v2 / v3), 90 judgments: first choice 17 / 24 / 12 / 37; v3
  above `xhigh` in 66 (p < 0.0001), above v2 in 68 (p < 0.0001), above the
  original in 72. By lens, v3 above `xhigh`: reader 15 of 18, learn 8,
  explain 11, author 18, plain 14; v3 above v2: 10, 16, 14, 15, 13. Learn
  still leans `xhigh` (first 10 vs 7, v3 better mean rank 1.67 vs 1.78);
  SRE ch9 improved (v3 above `xhigh` 5 of 15, v2 2). The original's
  author-lens firsts rose from 8 to 15 between rounds with no change to
  it: judge variance, so only within-round comparisons count. Top-layer
  audit: reasoning losses 3 (v2 4), opening losses 0, author reasons
  restored 12 (v2 4). Fidelity, `xhigh` / v2 / v3: claims kept 39.67 /
  39.67 / 39.50, hedges dropped 0.17 / 0.00 / 0.22, top-layer errors 1.99
  / 1.72 / 2.22 per 1k, within judge noise. Traced by exact quote, the
  second pass wrote none of the confirmed top-layer errors in any version
  (`xhigh` / v2 / v3: 22 / 19 / 23 in total; from the body pass 18 / 13 /
  19; written by the opening check 2 / 5 / 4). v2 had fewer because its
  cuts removed more of the body pass's overstated sentences; v3 keeps
  them as takeaways, and the opening check, a fresh call per run, catches
  a different subset each time. A v3.1 that made restored text keep the
  original's hedges word for word targeted the wrong mechanism: 25 errors,
  19 from the body pass, 0 from the pass; not shipped. v3 replaced v2 in
  `polish.md`.
- 2026-09-28: reader panel, four unlabeled versions side by side with no
  reference text: the original chapter, Fable, Opus `xhigh`, and `xhigh`
  + second pass v2; 18 chapter-draws × 5 judges with different lenses and
  label orders (the reader profile; learn it for work; explain it from
  memory; faithful to the author; plain preference). First choice of 90:
  v2 50, `xhigh` 32, original 8 (all from the author lens), Fable 0. v2
  ranked above the original in 82, above Fable in 90, above `xhigh` in 58
  (p = 0.008); Fable ranked below the original in 59. By lens, v2 was
  first for the reader profile (14 of 18), plain preference (15) and the
  author lens (7, original 8; v2 above `xhigh` 15 of 18), but `xhigh` led
  learn and explain (11 of 18 each): there v2 had cut restated takeaway
  lines ("The key idea is to permit only the things you find acceptable",
  "the target is therefore both a minimum and a maximum") and, in SRE ch9,
  left dangling references ("Again, not enough testing"), where `xhigh`
  won 14 of 15 judgments. Samples `experiments/panel-2026-09-28/`.
- 2026-09-28: second pass v2, from Kai's call that reasoning outranks
  de-duplication. A top-layer audit of v1's 181 changes to the opening
  and first two sections found 34 that cut or weakened a reason (10 in the
  chapter opening), every one still stated elsewhere: "keep each claim
  once" treated reasons as claims. v2 adds: reasons are not repeats; never
  cut, shorten or weaken a reason, qualifier or bridge in the opening; a
  section restating a reason goes one level deeper instead of deleting it;
  a section still opens with its answer; when a cut would cost reasoning,
  keep the repeat. Same 18 drafts: top-layer reasoning losses 34 → 4,
  opening losses 10 → 0, voice restorations 100 → 95. Blind three-way with
  the unrevised draft and v1, two label orders, 36 judgments: v2 ranked
  first in 24 and above the draft in 36 of 36, above v1 in 24 (p = 0.065).
  Per judgment, draft / v1 / v2: reasoning at the top 4.22 / 3.86 / 4.25,
  gaps 1.53 / 1.81 / 0.89, flow 3.58 / 3.81 / 4.17, restatements 5.89 /
  1.81 / 3.83, texture 3.11 / 4.31 / 4.19, readability 3.89 / 4.00 / 3.97.
  Fidelity: claims kept 39.67 in all three; top-layer errors 1.99 / 1.81 /
  1.72 per 1k. v2 replaced v1 in
  `polish.md`; v3 replaced v2 the same day (entry above). Blind four-way with Fable (36 judgments, labels rotated):
  v2 ranked first in 26, above Fable and the draft in 36 of 36, above v1
  in 26 (p = 0.011). Per judgment, Fable / draft / v1 / v2: reasoning at
  the top 4.00 / 4.53 / 4.31 / 4.50, flow 3.47 / 3.61 / 3.61 / 4.03, gaps
  1.39 / 1.92 / 2.44 / 1.50, restatements 5.39 / 6.67 / 3.69 / 5.22,
  texture 3.61 / 3.17 / 4.14 / 4.14, readability 2.61 / 4.08 / 4.14 /
  4.14.
- 2026-09-28: second pass (`polish.md`) after the body, before the opening
  check, from Kai's ask to cut the repetition and close the texture gap to
  Fable without gaps in the flow or losing readability. Two variants on
  the 18 Opus `xhigh` bodies (6 chapters × 3), each then checked: an edit
  list (span replacements, each verified: a cut repeat names the
  statement it keeps, a restored phrase quotes the original, no long
  sentence, dash or semicolon added) and a full revision (the chapter
  returned whole, guarded on tokens, headings, code, tables, links,
  length). Blind three-way with the unrevised draft, two label orders, 36
  judgments: the full revision ranked first in 27 and above the draft in
  33 (sign p < 0.001), above the edit list in 28 (p = 0.001);
  restatements 216 → 115 (edits) → 88 (full), no-duplication 101 → 145,
  texture 109 → 162, flow 135 → 141, readability 142 → 146, gaps 56 → 61,
  reasoning at the top 151 → 143; every difference rated "slight" (about
  95% of the text is unchanged). The edit list left more gaps (67): a cut
  span cannot reword the paragraph around it. Against Fable with the model
  A/B's judge: full won 18 of 18 (9 clear): restatements 73 vs 81,
  no-duplication 63 vs 55, texture 76 vs 69, readability 75 vs 49 — where
  the unrevised `xhigh` trailed on all three of the first. Fidelity,
  skeptic-rechecked: claims kept 39.7 in all three arms, top-layer errors
  1.8 vs 2.0 per 1k (within noise). Mechanics unchanged: sentences over 35
  words 4%, dashes 0.2 per 1k, length 89%. Cost: $1.09 and 394 s per
  chapter at `xhigh`. The full revision shipped as v1, replaced the same
  day by v2 (entry above); all 18 validated revisions pass the production
  guards. Samples
  `experiments/polish-2026-09-28/`.
- 2026-09-27: effort A/B on Opus 5.5, `high` vs `xhigh` vs `max`, same
  setup and chapters. `high` and `xhigh` ran 6 chapters × 3 draws; `max`
  ran only the 2 Statistics Done Wrong chapters × 3, because a 4.5k-word
  body took 51-105 min, split across 2-4 messages by the output limit,
  past the default 2400 s timeout. Judge noise, from re-judging the 18 `high`
  drafts: ±0.22 claims kept, ±1.17 top-layer errors per 1k words.
  Fidelity: `xhigh` equals `high` within that noise (claims kept 39.7 vs
  39.5, top-layer errors 2.0 vs 2.0 per 1k, deeper-sample errors 0.9 vs
  1.5 of 20). Structure, blind, each set judged in two label orders:
  `xhigh` ranked above `high` in 23 of 36 judgments, 32 of them rated a
  "slight" difference; per chapter-draw 10 `xhigh`, 5 `high`, 3 split
  (sign test p = 0.30); ahead on reasoning at the top (154 vs 134),
  behind on readability (130 vs 140). `max` ranked last in 10 of 12
  three-way judgments: texture 36 vs 49, not rushed 37 vs 57 — shorter
  (82% vs 90-93% of source), clipped, jokes and asides cut; claims kept
  39.3 vs 39.8 on the same chapters. Cost per chapter (reported): `high`
  $1.26, `xhigh` $2.35 (2.5× the time), `max` $11.60 on the Stats
  chapters vs $0.98 at `high` (22× the time). Kai chose `xhigh` as the
  default. `xhigh` vs Fable, blind in pairs with the model A/B's judge:
  `xhigh` preferred in 14 of 18 (8 clear; `high` had 3 clear); reasoning
  at the top 76 vs 71 (`high` trailed Fable, 67 vs 74), readability 76 vs
  49, top-layer errors 22 vs 41; still behind on restatements (118 vs 92),
  no-duplication (53 vs 60) and texture (65 vs 72). Fable's 4 wins: 2 in
  How Linux Works ch16, 2 in Stats ch11.
  Samples `experiments/effort-2026-09-27/`.
- 2026-09-27: model A/B, Fable (no effort flag) vs Opus 5.5 at `high`, on
  the production setup (P body prompt + opening check), 6 chapters × 3
  draws. Fidelity, judged blind against the frozen 40-claim inventories
  with a skeptic recheck: Opus kept 39.3 vs 37.7 claims (better in 6 of 6
  chapters), altered 0.7 vs 2.2, kept 97% vs 91% of hedged claims (6/6),
  and made 2.5 vs 3.2 top-layer errors per 1k words (5/6) and 1.4 vs 3.2
  errors in 20 sampled deeper sentences (5/6). Structure, judged blind in
  pairs against Kai's criteria (sums over 18 pairs): Opus preferred in 14
  (3 clear); readability 74 vs 50, not rushed 73 vs 59, context before
  detail 78 vs 68, top-layer errors 26 vs 43; but restatements 104 vs 78,
  no-duplication 50 vs 63, reasoning at the top 67 vs 74. The judges saw
  the same split in almost every pair: Fable compresses into long
  dash- and semicolon-chained sentences (27% over 35 words vs 5.5%), Opus
  writes short declarative sentences, keeps lists, uses claim headings,
  and restates top-level claims as sections open. Fable's 4 wins were
  where the author's voice carries the chapter (Rust ch10, Stats ch11).
  Opus bodies ran 90% vs 80% of source, 265 s vs 596 s, with no
  output-limit continuations (Fable 1.17 messages per body), at a reported
  $1.26 vs $5.14 per chapter. Chapter 1 of 4 books: Opus preferred in 3
  of 4. P2 on Opus: P preferred in 3 of 4; P2 cut restatements 31 → 25
  but lowered readability 16 → 13 and texture 15 → 13, and one P2 draft
  dropped nearly every anchor. Samples `experiments/model-2026-09-27/`.
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
  samples `experiments/ch1-2026-09-27-P*/`.
- 2026-09-27: Kai approved P ("i like the writeups it produces"); promoted
  to production `body.md`. O's answer-first opening is retired.
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
