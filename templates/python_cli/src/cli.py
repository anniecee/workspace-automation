"""CLI entry points and commands."""

import argparse
import sys
from collections.abc import Sequence


def build_parser() -> argparse.ArgumentParser:
    """Construct CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="{{project_name}}",
        description="{{project_description}}",
    )
    parser.add_argument(
        "-v", "--version",
        action="version",
        version="%(prog)s 0.1.0",
    )
    subparsers = parser.add_subparsers(dest="command", help="Subcommands")

    # Example subcommand: hello
    hello_parser = subparsers.add_parser("hello", help="Print a greeting")
    hello_parser.add_argument("--name", default="World", help="Name to greet")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """CLI execution entrypoint."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 0

    if args.command == "hello":
        print(f"Hello, {args.name}!")
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
