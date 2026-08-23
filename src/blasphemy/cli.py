import argparse
import sys
from importlib import resources
from pathlib import Path

from . import claude, epub, pipeline, primer


def default_prompt(name: str = "compress") -> str:
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

    compress_prompt = args.prompt.read_text() if args.prompt else default_prompt("compress")
    enhance_prompt = default_prompt("enhance")
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
        low, high = int(words * 0.4), int(words * 0.6)
        contract = (
            f"\n\n[Length contract: the chapter above is {words} words; your "
            f"compressed chapter must be {low}-{high} words.]"
        )
        compress_system = with_context(compress_prompt, chapter)
        compressed = call_claude(chapter_md + contract, compress_system)
        compressed_words = len(compressed.split())
        if compressed_words > int(words * 0.7):
            print(
                f"  shrink pass: draft {compressed_words}w > contract {low}-{high}w",
                flush=True,
            )
            shrink = (
                f"{compressed}\n\n[The draft above is {compressed_words} words; "
                f"the contract is {low}-{high} words. Compress it to contract by "
                f"dropping and merging passages. Keep all ⟦...⟧ tokens, headings, "
                f"code blocks, and facts. Output only the compressed chapter as "
                f"markdown.]"
            )
            shrunk = call_claude(shrink, compress_system)
            if low // 2 <= len(shrunk.split()) < compressed_words:
                compressed = shrunk
                compressed_words = len(compressed.split())
                print(f"  shrink accepted: {compressed_words}w", flush=True)
            else:
                print(f"  shrink rejected: {len(shrunk.split())}w", flush=True)

        cap = min(int(compressed_words * 1.3), int(words * 0.75))
        grow = (
            f"\n\n[Growth contract: the chapter above is {compressed_words} "
            f"words; your output with apparatus added must stay under {cap} "
            f"words total.]"
        )
        enhance_system = with_context(enhance_prompt, chapter)
        final = call_claude(compressed + grow, enhance_system)
        final_words = len(final.split())
        if not (compressed_words * 0.95 <= final_words <= cap):
            print(f"  apparatus retry: {final_words}w vs cap {cap}w", flush=True)
            retry = (
                f"{grow}\n[Your previous output was {final_words} words. Add "
                f"leaner apparatus: fewer questions, 1-2 sentence answers, "
                f"shorter Orient.]"
            )
            final = call_claude(compressed + retry, enhance_system)
            final_words = len(final.split())
            if not (compressed_words * 0.95 <= final_words <= cap):
                print(
                    f"  apparatus out of bounds ({final_words}w), keeping "
                    f"compressed body only",
                    flush=True,
                )
                return compressed
        return final

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
