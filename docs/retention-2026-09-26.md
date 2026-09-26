# Comprehension and retention mechanics, 2026-09-26

**The body rewrite mostly follows its own rules. The end-of-chapter
retention layer was built so it could barely work, and you never read it, so
it was removed the same day.** It gave each chapter one retrieval event with
the answers on the same screen as the questions, a 181-word recap a minute
above them, and "cumulative" questions answered by the current chapter. The
book now asks you to retrieve nothing and brings nothing back, which is
also where the original book stands. Whether the rewrite beats the original
for you is unmeasured, and measuring it costs item-writing and scoring
calls plus about 4–6 hours of your time.

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
| End-of-chapter apparatus (removed 2026-09-26) | could not work as built; unread | high | general + ADHD | Answers started a median 92 words below question 1, so the quiz ran as rereading; a recap sat directly above; cumulative questions were answered by the current chapter (median 89% of each answer); the word cap bound in 10 of 76 chapters. ADHD adults predict memory accurately but self-test less (Knouse 2012) [ND-adult, paired associates] |
| Orient, Watch for, prequestions (retired) | neutral | low-med | general | Prequestions help only what they ask (g=0.66 vs 0.01, King-Shepard 2025) |
| Pauses (retired) | leans neutral | low | ADHD | Placement alone buys about 0 at a delay (Weinstein 2016) [general-student] |
| No review after the chapter | hurts by omission | medium (direction) | general | Spaced vs massed retrieval g=0.74, a ceiling from mostly lab studies (Latimier 2021) |
| Nav passed through unchanged | hurts place-keeping | high (defect) | both | 3.3% of rewritten headings appear in the TOC, against 46% of original headings |
| Prompts chosen by one unblinded read | cannot measure retention | high | general | Felt vs actual comprehension r=.178 over 115 studies (Yang 2022) |

## What hurts, ranked

Ranked by damage to what you keep from the book (retention, fidelity,
re-entry).

```
0 min                                            ~20 min
|answer|shape|  depth  |  depth  |  depth  |asides|
retrieval events inside the chapter 0 · after it 0 · spaced re-contact 0
```

1. **Nothing asks you to retrieve or revisit.** Retrieval before seeing the
   answer is the strongest general retention lever (testing vs restudy
   g≈0.50, Rowland 2014), and spacing adds more (g=0.74 as a lab ceiling,
   Latimier 2021). The removed apparatus gestured at both and delivered
   neither: its answers were visible, so it ran as rereading (Kornell, Hays
   & Bjork 2009), and its cumulative questions were answered by the current
   chapter. Against the original book this loses nothing, since the original
   has none either. Confidence high that the lever is unused; low on what it
   would be worth to you, since both ND-adult prose studies were null.
2. **Top-layer overstatement.** The answer layer is read first, and before
   the removal it was echoed in Key points and quizzed. LLM summaries
   overgeneralise at OR 4.85 against expert-written summaries, and accuracy
   prompts make it worse (OR 1.90, Peters & Chin-Yee 2025). The hedge patch
   halved hedge deletion but left top-layer errors flat (A/B,
   `specs/prompt.md`).
3. **Prompts chosen by reading impression.** Compression and answer-first make
   text feel easier, and ease is the signal that comes apart from learning.
   A 3/3 preference has two-sided sign-test p=0.25.
4. **The nav misreports where you are.** The e-reader TOC drives chapter
   labels, progress and time-left, and it still describes the author's
   headings. Costs re-entry, not memory directly.

Just below: sentence-shape drift (certain defect, harm not shown).

## What you are not doing that could help, ranked

| # | Lever | Confidence | Cost, including cost to you |
|---|---|---|---|
| 1 | **Measure on you** (protocol below). Any retrieval mechanism now has to earn its friction, and only this can show whether one does | high as a method, low that the planned size settles small effects | Item and scoring calls; 4–6 h of quizzes; 12 chapters read in the original; a weekly start task |
| 2 | **Top-layer fidelity checks**: an absolutes list in `body.md` (only, always, never, all, must); flag absolute density above 1.15× source; flag answer/shape sentences with a causal link the source lacks | medium on direction | 1–3 h; flags cost 0 calls, a verify pass costs calls |
| 3 | **Nav rebuilt from the rewritten headings**; drop or repair the page-list | high on the defect, medium on the cost | 3–4 h, 0 calls |
| 4 | **In-flow retrieval, as a test arm only**: 1–2 why/how questions from chapters N-1 and N-4 at the top of chapter N, answers behind popups. It sits in the reading path rather than after the chapter end you skip. ADHD readers recall fewer central ideas but recognise them like controls, which points at missing retrieval cues (Yeari 2019) [ND-adult, expository text] | low-medium; adoption by you is the open question | 2–3 h, 0 calls. It repeats questions word for word, the complaint that retired Orient |

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
restatement, **bring content back as questions, never as restated prose**,
if anything is brought back · current section sizes · Orient and
prequestions stay retired.

## Where comfort and learning diverge

- **Feels right, costs retention:** choosing prompts by how a chapter
  reads; say-it-once as the whole policy (not restating is right, never
  returning is wrong). The removed apparatus was the same pattern: answers
  under the questions and a recap before the quiz felt efficient and turned
  retrieval into rereading.
- **Feels costly, helps:** a failed retrieval attempt (still beats reading
  the answer, Kornell 2009); answering on paper or aloud (adds g=0.17 over
  silent retrieval, Yu 2025; optional).
- **Neither:** answer-first (small either way, most errors); compression
  (saves 4.6 minutes per chapter, retention effect unmeasured); "I retain
  exact wording" (a fine comfort rule, not a basis for the retention design).

## How to test it on yourself

Top questions: (1) does the rewritten body beat the original at 7 days;
(2) do the answer and shape layers pay for their error cost; (3) does an
in-flow retrieval arm add enough to earn its friction.

- **Unit:** one chapter. Randomise with a fixed seed in blocks of 3 within a
  book, about 36 chapters over 2–3 books. Allocation stays sealed until you
  open a chapter; the arm is visible while you read; scoring is blind.
- **Factors:** rewrite vs original body (24:12, neither with apparatus);
  full vs depths-only (12:12 inside the rewrites); in-flow retrieval vs none
  (18:18).
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
  test. blasphemy delivered it only through the end-of-chapter apparatus,
  which was built weakest and removed on 2026-09-26; it now delivers none.
- Work books get re-exposed on the job, which shrinks the extra gain from
  spacing by an unknown amount.
- Local numbers are word-count proxies at 200–238 wpm with code counted as
  prose, and the audits are LLM passes.
