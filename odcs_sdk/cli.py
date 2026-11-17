"""
ODCS Python SDK Command Line Interface
"""

import argparse
import sys
import os
from . import __version__, __standard__, star, haven, ContinuityBridge


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="odcs",
        description=f"ODCS Official Python SDK CLI ({__standard__} · Dual Engine: Star + Haven)"
    )
    sub = parser.add_subparsers(dest="cmd")

    # Star subcommands
    p_star = sub.add_parser("star", help="Execute or analyze Star source code")
    p_star.add_argument("file", help="Path to .star file")
    p_star.add_argument("--wasm", action="store_true", help="Compile to WebAssembly (app.wasm)")
    p_star.add_argument("--check", action="store_true", help="Run semantic check only")

    # Haven subcommands
    p_haven = sub.add_parser("haven", help="Execute, lint, or transpile Haven source code")
    p_haven.add_argument("file", help="Path to .hvn file")
    p_haven.add_argument("--transpile", action="store_true", help="Print transpiled Python code")
    p_haven.add_argument("--lint", action="store_true", help="Verify syntax without executing")

    # Info / Doctor
    sub.add_parser("info", help="Display ODCS SDK version, engines, and toolchain paths")

    args = parser.parse_args()

    if args.cmd == "info":
        print(f"🌟 ODCS Official Python SDK (v{__version__})")
        print(f"   Standard:        {__standard__}")
        print(f"   Star Toolchain:  {'ONLINE' if star.STAR_AVAILABLE else 'OFFLINE'} ({star.STAR_SDK_DIR})")
        print(f"   Haven Toolchain: {'ONLINE' if haven.HAVEN_AVAILABLE else 'OFFLINE'}")
        return 0

    if args.cmd == "star":
        if args.wasm:
            out = "app.wasm"
            wasm_bytes = star.compile_wasm(args.file)
            with open(out, "wb") as f:
                f.write(wasm_bytes)
            print(f"✓ Compiled '{args.file}' to WebAssembly: {out} ({len(wasm_bytes):,} bytes)")
            return 0
        if args.check:
            star.check(args.file)
            print(f"✓ Checks passed for '{args.file}'")
            return 0
        star.run_file(args.file)
        return 0

    if args.cmd == "haven":
        if args.transpile:
            print(haven.compile(args.file, include_prelude=False))
            return 0
        if args.lint:
            haven.lint(args.file)
            print(f"✓ Syntax verified for '{args.file}'")
            return 0
        haven.run(args.file)
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())

