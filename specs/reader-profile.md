# Reader profile: evidence-based guidelines (v2)

Synthesis of five research passes (2026-08-23). v2 re-scopes the autism
evidence to the **Asperger-type profile** (no language delay, high IQ, high
verbal — adult, IQ-matched samples only; easy-read/ID literature explicitly
discounted) and adds the **combined AuDHD** literature. Reader: senior
software engineer, Asperger-type autistic + ADHD, on stimulant medication.

## Operating model of the reader

- **Reading machinery is fully intact** (eye-tracking, IQ-matched adults:
  Howard 2017): word access, syntax, figurative-language accuracy all normal.
  The cost is paid in **efficiency**: more rereading, slower ambiguity
  resolution (novel metaphor at equal accuracy, d≈1.05 slower: O'Shea,
  Cersosimo & Engelhardt 2026, n=18 vs 22, auditory task, not Howard 2017),
  weaker *spontaneous* gist/coherence assembly — normal when structure is
  supplied.
- **Task Support Hypothesis** (Bowler): free recall is disorganized but cued
  recall/recognition are intact — retention normalizes when the text itself
  supplies the organizational scheme. The single strongest retention lever
  for this profile.
- **Strengths to exploit**: systemizing (if-then, rules, taxonomies), and
  exact wording and numbers retained and used (the reader's own account).
  Expository/technical text is the relative strength genre. The verbal
  false-memory advantage (Beversdorf 2000) did not replicate (Bowler 2000,
  Hillier 2007, Murphy 2025), and verbal long-term memory is slightly
  weaker overall (g=−0.21, Desaunay 2020).
- **Medication baseline** (adult data thin: one open-label n=15 trial + one
  retrospective study): methylphenidate effects in adults are all small
  (Pievsky & McGrath 2018: working memory g=0.13, vigilance 0.22,
  inhibition 0.23), and none reach the autism-side profile (inference
  cost, rigidity, sensory load). **Design for the trough** — the text must
  work for the unmedicated/fatigued state.
- **Hyperfocus and inattention co-occur** (Dwyer 2024, n=492 incl. 141
  AuDHD: combined group highest on hyperfocus, and the two positively
  correlated across people). "Locked-in or no traction" is the reader's own
  account, not a measured distribution. Engagement-contingency is the
  defining feature.
- **ADHD's reading failure route is attention (lapses, mind-wandering);
  autism's is inference cost.** Two independent routes; both must be served.

## The layered split (organizing principle)

**Rigid, uniform, predictable scaffolding — carrying varied, interest-dense,
explicitly-connected, short completable content units.** Autism sets the
skeleton; ADHD sets the content texture. Structural surprise costs the
autistic side; monotone content loses the ADHD side. The layers do not
conflict once separated.

## Guidelines

### Structure & scaffolding (autism layer)

1. Same chapter skeleton book-wide, same apparatus names, same order.
   Variation lives in content, never in scaffolding.
2. **Supply the organizational scheme**: numbered case enumerations ("Three
   cases: …"), invariants stated as invariants, conditionals as if-then,
   condition→outcome tables, explicit taxonomies. Make the text a system.
3. State the global point first and cue coherence explicitly ("this matters
   because", "unlike §2") — global processing is available on cue, not by
   default.
4. Orient section states what each part delivers and what can be skipped
   (compensates weaker task-adaptive reading; reduces search cost).
5. Deterministic layout: strong signposting, no decorative variety.

### Content units (ADHD layer)

6. Short completable sections (~5–10 min), never ending mid-argument;
   front-load each section's point (lapses accumulate toward ends).
7. Vary examples, angles, concrete detail — make content intrinsically
   interesting; hook the interest system. Novelty at content level only.
8. Frequent headings double as lapse-recovery anchors.
9. Metacognitive scaffolding closed the ADHD comprehension gap on a long
   digital text (Brann & Sidi 2025, online 2024). The scaffold was
   stage-specific guidance and reader-generated questions, not
   author-embedded prompts (per a secondary report, as the primary
   is closed). Retention apparatus can serve attention, not just memory.

### Language

10. Precise technical vocabulary is an asset — never simplify it. One
    concept = one term forever (verbatim memory makes synonym rotation read
    as a new referent).
11. Kill referential/lexical ambiguity: resolve pronouns across sentence
    boundaries, expand acronyms at first use, no load-bearing homographs.
12. Short-to-medium sentences, one causal link each — but **never delete the
    connective to save words** (trades ADHD load for autism inference cost).
    No center-embedding. Simplify syntax, not vocabulary.
13. Meaning must never depend on nonliteral language; figurative ornament is
    fine when the literal claim is also stated.
14. Flag wrongness explicitly ("Note: common misconfiguration") — subtle
    implausibility is detected slowly.
15. Convert hedges to explicit uncertainty structure ("usually (~90% of
    deployments)"); state positions flatly; never encode requirements in
    social subtext.

### Completeness & redundancy

16. **Brevity never comes from deleting specifics.** Edge cases, exceptions,
    limits, exact numbers are what this reader retains and uses; their
    omission is experienced as gaps. Compression cuts repetition, ceremony,
    and decoration.
17. Strategic *marked* redundancy: one canonical precise statement per idea
    + recaps at predictable points, explicitly labeled as recaps. Unmarked
    paraphrase-restatement reads as contradiction — worst of both profiles.

### Retention apparatus (learning science, unchanged from v1)

18. End-of-chapter retrieval questions with answers (testing effect,
    g≈0.5–0.6, strongest lever); 1–2 cumulative questions to earlier
    chapters (spacing).
19. 2–3 targeted prequestions (g≈0.66 on prequestioned content, 0.01 on
    the rest: King-Shepard 2025).
20. Pause/self-explanation prompts at inferential junctures (g≈0.55).
21. Key-points recap = answer key, not substitute for retrieval.
22. Cut seductive details (direction confirmed by Sundararajan & Adesope
    2020; the g≈−0.3 value is unverified); keep load-bearing examples
    (instantiation test).

### Anti-rules (explicitly rejected broad-autism advice)

- No vocabulary simplification or high-frequency word substitution.
- No short-sentence mandates / easy-read formats — choppy prose destroys
  the connectives this reader needs.
- No pictorial supports: images attract autistic gaze without improving
  comprehension (Yaneva 2015, weak support: easy-read documents, n=20).
  Diagrams that ARE the system (state machines, schemas, tables) are
  content, not decoration.
- No blanket figurative-language ban (accuracy is intact; efficiency rule 13
  is the correct form).
- No brevity-by-deleting-specifics (rule 16).
- No perceptual-difficulty tricks; no reliance on reader-generated
  summaries/rereading.

## Production departures

Since 2026-09-15 production does not apply guidelines 4 (Orient), 9
(embedded prompts), 19 (prequestions) and 20 (pauses): Orient, Watch for
and pauses were retired because they restated the body
(`specs/prompt.md`, 2026-09-13 and 2026-09-15). Guideline 17's recaps live
only in the end-of-chapter Key points. Guideline 15 is shortened in
`prompts/body.md` to "literal and flat", and on the samples that reads as
hedge deletion (`docs/review-2026-09-25.md`). Guidelines 1 and 5 hold for
the depth order but not the headings, which are contextual per chapter.

## Evidence caveats

Adult IQ-matched autism studies are small-N (15–25/group); no study tests
text-design manipulations in a combined AuDHD sample — layered-split
resolutions are principled inference from single-condition evidence; hedge
processing has no direct literature; stimulant data in autistic ADHD adults
is one open-label n=15 trial plus one retrospective chart study.

## Primary anchors

Howard/Liversedge/Benson 2017 · Au-Yeung 2015 · Kalandadze 2018 ·
Jolliffe & Baron-Cohen 1999/2000 · Bowler (Task Support) · Beversdorf 2000 ·
Eraslan/Yaneva 2018/2019 · Yaneva 2015/2019 · Brown 2013 · Dwyer 2024 ·
Craig (review) · Joshi 2019 · Muit/Kan 2019 · RUPP 2005 · Rodrigues 2021 ·
Raymaker 2020 · Dunlosky 2013 · Rowland 2014 · Adesope 2017 · Yang 2021 ·
Schneider 2018 · Sundararajan & Adesope 2020 · Bisra 2018 · Cepeda 2006 ·
Alderson 2013 · Pievsky & McGrath 2018 · Parks 2022 · Brann & Sidi 2025 ·
Desaunay 2020 · King-Shepard 2025 · O'Shea, Cersosimo & Engelhardt 2026.
Claims re-checked 2026-09-25: 51 of 54 cited sources confirmed, the rest
corrected above.
