#!/usr/bin/env python3
import argparse
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "services" / "backend"
FRONTEND = ROOT / "services" / "frontend"

BACKEND_COMMANDS = {
    "backend-check": ["python", "manage.py", "check"],
    "test": ["pytest"],
    "migrate": ["python", "manage.py", "migrate"],
    "setup": ["python", "manage.py", "setup_application"],
    "start": ["python", "manage.py", "start_server"],
    "celery-worker": ["celery", "-A", "pensieve", "worker", "--loglevel=INFO"],
}

FRONTEND_COMMANDS = {
    "frontend-dev": ["npm", "run", "dev"],
    "frontend-test": ["npm", "test", "--", "--run"],
    "frontend-build": ["npm", "run", "build"],
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Pensieve developer commands")
    parser.add_argument(
        "command",
        nargs="?",
        choices=["help", *BACKEND_COMMANDS, *FRONTEND_COMMANDS],
        default="help",
    )
    parser.add_argument("args", nargs=argparse.REMAINDER)
    args = parser.parse_args()

    if args.command == "help":
        parser.print_help()
        return 0

    if args.command in FRONTEND_COMMANDS:
        return subprocess.call(
            [*FRONTEND_COMMANDS[args.command], *args.args],
            cwd=FRONTEND,
        )

    return subprocess.call(
        ["uv", "run", *BACKEND_COMMANDS[args.command], *args.args],
        cwd=BACKEND,
    )


if __name__ == "__main__":
    raise SystemExit(main())
