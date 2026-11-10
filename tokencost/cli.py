"""Command-line interface for tokencost."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .pricing import (
    PricingError,
    available_models,
    load_pricing,
    resolve_model,
)
from .report import FileCount, Report, render_text
from .scan import read_file_text, scan_tree
from .tokenizer import DEFAULT_CHARS_PER_TOKEN, DEFAULT_METHOD, METHODS, estimate_tokens

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_USAGE = 2


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="tokencost",
        description="Estimate token counts and LLM cost for text, files, stdin or a repo.",
        epilog=(
            "examples:\n"
            "  tokencost --text 'hello world'\n"
            "  tokencost README.md -m medium\n"
            "  git diff | tokencost -\n"
            "  tokencost ./src --include '*.py' --json\n"
            "  tokencost ./ -m medium --output-tokens 500 --by-file\n\n"
            "Prices shipped are UNVERIFIED placeholders. Override with --pricing "
            "and verify against the provider. Token counts are heuristic estimates."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "sources",
        nargs="*",
        metavar="SOURCE",
        help="files or directories to measure; '-' reads stdin (default if piped)",
    )
    p.add_argument("--text", help="measure this literal string instead of a file")
    p.add_argument(
        "-m",
        "--model",
        action="append",
        dest="models",
        metavar="NAME",
        help="price this model (repeatable); default: every model in the table",
    )
    p.add_argument(
        "--method",
        choices=METHODS,
        default=DEFAULT_METHOD,
        help=f"token estimation method (default: {DEFAULT_METHOD})",
    )
    p.add_argument(
        "--chars-per-token",
        type=float,
        default=DEFAULT_CHARS_PER_TOKEN,
        metavar="N",
        help=f"divisor for --method chars (default: {DEFAULT_CHARS_PER_TOKEN})",
    )
    p.add_argument(
        "--pricing",
        metavar="FILE",
        help="JSON price table to merge over the defaults",
    )
    p.add_argument(
        "--output-tokens",
        type=int,
        default=0,
        metavar="N",
        help="assumed completion tokens, priced at the output rate (default: 0)",
    )
    p.add_argument(
        "--include",
        action="append",
        default=[],
        metavar="GLOB",
        help="only include files matching this glob (repeatable, repo mode)",
    )
    p.add_argument(
        "--exclude",
        action="append",
        default=[],
        metavar="GLOB",
        help="skip files matching this glob (repeatable, repo mode)",
    )
    p.add_argument(
        "--no-gitignore",
        action="store_true",
        help="do not honour .gitignore files when scanning directories",
    )
    p.add_argument(
        "--by-file",
        action="store_true",
        help="show a per-file token breakdown",
    )
    p.add_argument("--json", action="store_true", help="emit a stable JSON object")
    p.add_argument(
        "--list-models",
        action="store_true",
        help="print the models in the active price table and exit",
    )
    p.add_argument("-v", "--verbose", action="store_true", help="more detail")
    p.add_argument("--version", action="version", version=f"tokencost {__version__}")
    return p


def _gather_counts(args, method_kwargs) -> tuple[int, list[FileCount]]:
    total = 0
    files: list[FileCount] = []

    def count(text: str) -> int:
        return estimate_tokens(text, **method_kwargs)

    if args.text is not None:
        total += count(args.text)

    sources = list(args.sources)
    if not sources and args.text is None and not sys.stdin.isatty():
        sources = ["-"]

    for src in sources:
        if src == "-":
            total += count(sys.stdin.read())
            continue
        path = Path(src)
        if not path.exists():
            raise FileNotFoundError(f"no such file or directory: {src}")
        if path.is_dir():
            for sf in scan_tree(
                path,
                use_gitignore=not args.no_gitignore,
                include=args.include,
                exclude=args.exclude,
            ):
                tokens = count(sf.text)
                total += tokens
                files.append(FileCount(path=sf.path, tokens=tokens))
        else:
            tokens = count(read_file_text(path))
            total += tokens
            files.append(FileCount(path=str(path), tokens=tokens))

    if args.text is None and not sources:
        raise ValueError("no input: pass a file, a directory, --text, or pipe stdin")

    return total, files


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        table = load_pricing(args.pricing)
    except PricingError as exc:
        print(f"tokencost: {exc}", file=sys.stderr)
        return EXIT_ERROR

    if args.list_models:
        names = available_models(table)
        if args.json:
            print(json.dumps({"models": names}, indent=2))
        else:
            for n in names:
                print(n)
        return EXIT_OK

    model_names = args.models or available_models(table)
    try:
        prices = [resolve_model(table, n) for n in model_names]
    except PricingError as exc:
        print(f"tokencost: {exc}", file=sys.stderr)
        return EXIT_ERROR

    if args.output_tokens < 0:
        print("tokencost: --output-tokens must be >= 0", file=sys.stderr)
        return EXIT_USAGE

    method_kwargs = {"method": args.method, "chars_per_token": args.chars_per_token}
    try:
        total, files = _gather_counts(args, method_kwargs)
    except (FileNotFoundError, ValueError) as exc:
        print(f"tokencost: {exc}", file=sys.stderr)
        return EXIT_ERROR
    except OSError as exc:
        print(f"tokencost: {exc}", file=sys.stderr)
        return EXIT_ERROR

    report = Report(
        method=args.method,
        currency=table["currency"],
        per_tokens=int(table["per_tokens"]),
        input_tokens=total,
        output_tokens=args.output_tokens,
        prices=prices,
        files=files,
    )

    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print(render_text(report, by_file=args.by_file or args.verbose))
    return EXIT_OK
