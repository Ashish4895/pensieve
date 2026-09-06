#!/usr/bin/env python3
import argparse
import subprocess
from pathlib import Path


BACKEND = Path(__file__).resolve().parent / "services" / "backend"
COMMANDS = {
    "backend-check": ["python", "manage.py", "check"],
    "test": ["pytest"],
    "migrate": ["python", "manage.py", "migrate"],
    "setup": ["python", "manage.py", "setup_application"],
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Pensieve developer commands")
    parser.add_argument(
        "command",
        nargs="?",
        choices=["help", *COMMANDS],
        default="help",
    )
    parser.add_argument("args", nargs=argparse.REMAINDER)
    args = parser.parse_args()

    if args.command == "help":
        parser.print_help()
        return 0

    return subprocess.call(["uv", "run", *COMMANDS[args.command], *args.args], cwd=BACKEND)


if __name__ == "__main__":
    raise SystemExit(main())
