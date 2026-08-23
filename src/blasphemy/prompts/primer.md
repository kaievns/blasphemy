You receive a book's chapter list: titles, word counts, and the opening words
of each chapter. Produce a compact book primer that will be provided as
context every time one chapter of this book is rewritten in isolation.

The primer must contain, in markdown:

1. **Arc** — 2–3 sentences: what the book argues/teaches and how it
   progresses.
2. **Chapters** — one line per chapter: `N. Title — scope/purpose`.
3. **Canonical terminology** — the recurring technical terms a rewriter must
   keep consistent across chapters (term: one-line meaning). Only terms that
   recur across chapters.

Output ONLY the primer as markdown. No preamble. Keep it under ~600 words —
it is context overhead on every chapter.
