# Pipeline spec

## Goal

Take an epub, rewrite each chapter with Claude for readability/comprehension,
reassemble into a new epub. Compression without loss of meaning or useful
information.

## Decisions (locked 2026-08-23)

- **Stack:** Python 3.12, pytest, ebooklib + markdownify (html→md) +
  markdown-it-py (md→html, CommonMark with tables and definition lists).
  CommonMark because that is what a model writes: list content indented by
  marker width and fences nested in list items, both of which
  Python-Markdown rejected.
- **Model access:** an agent CLI in headless mode, not a vendor SDK — keeps
  subscription auth and avoids per-token billing. Providers are data
  (`providers.py`): binary, base flags, and optional model/effort/system-prompt
  flags. `claude -p` is the default (never `--bare`, which forces API-key
  auth); `kiro` is opt-in via `--provider kiro`. A provider without a system-prompt flag
  gets the system prompt folded into stdin. Binary lookup falls back past
  `PATH` to the usual install dirs because cron/make/nohup shells lose it.
- **Default model:** Claude Opus 5.5 at `xhigh` effort on both providers
  (`claude-opus-5-5` on claude, `claude-opus-5.5` on kiro), set
  2026-09-27 at Kai's request; pinned ids so the default does not drift
  when an alias moves. A blind A/B on the production setup preferred Opus
  5.5 to Fable (the default from 2026-08-25) on fidelity and structure at
  a quarter of the cost. `xhigh` matched `high` on fidelity with a slight,
  not significant, structural edge at 1.9× the cost and 2.5× the time;
  `max` ranked last and outruns the default timeout (`prompt.md`,
  iteration log, 2026-09-27). The hedge and opening-check A/Bs ran on
  Fable and were not repeated on Opus. Configurable via `--model` /
  `--effort`.
- **Book types:** non-fiction + technical. Rewriting can be aggressive.

## Flow

1. Load epub, walk spine items that are documents, in spine order.
2. Pass through unchanged: nav documents, reference documents and front or
   back matter (below), `--skip`/`--only` exclusions, and documents under
   `--min-words` (default 200) words (covers, title pages).
3. Convert chapter HTML → markdown with fragile markup tokenised, run the
   rewrite passes (see Rewrite architecture), put the chapter title first.
4. Convert rewritten markdown → HTML, replace the chapter content in the book.
5. Write the reassembled epub. CSS, spine and non-cover images untouched.
   The title and cover change (see Output identity & styling). The original
   ISBN stays as the unique identifier.

## Resume / caching

Per-book work dir: `.blasphemy/<stem>-<hash8>/`. For each processed chapter:
`NNN.src.md` (input sent to Claude) and `NNN.md` (output). A chapter with
an existing output file is not re-sent (`cached`), unless `--force`. This
makes long runs resumable and prompt iteration inspectable/diffable.
Cached outputs are checked on read, for 0 calls. One from before
2026-09-26 loses its retired Key points / Check yourself tail (unless the
source has its own Key points heading) and the doubled title the old
assembler gave Pandoc books, and is rewritten in place; under `--rebuild`
the clean-up happens in memory only. A cached output that then fails the
body check is a cache miss: a normal run rewrites it, `--rebuild` reports
it failed and leaves it in place. A `--force` run that fails a chapter
moves the old output to `NNN.stale.md`, so a later run rewrites the chapter
instead of serving what `--force` meant to replace.
The cache has no key: a cached `NNN.md` is reused after a prompt, model,
primer or converter change, and `NNN.src.md` is rewritten on every run,
cache hits included, so it can describe input the cached output never saw.

## Failure handling

- Claude call retried with backoff; after exhausting retries the chapter is
  marked `failed` and the original content is kept — a failed chapter never
  blocks the book. A timed-out call is killed with its whole process group
  (`providers.run_process`): the `claude` launcher starts the real binary as
  a child, and killing only the launcher left that call running beside the
  retry.
- Body check before caching (`pipeline.body_problem`): the body fails when
  it does not open with the chapter title (leading ⟦ANCHOR⟧ lines aside),
  ends inside an unclosed ⟦token⟧, ends on a bare heading, or is under 35%
  of the chapter (a refusal). The title rule catches tail fragments, which
  text-mode output produced when a long reply was continued past the
  output-token limit (`docs/usage.md#claude-default`); the provider now
  joins every message, so the rule is the backstop. The lowest body ratio
  across the 98 sample rewrites was 0.56. A failed body goes to
  `NNN.failed.md`. HLW ch4 (cut mid-token at a body ratio of 0.64) is the
  case this exists for: a word ratio cannot see it.
- Sanity check on a fresh output: words must be ≥ 0.05× and ≤ 1.5× input,
  and no ⟦token⟧ may be left unclosed, else treated as failure.

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
re-wrapping an adjacent `<table>` into its `<figure>`. A paragraph counts as
the caption only when it opens with the label and the original caption's
separator, stays within about twice the original's length, and sits next to
a `<pre>` or `<table>`: prose that opens "Listing 2-1 shows…" is left alone.
Anchors inside the paragraph move into the restored caption, and a table
title with no table beside it stays a paragraph rather than becoming a bare
`<figcaption>`. Image figures are
excluded: their caption travels inside the protected figure, and an older
cache that also kept the caption as prose would otherwise get it twice.

`<var>` passes through as inline HTML with its text escaped, like `<sup>`.
Placeholders are written `<profile-name>`; unescaped they came back as a fake
tag and the reader swallowed them, so `[profile.<profile-name>.package.]`
read as `[profile..package.]`. Inside code, `<var>`/`<sup>`/`<sub>`/`<u>`
become plain text instead (HLW writes `$ cp <var>file1</var>`; as tags they
showed literally and the listing's markup could not be matched back, 145
listings), and the original `<pre>` markup restores the styling. On the way
back, any tag that is not an HTML element (`<uid>`, `<profile-name>`) renders
as text. Code containing backtick runs gets a fence one backtick longer, and
a definition term that opens with a list or heading marker ("1) No
automation") is escaped so it stays a term.

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
`## Note` heading plus body blocks (paragraphs, lists, quotes), or as a
blockquote opening with its bold label (`> **Note:** …`): `restyle_notes` reuses the original
callout of the same label (No Starch's `<aside epub:type="sidebar"><section
class="note">`, DocBook's `div.note|tip|warning|…`) as a shell, stripped to
its label and rules, and puts the rewritten paragraphs inside, so the label,
rules and italics come back around the model's text. It takes at most as
many following blocks as the original callout held: the note has no end
marker in markdown, and taking every paragraph swallowed main text (and a
shell that kept its own body showed the original listing twice); the
shell's empty anchors stay, since other chapters link to them (Stats'
`pr03 → ch02#tips`). A dissolved note is left alone.

Other publisher styling the markdown round trip drops comes back after
restoring: a block the publisher wrapped singly (DocBook `div.footnote > p`,
`div.blockquote > blockquote.blockquote`) is re-wrapped with its class when
the rewrite has the same block, matched by an anchor id it carries, else by
identical text (at least 90% similar for non-paragraphs, since quotes come
back lightly normalised) (`restore_wrappers`); links get their class back by
target (`a.footnote`, `a.xref`, `a.ulink`, `a.indexterm`;
`restore_link_classes`); and when the source puts one class on most
paragraphs right after a heading (No Starch `BodyFirst`: no indent), the
first paragraph under each rewritten heading gets it (`restore_section_leads`). The chapter
title detector skips headings inside callouts, or a chapter without a
styled title would take a note's "Note" heading as the title.

### Reference documents

Indexes, glossaries, bibliographies and contents pages pass through
untouched (`Chapter.is_reference`, detected by title, `epub:type`, or a
wrapper `div.index|toc`). They are lookup structures, not arguments: a
rewrite destroys them (Statistics' index came back as 23 code blocks with an
"Orient" paragraph) and costs a chapter's worth of credits doing it.
Structural ratios are deliberately not used — Rust's Introduction has more
list items than paragraphs and must still be rewritten.

Front and back matter, part dividers and appendices pass through too
(`Chapter.is_matter`), because Kai skips them: `epub:type` frontmatter,
backmatter, copyright-page, preface, foreword, appendix, endnotes and
similar (No Starch); classes `preface`, `colophon`, `appendix` (DocBook);
titles such as Foreword, Preface, Acknowledgments, "Praise for", "Part II -
…", "Appendix A - …" (Pandoc has nothing else); and short pages reading "All
rights reserved". An Introduction, or anything typed chapter or bodymatter,
is always rewritten. On the 4 sample books this passes through the 22
non-chapters the 2026-09-25 review found and none of the 76 chapters.

## Rewrite architecture (fractal body and opening check since 2026-09-27, second pass since 2026-09-28)

Four Claude calls per chapter: body, second pass, two opening checks (one
more when a banned word slips, one more when the second pass's first
revision fails its guards):

1. **Body pass** (`prompts/body.md`, option P): the fractal restructure —
   the same shape at every level. Under the title, the problem the chapter
   answers in the author's framing, then the answer with the author's
   reasons, each pointing to the section that develops it; each section
   opens with the question the level above left open, answers it one
   level deeper, then gives the detail, nesting the same shape in `###`
   subsections; asides last. Expert register, the author's texture and
   reasoning at every level.
   A 55–70% length contract with a comprehension override is appended to
   the user message (`cli.py`) and never measured. Framing matters more than
   numbers: a comprehension-first framing ignores numeric targets entirely
   (H/I experiments).
2. **Second pass** (`prompts/polish.md`, `polish.py`): a fresh call gets
   the original and the body and returns the whole chapter revised for two
   things only: claims stated twice across levels are cut or turned into a
   bridge that picks up the open question, rewording the neighbouring
   sentence so no gap shows, but reasons and takeaways are never cut as
   repeats (the opening keeps every reason, a section that restates one goes
   a level deeper instead, a section keeps the principle it lands on, and a
   repeat stays when cutting it would cost reasoning), and no back-reference
   ("again", "this framing") is left pointing at a cut; and texture the body
   flattened comes back in
   the author's own words (narration like "the author's advice is…" back
   into the author's voice, dropped quips and asides restored, rewriting
   leaks removed), with the body's short-sentence, no-dash-chain style
   kept. The revision replaces the body only if it passes the body check,
   keeps the same ⟦tokens⟧, headings, code blocks, tables and links, adds
   no banned word, and stays within 80–110% of the body's length; one
   retry, then the body is kept. The outcome is in `NNN.polish.json`; a
   failed call keeps the body. `--no-polish` skips the pass. Measured in
   `prompt.md` (iteration log, 2026-09-28, v2 and v3): a blind reader panel
   put the pass above the unrevised draft in 66 of 90 judgments and above
   the original chapter in 72; fidelity within judge noise of the draft.
3. **Opening check** (`prompts/check.md`, `check.py`): the chapter-level
   opening and the first two sections, the part a reader may stop at, are
   checked
   sentence by sentence against the original in a fresh call. The reply is
   JSON fixes: the exact sentence, the original's supporting passage, and a
   replacement that says only what the original supports. A fix is applied
   only if its sentence occurs once in the opening, its quoted passage is
   really in the original, it keeps every ⟦token⟧, and it adds no banned
   word; everything else is recorded as rejected in `NNN.check.json`. The
   call also sees the chapter's section headings: the opening points to
   sections by heading, so a claim heading that says more than the original
   ("…Only Through NAT") gets the same treatment, with the same quoted
   evidence required, and the rename carries to every `*heading*` reference
   (`check.apply_heading_fixes`; the title and headings inside code are
   never touched). The check runs twice (`check.PASSES`), the second call on the already
   corrected opening, because each fresh call catches a different subset;
   a call that fails or breaks the body stops the loop and keeps the
   earlier calls' fixes. `--no-check` skips the pass. The second call
   measured in `prompt.md` (iteration log, 2026-09-28).

   Measured 2026-09-27 on 18 body drafts (6 chapters × 3), each judged
   blind with and without the check (re-judging identical text varies by
   about 1.0 error per 1,000 words). On the 12 drafts whose opening was
   split correctly: opening errors 6.0 → 3.9 per 1,000 words (8 better),
   everything else flat, as expected for an opening-only pass. On the 6 SRE
   drafts a split bug (fixed the same day) sent the whole chapter, and
   everything improved in 6 of 6: opening errors 10.9 → 6.2, claims kept
   31.8 → 35.5 of 40, hedges dropped 5.8 → 3.3, depth errors 8.0 → 5.7 of
   20. That points at checking the whole body for the same one call,
   untested beyond SRE, which also had the worst baseline. 131 fixes
   applied, 4 rejected for quoting evidence the original does not
   contain.

The body ships as written after that. The body check requires it to open
with the chapter title (after leading ⟦ANCHOR⟧ tokens) whenever the source
does.

The end-of-chapter apparatus (Key points, Check yourself, Answers) was
removed on 2026-09-26: Kai never read it, it cost one call per chapter, it
repeated the top layers' overstatements in 5 of 8 audited chapters
(`docs/review-2026-09-25.md`), and it could not work as built
(`docs/retention-2026-09-26.md`).

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
travels with them, and so is DocBook's equivalent, `div.figure` or
`div.informalfigure` (anchor, image block and `p.title` caption in one
styled div). An image with nothing beyond `src`/`alt` and no classed
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
spans, or a `<header>` wrapper, which is taken whole, as is any block that
holds nothing but the title (DocBook's `div.titlepage > div > div > h1`,
which Stats' CSS sizes through `div.chapter > div.titlepage:first-child`). `# Title` flattens all
of it to a bare `<h1>`, and on No Starch books that broke the opener layout
twice over: the centred number/title spans were lost, and `figure.opener`
(`margin-top: -3em; float: left`) is designed to float into `h1.chapter`'s
3.25em bottom margin, so without it the art sat on top of the heading. A
plain `<h1>text</h1>` is left to markdown, which reproduces it exactly.
The prompt tells the model the token *is* the title and to add no heading of
its own; the body check recognises the token as the title line. It looks
past leading ⟦ANCHOR⟧ tokens, because a Pandoc body (SRE) opens with the
chapter's anchor. The retired assembler checked only the first line and
prepended the source title, which gave two `<h1>` in 43 of 45 SRE
documents; cached outputs are repaired on read.

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
2. **Style contract** — the body prompt fixes one shape for every chapter
   and every level within it (problem → reasoned answer → detail, asides
   last). See
   `specs/reader-profile.md` for the evidence base.
3. **Book primer** — one Claude call per book (prompt: `prompts/primer.md`,
   input: chapter titles + openings) produces arc + per-chapter scope +
   canonical terminology; cached as `primer.md` in the workdir and prepended
   to every chapter rewrite with the current chapter's position. `--no-primer`
   disables. Primer changes do not invalidate cached chapters — use `--force`.

Layer 4 (sequential digests of previously rewritten chapters) was considered
and deferred; revisit if back-reference fidelity is lacking in practice.

## Navigation

The source TOC describes the author's sections, which a restructured
chapter no longer has. After all chapters are assembled, `toc.number_headings`
gives each rewritten chapter's section headings an id (depth 1–2 below the
title, callout headings skipped; books that title sections with `<h1>`, like
Statistics Done Wrong, count from there), and `toc.apply` makes that
chapter's entry in both the NCX (`book.toc`) and the EPUB 3 nav document
point at them. Page-list entries into rewritten chapters are dropped: their
print page positions no longer exist. Untouched chapters keep their entries.
This runs on every build, so `--rebuild` repairs an already-processed book.
On identity builds of the 4 samples every TOC link resolves (HLW 498, Rust
208, SRE 513, Stats 89).

Block elements that markdown leaves inside a `<p>` (a figure next to a
restored anchor) are lifted out (`blocks.lift_blocks`), and the source
package's `prefix` declarations are carried over, because ebooklib rewrites
the OPF with only its own. ebooklib also always writes a 3.0 package, and
an EPUB 2 book's untouched XHTML 1.1 documents fail EPUB 3's HTML5 rules
(Stats: 91 errors from a clean source), so a 2.0 source is written back as
a 2.0 package (`epub.save`: version, no `prefix`, no `<meta property>`, no
manifest `properties`). With these, HLW, Rust and Stats pass epubcheck
5.3.0 with 0 errors, as their originals do; SRE carries exactly its
source's 740 (HTML5 `data-type` attributes in a 2.0 package, broken
fragment links) and adds none.

## Integrity check

After the book is written, `integrity.verify` compares the output epub with
the source, in code rather than a model call: the check is mechanical and
book-wide, a model cannot hold a whole book, and it would miss or invent
link failures. It reads both zips directly and reports problems (the book
is damaged) and warnings (worth a look) to `.blasphemy/<book>/integrity.json`;
a problem makes the run exit 1. What it compares:

- package: spine order, every source manifest resource still present
- every document: well-formed XHTML (unless the source already was not),
  the same stylesheet links, the same `<body>` attributes; an untouched
  document's text unchanged
- links: every internal link, image and stylesheet reference resolves,
  except ones the source already shipped broken; NCX and nav entries
  resolve, and entries outside rewritten chapters survive (a problem in
  the book's primary navigation, nav for EPUB 3 and NCX for EPUB 2, a
  warning in the fallback)
- rewritten chapters: the styled wrapper that held the whole body
  (`div.chapter`) is kept, CSS-styled classes the source used, no fewer
  images, math, SVG or figures (protected, so a problem) or tables and code
  blocks (a warning), no ⟦token⟧ or markdown syntax left in the text, no
  duplicate ids, no new heading-level jumps

`--verify` runs it alone against an existing output.

On the samples, identity rebuilds of HLW, Rust and SRE have no problems,
and neither do rebuilds with rewritten chapters of all four (Stats ch2/4,
SRE ch3/22, Rust ch2, HLW ch9; epubcheck 0 errors, SRE 721 of its source's
740). It found rewritten Stats chapters losing `div.chapter` (16 of 16 in a
full rewrite) and, in those four chapters, `div.figure`, `div.sidebar`,
`div.footnote`, `div.blockquote`, link classes and No Starch `BodyFirst`
leads, all since restored. Warnings that remain: HLW and Rust lose NCX page
targets and third-level entries (392 of 920, 242 of 449) because ebooklib
regenerates the NCX from its own TOC model, harmless while their nav
documents are untouched; and callouts the rewrite dissolved into its prose
or asides (7 of HLW ch9's 22 notes, Rust ch2's 8 notes, both No Starch
boxes, one Stats sidebar), which is the prompt's choice, not reconstruction
damage.

## Output identity & styling

- Title gets " (Optimised)" appended; cover image gets an "OPTIMISED" banner
  (Pillow), so originals and optimised versions are distinguishable in lists.
- ebooklib's writer regenerates every chapter document from a template,
  discarding original heads (stylesheet links) and body attributes. We bypass
  it: documents are written raw (`_RawHtml`), untouched chapters byte-for-byte
  original, rewritten chapters keep their original head + body attrs, and
  go back inside the elements that alone held the original body
  (`epub._rewrap`: DocBook's `div.chapter`, same tag and attributes, its id
  dropped only when the rewrite restored that id), so the book's CSS keeps
  applying. Raw document bytes live in `item.content`;
  `item.get_content()` is the regenerating path — never use it for documents.

## Known limitations (v1)

- A referenced anchor the model drops falls back to the top of its chapter.
  Cross-references by section number point at numbered headings the
  restructure removes (37–38 dangling in HLW).
- Chapters are sent whole. HLW ch4 (17,286 words) came back cut mid-token;
  an output cap is the suspected cause, not confirmed. The body check now
  fails such a chapter instead of shipping it, but the chapter still needs
  a working way to produce its full body.
- Plain images (only `src`/`alt`, no classed wrapper) travel as markdown and
  nothing enforces them. Styled images and figures are protected tokens.
- Tables with colspan/rowspan flatten (markdown can't express merges); cell
  data survives.
- The HTML↔markdown round trip, fed back unchanged over the 4 sample
  books, keeps every listing (595/595, 116/116, 22/22 with identical text),
  every list item and caption class in HLW, Rust and Stats, 47 of SRE's 49
  definition lists, and produces no duplicate ids. Chapters rewritten
  before 2026-09-27 were generated from the broken conversion and need
  `--force` to benefit.
