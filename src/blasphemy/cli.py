import argparse
import json
import sys
from importlib import resources
from pathlib import Path

from . import check, epub, pipeline, polish, primer, providers, report, style


def default_prompt(name: str = "body") -> str:
    return (resources.files("blasphemy") / "prompts" / f"{name}.md").read_text()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="blasphemy",
        description="Optimise an epub for readability via an agent CLI.",
    )
    parser.add_argument("epub", type=Path, nargs="?")
    parser.add_argument("-o", "--output", type=Path)
    parser.add_argument(
        "--provider",
        default=providers.DEFAULT.name,
        choices=list(providers.REGISTRY),
        help=f"agent CLI to drive (default: {providers.DEFAULT.name})",
    )
    parser.add_argument(
        "--check-providers",
        action="store_true",
        help="report which agent CLIs are usable and exit",
    )
    parser.add_argument("--model", help="provider-specific model name")
    parser.add_argument("--effort", choices=["low", "medium", "high", "xhigh", "max"])
    parser.add_argument("--prompt", type=Path)
    parser.add_argument("--min-words", type=int, default=200)
    parser.add_argument(
        "--skip", default="", help="comma-separated chapter indices to pass through"
    )
    parser.add_argument(
        "--only", default="", help="comma-separated chapter indices to rewrite; all others pass through"
    )
    parser.add_argument(
        "--timeout", type=int, default=2400,
        help="seconds per agent call (default 2400 — xhigh effort on a large "
        "chapter can exceed 20 minutes)",
    )
    parser.add_argument("--force", action="store_true")
    parser.add_argument(
        "--rebuild", action="store_true",
        help="reassemble the epub from cached rewrites only; never calls an "
        "agent, uncached chapters keep their original text",
    )
    parser.add_argument("--no-primer", action="store_true", help="skip book primer")
    parser.add_argument(
        "--no-polish", action="store_true",
        help="skip the second pass that removes repetition and restores the author's voice",
    )
    parser.add_argument(
        "--no-check", action="store_true",
        help="skip the pass that checks the chapter's opening against the original",
    )
    parser.add_argument("--list", action="store_true", help="list chapters and exit")
    return parser


def check_providers() -> int:
    for name, provider in providers.REGISTRY.items():
        found = providers.available(provider)
        model = provider.default_model or "(provider default)"
        if provider.default_effort:
            model += f" @ {provider.default_effort}"
        print(
            f"{name:8s} {'ok' if found else 'missing':8s} "
            f"{providers.binary_for(provider)}  model: {model}"
        )
    return 0 if any(providers.available(p) for p in providers.REGISTRY.values()) else 1


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.check_providers:
        return check_providers()
    if args.epub is None:
        print("error: an epub path is required", file=sys.stderr)
        return 2
    if not args.epub.exists():
        print(f"not found: {args.epub}", file=sys.stderr)
        return 1

    if args.list:
        for chapter in epub.chapters(epub.load(args.epub)):
            print(f"{chapter.index:3d}  {chapter.words:6d}w  {chapter.href}  {chapter.title}")
        return 0

    provider = providers.resolve(args.provider)
    if not args.rebuild and not providers.available(provider):
        other = next(n for n in providers.REGISTRY if n != provider.name)
        print(
            f"error: {providers.binary_for(provider)} not found — install it, set "
            f"BLASPHEMY_{provider.name.upper()}_BIN, or use --provider {other}",
            file=sys.stderr,
        )
        return 1

    body_prompt = args.prompt.read_text() if args.prompt else default_prompt("body")
    polish_prompt = default_prompt("polish")
    check_prompt = default_prompt("check")
    out_path = args.output or args.epub.with_suffix(".optimised.epub")
    workdir = pipeline.workdir_for(args.epub)

    chapters = epub.chapters(epub.load(args.epub))
    reporter = report.Reporter(len(chapters))
    effort = args.effort or provider.default_effort
    reporter.note(
        f"{args.epub.name} — {len(chapters)} documents · "
        + (
            "rebuild from cache, no agent calls"
            if args.rebuild
            else f"{provider.name} · "
            f"{args.model or provider.default_model or 'provider default'}"
            + (f" · {effort}" if effort else "")
        )
    )

    def call_agent(payload: str, system: str) -> str:
        if args.rebuild:
            raise RuntimeError("not cached; rerun without --rebuild to rewrite")
        return providers.rewrite(
            payload, system, provider=provider,
            model=args.model, effort=args.effort, timeout=args.timeout,
        )

    book_primer = ""
    if not args.no_primer and not args.rebuild:
        reporter.start("building book primer")
        book_primer = primer.build(
            chapters,
            lambda text: call_agent(text, default_prompt("primer")),
            workdir,
            force=args.force,
            min_words=args.min_words,
        )
        reporter.note(f"primer ready ({len(book_primer.split())} words)")

    def with_context(base: str, chapter: epub.Chapter) -> str:
        if book_primer:
            return base + primer.chapter_context(book_primer, chapter)
        return base

    def second_pass(chapter_md: str, body: str, index: int) -> str:
        record = pipeline.polish_record(workdir, index)
        record.unlink(missing_ok=True)
        if args.no_polish:
            return body
        try:
            polished, report_ = polish.polish(
                chapter_md, body, lambda text: call_agent(text, polish_prompt)
            )
        except Exception as error:
            record.write_text(json.dumps({"error": str(error)}, indent=1))
            return body
        record.write_text(json.dumps(report_, indent=1, ensure_ascii=False))
        return polished

    def rewrite(chapter_md: str, chapter: epub.Chapter) -> str:
        words = len(chapter_md.split())
        contract = (
            f"\n\n[Length contract: the chapter above is {words} words; your "
            f"rewritten chapter must be {int(words * 0.55)}-{int(words * 0.70)} "
            f"words. Exceed only where a cut would damage comprehension of the "
            f"main argument.]"
        )
        body = call_agent(chapter_md + contract, with_context(body_prompt, chapter))
        slipped = style.banned(chapter_md, body)
        if slipped:
            note = (
                f"\n\n[Your previous attempt used the banned word(s): "
                f"{', '.join(slipped)}. Rewrite without them.]"
            )
            body = call_agent(
                chapter_md + contract + note, with_context(body_prompt, chapter)
            )
        problem = pipeline.body_problem(chapter_md, body)
        if problem:
            failed = pipeline.chapter_file(workdir, chapter.index, "failed")
            failed.write_text(body)
            raise ValueError(f"{problem}, see {failed}")
        body = second_pass(chapter_md, body, chapter.index)
        record = pipeline.check_record(workdir, chapter.index)
        record.unlink(missing_ok=True)
        if args.no_check:
            return body
        try:
            patched, report_ = check.patch(
                chapter_md, body, lambda text: call_agent(text, check_prompt)
            )
        except Exception as error:
            record.write_text(json.dumps({"error": str(error)}, indent=1))
            return body
        if pipeline.body_problem(chapter_md, patched):
            report_["reverted"] = pipeline.body_problem(chapter_md, patched)
            patched = body
        record.write_text(json.dumps(report_, indent=1, ensure_ascii=False))
        return patched

    try:
        results = pipeline.optimise(
            args.epub, out_path, rewrite, workdir,
            min_words=args.min_words, force=args.force, rebuild=args.rebuild,
            progress=reporter.finish,
            starting=lambda chapter: reporter.start(
                chapter.title or chapter.href
            ),
            skip={int(i) for i in args.skip.split(",") if i.strip()},
            only={int(i) for i in args.only.split(",") if i.strip()} or None,
        )
    except KeyboardInterrupt:
        reporter.close()
        print("\ninterrupted — rerun to resume from cache", file=sys.stderr)
        return 130
    finally:
        reporter.close()

    print(reporter.summary(out_path, workdir))
    return 1 if any(r.status == "failed" for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
