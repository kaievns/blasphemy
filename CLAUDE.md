# blasphemy

Pipeline that takes an epub, rewrites it chapter-by-chapter with Claude for
readability/comprehension (tuned to Kai), and reassembles an optimised epub.

## Ground rules (locked)

1. **Everything has tests.** No feature or fix lands without tests covering it.
2. **Comments are terse and minimal.** Code must be self-explanatory. Context,
   rationale, and design live in `docs/` and `specs/`, never in comments.
3. **Docs are minimal and on point.** `docs/` for how things work, `specs/` for
   what we're building and why. No filler.
4. **Ambiguity → ask, don't assume.** When a decision isn't settled by the specs
   or the user, stop and ask, presenting concrete options.
5. **Commit as you go.** Small, coherent commits are encouraged without asking.

## Layout

- `docs/` — how the pipeline works, operational notes
- `specs/` — what we're building: requirements, prompt design, model choices
