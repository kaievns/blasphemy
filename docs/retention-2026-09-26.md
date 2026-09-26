# Comprehension and retention mechanics, 2026-09-26

**The body rewrite mostly follows its own rules. The retention layer is built
so it can barely work.** Each chapter gets one retrieval event. Its answers
sit on the same screen as the questions, a 181-word recap sits a minute
above them, the "cumulative" questions are answered by the current chapter,
and nothing brings a claim back after the chapter ends. The three cheapest
fixes (hidden answers, questions before Key points, real carry-forward
items) cost 0 model calls. Whether the rewrite beats the original for you
is unmeasured, and measuring it costs item-writing and scoring calls plus
about 4–6 hours of your time.

Governing caveat: almost all evidence below is general learning science.
Only 2 ND-adult studies test retrieval practice on prose, and both found no
benefit over restudy in either group (the controls showed none either), so
they speak to that setup (short texts, free recall, no feedback), not to ND
status.

Sources: 7 research reports, each citation-checked (167 checked: 139
confirmed, 26 misstated, 2 not found; misstated items corrected or dropped),
a measurement pass over 76 chapters, and a critic pass. Raw material is
local in `experiments/retention-2026-09-25/` (gitignored).

## Scorecard

Evidence tags: population (ND-adult, ND-child, general-adult,
general-student, expert) and design.

| Mechanic | Verdict | Conf. | Basis | Why |
|---|---|---|---|---|
| Answer-first (M1) | mixed, small | low | both + expertise | Massed objectives up front did not beat no preview (Sana 2020, p=.21) [general-student]. Highest error density of any layer (3.87 per 1k words vs 0.57 in the depths, `review-2026-09-25.md`) |
| Shape layer (M2) | helps if it mirrors depth order | low | autism | Category cues at encoding raised recall in both groups, the autistic group still clustered less (Bowler 2010) [ND-adult, word lists] |
| Author's depth order (M3) | helps (plausible) | low | both | Output keeps it (median tau 0.98–0.995), but `body.md` still orders a "full restructure" |
| Contextual headings | help | medium | general + expertise | Headings help recall of important content more at high prior knowledge (Surber & Schroeder 2007) [general-student] |
| Section size | neutral | low | ADHD | Median 215 words between headings, max 1,004. Adult ADHD shows a lower overall level, not a steeper decline (Tucha 2008) [ND-adult] |
| Asides last (M4) | helps | medium | general | End placement reduced seductive-detail damage (Harp & Mayer 1998) [general-student] |
| Say-it-once (M5) | comfort yes, retention cost small | low | general | Massed rereading gave no gain at 2 days (Rawson & Kintsch 2005) [general-student] |
| 55–70% compression (M6) | mixed | low | general | Saves 4.6 min per chapter. Examples beat extra definition study (d=0.74–1.67, Rawson et al. 2015) [general-student]; today 90% of 929 example sentences survive |
| Terms verbatim (M7) | helps | medium | expertise | Holds on fidelity grounds; the autism premise (synonym = new referent) is unsupported, not refuted |
| Expert register (M8) | mixed | low-med | expertise | Expertise reversal: novices gain d=0.505 from assistance, experts d=0.428 from less (Tetzlaff 2025, via prior check). Costly side for books outside your field (inference) |
| Author-sourced connectives, kept hedges (M9, patched) | helps fidelity | medium | autism + general | Paired A/B, 6 chapters × 3 draws: hedges dropped 6.6 → 3.1, claims kept 31.8 → 35.3 of 40 (`specs/prompt.md`) |
| Antecedent rule | helps | low | both | Sentence-initial pronouns 9.4% → 4.3%. Re-presenting the last 1–2 sentences offsets an interruption (Glanzer 1984) [general-student] |
| Short sentences | rule right, output breaks it | high (defect) | ADHD | Sentences over 35 words 8.6% → 16.1% shipped; drafts were at 24% before and after the patch |
| Bold | mixed | low | general | 1.09 per 1k vs 0.43 in the originals; none in 24/76 chapters |
| Key points above the questions (A1) | reduces the retrieval benefit | low | general | The quiz follows a recap read 1 minute earlier |
| Why/how questions (A2) | helps, small for you | low-med | general; ND | ADHD readers recalled fewer central ideas but recognised them like controls: fewer retrieval cues (Yeari 2019) [ND-adult, expository text] |
| Cumulative questions | cosmetic as built | high | general | The current chapter holds a median 89% of each answer; 3 of 14 hand-checked needed the earlier chapter |
| Answers under the questions (A3) | hurts vs hidden answers | medium | general + ADHD | ADHD adults predict memory accurately but self-test less (Knouse 2012) [ND-adult, paired associates] |
| Word cap (A4) | does not bind | low | – | Over cap in 66/76 chapters |
| Orient, Watch for, prequestions (retired) | neutral | low-med | general | Prequestions help only what they ask (g=0.66 vs 0.01, King-Shepard 2025) |
| Pauses (retired) | leans neutral | low | ADHD | Placement alone buys about 0 at a delay (Weinstein 2016) [general-student] |
| No review after the chapter | hurts by omission | medium (direction) | general | Spaced vs massed retrieval g=0.74, a ceiling from mostly lab studies (Latimier 2021) |
| Nav passed through unchanged | hurts place-keeping | high (defect) | both | 3.3% of rewritten headings appear in the TOC, against 46% of original headings |
| Prompts chosen by one unblinded read | cannot measure retention | high | general | Felt vs actual comprehension r=.178 over 115 studies (Yang 2022) |

## What hurts, ranked

Ranked by damage to what you keep from the book (retention, fidelity,
re-entry).

```
0 min                                            ~20 min      +1 min     +1.5 min
|answer|shape|  depth  |  depth  |  depth  |asides| Key points | Q1..Q6  | Answers
                 ^ typical tested claim            181 words    92 words
                 └── median 10.6 min to its question (p10 3.4, p90 26.9) ──┘
retrieval events inside the body 0 · after the chapter 0
```

1. **The only retrieval event runs as restudy.** The testing effect needs an
   attempt before the answer is visible. Answers start a median 92 words
   below question 1 (`apparatus.py` prints them under the questions), so the
   low-effort path is to read question and answer together, which is the
   restudy condition retrieval beats (Kornell, Hays & Bjork 2009). ADHD
   adults drop the choice to self-test (Knouse 2012), so the layout has to
   force the attempt. Confidence medium on direction; size for you unknown.
2. **No spaced re-contact; cumulative questions are cosmetic.** The
   apparatus pass sees only the current body and the primer, and
   `apparatus.md` requires every question to be "answerable from the chapter
   text alone", so the model names the earlier chapter and answers from the
   current one. No spacing study in autistic or ADHD adults was located.
   Confidence high on the diagnosis, low on the size of the loss.
3. **Top-layer overstatement, exposed three times.** The answer layer is read
   first, echoed in Key points, then quizzed. LLM summaries overgeneralise at
   OR 4.85 against expert-written summaries, and accuracy prompts make it
   worse (OR 1.90, Peters & Chin-Yee 2025). The hedge patch halved hedge
   deletion but left top-layer errors flat (A/B, `specs/prompt.md`).
   21.8% of quiz answers come from the first 15% of the body.
4. **Prompts chosen by reading impression.** Compression and answer-first make
   text feel easier, and ease is the signal that comes apart from learning.
   A 3/3 preference has two-sided sign-test p=0.25.
5. **The nav misreports where you are.** The e-reader TOC drives chapter
   labels, progress and time-left, and it still describes the author's
   headings. Costs re-entry, not memory directly.

Just below: sentence-shape drift (certain defect, harm not shown) and
apparatus on 22 non-chapter documents (3,846 words).

## What you are not doing that could help, ranked

| # | Lever | Confidence | Cost, including cost to you |
|---|---|---|---|
| 1 | **Retrieval-first layout**: questions, then hidden answers (epub footnote popups, or a non-linear answer page), then Key points as the labelled answer key, at most 8 bullets | medium | ~1.5 h, 0 calls. About 6 taps per chapter |
| 2 | **Carry-forward items**: at assembly, copy 1–2 questions from chapters N-1 and N-4 into chapter N, answers hidden, chosen from depth sections; delete the cumulative-question instruction | medium for the carried items, low across the book | 2–3 h, 0 calls. It repeats questions word for word, the complaint that retired Orient, so test it as an arm |
| 3 | **Measure on you** (protocol below) | high as a method, low that the planned size settles small effects | Item and scoring calls; 4–6 h of quizzes; 12 chapters read in the original; a weekly start task |
| 4 | **Top-layer fidelity checks**: an absolutes list in `body.md` (only, always, never, all, must); flag absolute density above 1.15× source; flag answer/shape sentences with a causal link the source lacks | medium on direction | 1–3 h; flags cost 0 calls, a verify pass costs calls |
| 5 | **Question targeting**: one question per depth section, at most one on the answer layer, none on asides | medium | ~1 h, 0 calls |
| 6 | **Nav rebuilt from the rewritten headings**, with entries for Key points and Check yourself; drop or repair the page-list | high on the defect, medium on the cost | 3–4 h, 0 calls |

Lower: per-book familiarity setting (low-medium), link back to the original
(fidelity only), Anki export (low realised gain, adherence is the limit),
bold aimed at quiz targets (low), question-only probes at section ends (A/B
arm only).

Do not build: audio/TTS (self-paced reading beat listening, g=0.13),
Bionic Reading (no benefit), pipeline-set typography (reader settings own
it), generated concept maps (the model-written layers already hold most
errors), added worked examples (expertise reversal), teach-back prompts
(g=−0.02 without a real audience), restored Orient or prequestions.

## Keep

Asides last · the author's depth order (fix `body.md` to say so) ·
contextual headings (copy them into the nav) · terms and code verbatim ·
the hedge and connective patches · the antecedent rule · no paraphrased
restatement, **bring content back as questions, never as restated prose** ·
why/how questions · Key points, moved below the questions · current section
sizes · Orient and prequestions stay retired.

## Where comfort and learning diverge

- **Feels right, costs retention:** answers under the questions (turns the
  quiz into rereading); a recap right before the quiz (makes it easy, and
  the benefit tracks effort); choosing prompts by how a chapter reads;
  say-it-once as the whole policy (not restating is right, never returning
  is wrong).
- **Feels costly, helps:** a failed retrieval attempt (still beats reading
  the answer, Kornell 2009); answering on paper or aloud (adds g=0.17 over
  silent retrieval, Yu 2025; optional).
- **Neither:** answer-first (small either way, most errors); compression
  (saves 4.6 minutes per chapter, retention effect unmeasured); "I retain
  exact wording" (a fine comfort rule, not a basis for the retention design).

## How to test it on yourself

Top questions: (1) does the rewritten body beat the original at 7 days;
(2) do the answer and shape layers pay for their error cost; (3) how much do
retrieval-first plus carry-forward add.

- **Unit:** one chapter. Randomise with a fixed seed in blocks of 3 within a
  book, about 36 chapters over 2–3 books. Allocation stays sealed until you
  open a chapter; the arm is visible while you read; scoring is blind.
- **Factors:** rewrite vs original body (24:12, each with its own apparatus);
  full vs depths-only (12:12 inside the rewrites); retrieval-first vs current
  layout (18:18).
- **Outcome:** a 7-day quiz, 10 items per chapter written from the original
  by a model outside the generator's family and frozen by hash: 4 central
  cued-recall, 2 specifics, 2 quantifier, 1 causal, 1 application.
  Quantifier items offer scale words only (always / usually / sometimes /
  rarely / not stated). No true/false items: truth-checking raised later
  belief in false statements (Arcos 2024).
- **Secondary:** one felt-clarity tap per chapter; reading minutes from the
  e-reader.
- **Decision rule:** keep an arm if P(gap > −5 points) ≥ 0.8. With the
  assumed chapter SD, effects under about 10 points stay undecided in about
  half of runs; re-estimate the SD after 10 chapters.
- **First action:** freeze the item bank for your next unread book from its
  original text. It needs nothing from you.

## Evidence limits

- ND-adult evidence on prose retention: 2 studies, both null in both groups.
  Retrieval benefits in ND adults are shown on word pairs and key terms
  (Knouse 2015/2020, Cairney 2026, Minear 2023). Spacing: no ND study
  located.
- Most ADHD samples are unmedicated or unreported. The one medicated
  subgroup (Minear 2023, n=20, exploratory, word pairs) did not differ
  significantly from controls.
- Task support (Bowler) is about support at retrieval, cued questions at
  test. The part of blasphemy that delivers it is the apparatus, the part
  built weakest.
- Work books get re-exposed on the job, which shrinks the extra gain from
  spacing by an unknown amount.
- Local numbers are word-count proxies at 200–238 wpm with code counted as
  prose, and the audits are LLM passes.
