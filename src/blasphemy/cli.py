import argparse
import sys
from importlib import resources
from pathlib import Path

from . import apparatus, claude, epub, pipeline, primer


def default_prompt(name: str = "body") -> str:
    return (resources.files("blasphemy") / "prompts" / f"{name}.md").read_text()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="blasphemy", description="Optimise an epub for readability via Claude."
    )
    parser.add_argument("epub", type=Path)
    parser.add_argument("-o", "--output", type=Path)
    parser.add_argument("--model", default="opus")
    parser.add_argument("--effort", choices=["low", "medium", "high", "xhigh", "max"])
    parser.add_argument("--prompt", type=Path)
    parser.add_argument("--min-words", type=int, default=200)
    parser.add_argument(
        "--skip", default="", help="comma-separated chapter indices to pass through"
    )
    parser.add_argument(
        "--only", default="", help="comma-separated chapter indices to rewrite; all others pass through"
    )
    parser.add_argument("--timeout", type=int, default=1200)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--no-primer", action="store_true", help="skip book primer")
    parser.add_argument("--list", action="store_true", help="list chapters and exit")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.epub.exists():
        print(f"not found: {args.epub}", file=sys.stderr)
        return 1

    if args.list:
        for chapter in epub.chapters(epub.load(args.epub)):
            print(f"{chapter.index:3d}  {chapter.words:6d}w  {chapter.href}  {chapter.title}")
        return 0

    body_prompt = args.prompt.read_text() if args.prompt else default_prompt("body")
    apparatus_prompt = default_prompt("apparatus")
    out_path = args.output or args.epub.with_suffix(".optimised.epub")
    workdir = pipeline.workdir_for(args.epub)

    book_primer = ""
    if not args.no_primer:
        chapters = epub.chapters(epub.load(args.epub))
        book_primer = primer.build(
            chapters,
            lambda text: claude.rewrite(
                text, default_prompt("primer"),
                model=args.model, effort=args.effort, timeout=args.timeout,
            ),
            workdir,
            force=args.force,
            min_words=args.min_words,
        )
        print(f"primer ready ({len(book_primer.split())} words)", flush=True)

    def call_claude(payload: str, system: str) -> str:
        return claude.rewrite(
            payload, system,
            model=args.model, effort=args.effort, timeout=args.timeout,
        )

    def with_context(base: str, chapter: epub.Chapter) -> str:
        if book_primer:
            return base + primer.chapter_context(book_primer, chapter)
        return base

    def rewrite(chapter_md: str, chapter: epub.Chapter) -> str:
        words = len(chapter_md.split())
        contract = (
            f"\n\n[Length contract: the chapter above is {words} words; your "
            f"rewritten chapter must be {int(words * 0.55)}-{int(words * 0.70)} "
            f"words. Exceed only where a cut would damage comprehension of the "
            f"main argument.]"
        )
        body = call_claude(chapter_md + contract, with_context(body_prompt, chapter))
        budget = max(220, int(len(body.split()) * 0.10))
        raw = call_claude(
            f"{body}\n\n[Apparatus word cap: {budget} words total across all "
            f"sections — a contract.]",
            with_context(apparatus_prompt, chapter),
        )
        return apparatus.assemble(chapter_md, body, raw)

    def progress(result: pipeline.Result) -> None:
        line = (
            f"[{result.index:3d}] {result.status:9s} "
            f"{result.words_in:6d}w -> {result.words_out:6d}w  {result.title or result.item_id}"
        )
        if result.detail:
            line += f"  ({result.detail})"
        print(line, flush=True)

    results = pipeline.optimise(
        args.epub, out_path, rewrite, workdir,
        min_words=args.min_words, force=args.force, progress=progress,
        skip={int(i) for i in args.skip.split(",") if i.strip()},
        only={int(i) for i in args.only.split(",") if i.strip()} or None,
    )
    failed = sum(1 for r in results if r.status == "failed")
    print(f"\nwrote {out_path}  ({len(results)} chapters, {failed} failed, cache: {workdir})")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
