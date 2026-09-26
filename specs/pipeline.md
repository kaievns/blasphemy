# Pipeline spec

## Goal

Take an epub, rewrite each chapter with Claude for readability/comprehension,
reassemble into a new epub. Compression without loss of meaning or useful
information.

## Decisions (locked 2026-08-23)

- **Stack:** Python 3.12, pytest, ebooklib + markdownify + markdown.
- **Model access:** an agent CLI in headless mode, not a vendor SDK — keeps
  subscription auth and avoids per-token billing. Providers are data
  (`providers.py`): binary, base flags, and optional model/effort/system-prompt
  flags. `claude -p` is the default (never `--bare`, which forces API-key
  auth); `kiro` is opt-in via `--provider kiro`. A provider without a system-prompt flag
  gets the system prompt folded into stdin. Binary lookup falls back past
  `PATH` to the usual install dirs because cron/make/nohup shells lose it.
- **Default model:** `fable` on the claude provider, `claude-fable-5.1` at
  `high` effort on kiro. Default since 2026-08-25. It came closer to the
  length and budget contracts than Opus and reads denser at equal quality.
  On the current samples 69 of 98 bodies still exceed the 70% ceiling
  (`docs/review-2026-09-25.md`). Configurable via `--model`.
- **Book types:** non-fiction + technical. Rewriting can be aggressive.

## Flow

1. Load epub, walk spine items that are documents, in spine order.
2. Pass through unchanged: nav documents, reference documents (below),
   `--skip`/`--only` exclusions, and documents under `--min-words` (default
   200) words (covers, title pages, short part dividers). Front matter over
   the threshold (copyright pages, forewords, prefaces, acknowledgments) is
   rewritten and gets apparatus.
3. Convert chapter HTML → markdown with fragile markup tokenised, run the
   body pass and the apparatus pass (see Rewrite architecture), assemble.
4. Convert rewritten markdown → HTML, replace the chapter content in the book.
5. Write the reassembled epub. CSS, spine and non-cover images untouched.
   The title and cover change (see Output identity & styling). The original
   ISBN stays as the unique identifier.

## Resume / caching

Per-book work dir: `.blasphemy/<stem>-<hash8>/`. For each processed chapter:
`NNN.src.md` (input sent to Claude), `NNN.body.md` (the body pass, written
before the apparatus call) and `NNN.md` (assembled output). A chapter with
an existing output file is not re-sent (`cached`), unless `--force`. A
chapter with only `NNN.body.md` reruns the apparatus pass alone, so a
failed apparatus call never re-bills the body. This makes long runs
resumable and prompt iteration inspectable/diffable.
The cache has no key: a cached `NNN.md` is reused after a prompt, model,
primer or converter change, and `NNN.src.md` is rewritten on every run,
cache hits included, so it can describe input the cached output never saw.

## Failure handling

- Claude call retried with backoff; after exhausting retries the chapter is
  marked `failed` and the original content is kept — a failed chapter never
  blocks the book.
- Body check before caching (`pipeline.body_problem`): the body fails when
  it does not open with the chapter title (leading ⟦ANCHOR⟧ lines aside),
  ends inside an unclosed ⟦token⟧, ends on a bare heading, or is under 35%
  of the chapter (a refusal). The title rule catches tail fragments: 4 of
  6 HLW ch9 validation draws (2026-09-26) came back as only the last part
  of a long answer, one of them 12,352 words, which a ratio cannot see. The lowest body ratio across the 98
  sample rewrites was 0.56. A failed body goes to `NNN.failed.md` and the
  apparatus pass is never called. HLW ch4 (cut mid-token at a body ratio
  of 0.64) is the case this exists for: a word ratio cannot see it.
- Apparatus check: a reply with no KEY POINTS section is retried once with
  a note, then the chapter fails with its body kept in `NNN.body.md`.
- Sanity check on the assembled chapter (body plus apparatus): output words
  must be ≥ 0.05× input and ≤ 1.5× input + 250 (`APPARATUS_ALLOWANCE`),
  and no ⟦token⟧ may be left unclosed, else treated as failure. A cached
  `NNN.md` with an unclosed token counts as a cache miss: a normal run
  rewrites it, `--rebuild` reports it failed and leaves it in place.
- A sanity or lost-block failure evicts `NNN.body.md` too, so the rerun
  starts from a fresh body.

## Protected blocks

MathML (`<math>`) and inline SVG don't survive the HTML→markdown→HTML round
trip, so before conversion they're swapped for tokens (`⟦MATH-0: E=mc2⟧`)
carrying a text gist — Claude keeps semantic context for compressing the
surrounding prose without touching the fragile XML. Originals are re-injected
after conversion back to HTML. A lost token fails the chapter (original kept,
output evicted from cache into `NNN.failed.md`).

Code listings are deliberately *not* tokenized: the model reads and rewrites
around real fenced code, and the original `<pre>` markup (styled spans,
listing annotations, bolded input) is swapped back afterwards. Blocks are
matched by whitespace-normalised text, so a listing the model dropped or
merged costs that listing alone (positional pairing cost the whole chapter:
How Linux Works had seven chapters with one listing off and lost bold
typed-input on 154 of 382 listings). Leftovers are paired in order only
when their counts agree *and* the word overlap is ≥ 0.6 — a lone unrelated
leftover is a coin toss, not an edit. Whatever stays unmatched remains
fenced and is counted in the chapter note. This relies on the provider
returning the model's markdown faithfully — see the kiro session-store note
in `docs/usage.md` for how that is guaranteed there.

Listing captions (`p.CodeListingCaption`) and table titles
(`figcaption.TableTitle` inside a `<figure>` around the table) travel as
prose and come back as plain paragraphs. `restore_captions` matches them to
the originals by label ("Table 2-1") and copies the original element over,
re-wrapping an adjacent `<table>` into its `<figure>`. Image figures are
excluded: their caption travels inside the protected figure, and an older
cache that also kept the caption as prose would otherwise get it twice.

`<var>` passes through as inline HTML with its text escaped, like `<sup>`.
Placeholders are written `<profile-name>`; unescaped they came back as a fake
tag and the reader swallowed them, so `[profile.<profile-name>.package.]`
read as `[profile..package.]`. This covers `<var>` input only: a bare
`<uid>` the model writes in prose is still swallowed on the way back.

### Callouts are content, not markup

Notes, tips, warnings and sidebars are deliberately *not* protected. They
are part of the chapter's argument and the restructuring is free to
dissolve them into the prose, gather them into the asides layer, or keep
them: on the four sample books the model did all three, and 98–99% of each
note's distinctive terms are present in the rewritten chapters. Tokenising
them (tried 2026-09-16, reverted the same day) would have frozen every
note in place as an opaque box, defeating the compression the prompt asks
for.

What *is* restored is styling for the notes the model chose to keep as a
`## Note` heading plus paragraphs: `restyle_notes` reuses the original
callout of the same label (No Starch's `<aside epub:type="sidebar"><section
class="note">`, DocBook's `div.note|tip|warning|…`) as a shell, swapping
its body for the rewritten paragraphs, so the label, rules and italics come
back around the model's text. A dissolved note is left alone. The chapter
title detector skips headings inside callouts, or a chapter without a
styled title would take a note's "Note" heading as the title.

### Reference documents

Indexes, glossaries, bibliographies and contents pages pass through
untouched (`Chapter.is_reference`, detected by title, `epub:type`, or a
wrapper `div.index|toc`). The title must match whole, so a prefixed title
such as "Appendix A. Notes" is rewritten. They are lookup structures, not arguments: a
rewrite destroys them (Statistics' index came back as 23 code blocks with an
"Orient" paragraph) and costs a chapter's worth of credits doing it.
Structural ratios are deliberately not used — Rust's Introduction has more
list items than paragraphs and must still be rewritten.

## Rewrite architecture (two-pass locked 2026-08-25, hologram body since 2026-09-15)

Two Claude calls per chapter, then mechanical assembly:

1. **Body pass** (`prompts/body.md`): the hologram restructure (the answer
   under the title, the shape of the problem as narrative, depth sections
   with contextual headings, optional asides) in the expert register.
   A 55–70% length contract with a comprehension override is appended to
   the user message (`cli.py`) and never measured. Framing matters more than
   numbers: a comprehension-first framing ignores numeric targets entirely
   (H/I experiments).
2. **Apparatus pass** (`prompts/apparatus.md`): produces ONLY delimited
   apparatus sections (Key points / Check yourself / Answers) under a word
   cap of max(220, 10% of body words) stated in the prompt, adaptive to how
   much genuine argument the chapter has; every item must serve the
   chapter's main argument.
3. **Assembly** (`apparatus.py`): deterministic. Title line first, then the
   body, then `## Key points`, then `## Check yourself` with the answers
   under a separate **Answers** label. The Orient, Watch for and
   pause paths are dead code since 2026-09-15. The body cannot be padded or
   tampered with by the apparatus pass.

## Image wrappers

Markdown expresses only `src` and `alt`, so anything else an image carries is
lost in the round trip — and publishers put the styling in different places:

- No Starch (HLW, Rust): `<figure class="opener">` — CSS floats the chapter
  art left at 20%; flattened, it rendered full size between paragraphs.
- DocBook (Statistics): `<div class="mediaobject">` around an empty `<a id>`
  marker and the image; one image carries an inline `style` width.
- Pandoc (SRE): no wrapper, `class`/`id` sit on the `<img>` itself.

So protection targets the *smallest element that carries the styling*: climb
from each image through wrappers that hold it alone (no text, no second
image), and protect that. Figures are always taken whole so `<figcaption>`
travels with them. An image with nothing beyond `src`/`alt` and no classed
wrapper is left as markdown — no token, no failure surface.

Order matters: blocks are protected *before* anchors. An `id` inside a
figure travels with the figure, so tokenising it separately would restore the
same id twice — invalid HTML, and a link target the reader's device may
resolve to the wrong copy.

After restoring, a paragraph adjacent to a figure whose text repeats the
`<figcaption>` is dropped: rewrites cached before figures were protected kept
the caption as prose, so the reader saw it twice. Any token still unresolved
at the end of the chain is stripped rather than shipped.

A figure containing no image (No Starch wraps tables this way) stays markdown
so the model can still read and compress the table; its `<figcaption>`
styling is the price, and the caption text survives as prose.

If a token is missing from the output, the wrapper is re-applied by matching
the image `src` before the chapter is failed. That rescues rewrites cached
before protection existed, so repairing an already-processed book is a
rebuild from cache with no model calls.

### Chapter titles and lead paragraphs

The chapter title is protected the same way (`⟦TITLE-0: 1 Foundations⟧`)
when its markup carries styling — a class on the heading, styled child
spans, or a `<header>` wrapper, which is taken whole. `# Title` flattens all
of it to a bare `<h1>`, and on No Starch books that broke the opener layout
twice over: the centred number/title spans were lost, and `figure.opener`
(`margin-top: -3em; float: left`) is designed to float into `h1.chapter`'s
3.25em bottom margin, so without it the art sat on top of the heading. A
plain `<h1>text</h1>` is left to markdown, which reproduces it exactly.
The prompt tells the model the token *is* the title and to add no heading of
its own; `apparatus.assemble` recognises the token as the title line so the
title stays first. It checks the first line only: an SRE body opens with an
⟦ANCHOR⟧ line, so the source title is prepended and the body's own heading
stays, giving two `<h1>` in 43 of 45 SRE documents.

The lead paragraph is rewritten, so its class cannot travel as a token.
Instead the original lead's class (`p.ChapterIntro`: 1.3em, no indent) is
copied onto the rewrite's first non-empty paragraph after the heading.

A `<p>` that markdown wraps around adjacent tokens — the title and the
opener art land on consecutive lines — is unwrapped when every child is a
restored block, so `<p><header>…</header><figure>…</figure></p>` becomes
valid siblings.

## Cross-chapter consistency (layers, locked 2026-08-23)

1. **Anchor contract** — all intra-book link targets are collected up front;
   referenced anchors travel through the rewrite as `⟦ANCHOR:id⟧` tokens and
   are restored as `<a id>` elements. A dropped token falls back to an anchor
   at chapter top (link lands at chapter start, never breaks) and is reported
   as a warning in the result detail.
2. **Style contract** — the body prompt fixes one depth order for every
   chapter (answer → shape → depths → optional asides). The apparatus
   appends Key points → Check yourself → Answers. See
   `specs/reader-profile.md` for the evidence base.
3. **Book primer** — one Claude call per book (prompt: `prompts/primer.md`,
   input: chapter titles + openings) produces arc + per-chapter scope +
   canonical terminology; cached as `primer.md` in the workdir and prepended
   to every chapter rewrite with the current chapter's position. `--no-primer`
   disables. Primer changes do not invalidate cached chapters — use `--force`.

Layer 4 (sequential digests of previously rewritten chapters) was considered
and deferred; revisit if back-reference fidelity is lacking in practice.

## Output identity & styling

- Title gets " (Optimised)" appended; cover image gets an "OPTIMISED" banner
  (Pillow), so originals and optimised versions are distinguishable in lists.
- ebooklib's writer regenerates every chapter document from a template,
  discarding original heads (stylesheet links) and body attributes. We bypass
  it: documents are written raw (`_RawHtml`), untouched chapters byte-for-byte
  original, rewritten chapters keep their original head + body attrs so the
  book's CSS keeps applying. Raw document bytes live in `item.content`;
  `item.get_content()` is the regenerating path — never use it for documents.

## Known limitations (v1)

- A referenced anchor the model drops falls back to the top of its chapter.
  Cross-references by section number point at numbered headings the
  restructure removes (37–38 dangling in HLW). `restore_captions` replaces
  any unclassed paragraph that starts with a caption label, deleting its
  prose and anchors (13 duplicate ids, 16 broken Rust links).
- Chapters are sent whole. HLW ch4 (17,286 words) came back cut mid-token;
  an output cap is the suspected cause, not confirmed. The body check now
  fails such a chapter instead of shipping it, but the chapter still needs
  a working way to produce its full body.
- Plain images (only `src`/`alt`, no classed wrapper) travel as markdown and
  nothing enforces them. Styled images and figures are protected tokens.
- Tables with colspan/rowspan flatten (markdown can't express merges); cell
  data survives.
- The HTML↔markdown round trip breaks four constructs: code containing a
  line-initial triple-backtick fence (the fence closes early and code and
  prose swap), code nested in list items, definition lists (no `def_list`
  on the way back), and bare `<placeholder>` text. See
  `docs/review-2026-09-25.md`.
