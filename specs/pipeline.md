# Pipeline spec

## Goal

Take an epub, rewrite each chapter with Claude for readability/comprehension,
reassemble into a new epub. Compression without loss of meaning or useful
information.

## Decisions (locked 2026-08-23)

- **Stack:** Python 3.12, pytest, ebooklib + markdownify + markdown.
- **Claude access:** `claude -p` headless (subscription auth — never `--bare`,
  which forces API-key-only auth). Not the Anthropic SDK.
- **Default model:** `opus` (Claude Opus 5). Configurable via `--model`
  (`fable`, `sonnet`, `haiku` or full model names) for quality/quota iteration.
- **Book types:** non-fiction + technical. Rewriting can be aggressive.

## Flow

1. Load epub, walk spine items that are documents, in spine order.
2. Skip non-content documents by heuristic: fewer than `--min-words`
   (default 200) words → passed through unchanged (covers, TOC, copyright).
3. Convert chapter HTML → markdown, send to Claude with the rewrite prompt,
   receive rewritten markdown.
4. Convert rewritten markdown → HTML, replace the chapter content in the book.
5. Write the reassembled epub. Metadata, CSS, images, spine untouched.

## Resume / caching

Per-book work dir: `.blasphemy/<stem>-<hash8>/`. For each processed chapter:
`NNN.src.md` (input sent to Claude) and `NNN.md` (Claude output). A chapter
with an existing output file is not re-sent (`cached`), unless `--force`.
This makes long runs resumable and prompt iteration inspectable/diffable.

## Failure handling

- Claude call retried with backoff; after exhausting retries the chapter is
  marked `failed` and the original content is kept — a failed chapter never
  blocks the book.
- Sanity check on output: word ratio vs input must be within [0.05, 1.5],
  else treated as failure (guards against refusals/truncation).

## Known limitations (v1)

- Original intra-book anchors/cross-references may break (rewritten HTML has
  new structure). TOC at spine level survives.
- Very long chapters are sent whole; no chunking yet. Claude's context makes
  this fine for normal books.
- Images inside chapters are dropped from rewritten output (markdown pipeline
  does carry `![...]` through, but Claude may drop them; revisit if it hurts).
