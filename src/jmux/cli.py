from __future__ import annotations

import argparse
from pathlib import Path

from jmux.generator import find_streamable_models, generate_jmux_code


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="jmux",
        description="JMux CLI for generating JMux classes from Pydantic models",
    )
    subparsers = parser.add_subparsers(dest="command")

    gen_parser = subparsers.add_parser(
        "generate",
        help="Generate JMux classes from StreamableBaseModel subclasses",
    )
    gen_parser.add_argument(
        "--root",
        default=".",
        help="Root directory to scan for StreamableBaseModel subclasses",
    )
    gen_parser.set_defaults(func=generate_command)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return

    args.func(args)


def generate_command(args: argparse.Namespace) -> None:
    root = Path(args.root).resolve()
    print(f"Scanning for StreamableBaseModel subclasses in: {root}")

    models = find_streamable_models(root)

    if not models:
        print("No StreamableBaseModel subclasses found.")
        return

    print(f"Found {len(models)} model(s): {', '.join(m.__name__ for m in models)}")

    code = generate_jmux_code(models)

    output_path = Path(__file__).parent / "generated" / "__init__.py"
    output_path.parent.mkdir(exist_ok=True)
    output_path.write_text(code)

    print(f"Generated JMux classes written to: {output_path}")


if __name__ == "__main__":
    main()
