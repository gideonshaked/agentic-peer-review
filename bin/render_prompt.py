#!/usr/bin/env python3
"""Render the audit prompt template with provided variables.

Usage:
    render-prompt --language PY --working-dir /path --round-num 1 --total-rounds 3 \
        --checks bugs,security [--framework django] [--instructions "..."] \
        [--focus src/] [--prior-fixes "..."] [--skipped-findings "..."]

All values are passed as CLI arguments directly.
"""

import argparse
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from bin.list_checks import load_check

PROMPTS_DIR = Path(__file__).parent / "prompts"


def main():
    parser = argparse.ArgumentParser(description="Render audit prompt")
    parser.add_argument("--language", required=True)
    parser.add_argument("--framework", default="")
    parser.add_argument("--working-dir", required=True)
    parser.add_argument("--instructions", default="")
    parser.add_argument("--focus", default="")
    parser.add_argument("--checks", required=True, help="Comma-separated check names")
    parser.add_argument("--round-num", type=int, required=True)
    parser.add_argument("--total-rounds", type=int, required=True)
    parser.add_argument("--prior-fixes", default="", help="Prior fixes summary text")
    parser.add_argument(
        "--skipped-findings", default="", help="Skipped findings summary text"
    )
    args = parser.parse_args()

    check_names = [c.strip() for c in args.checks.split(",") if c.strip()]
    checks = [{"name": name, "description": load_check(name)} for name in check_names]

    data = {
        "language": args.language,
        "framework": args.framework,
        "working_dir": args.working_dir,
        "instructions": args.instructions,
        "focus": args.focus,
        "checks": checks,
        "round_num": args.round_num,
        "total_rounds": args.total_rounds,
        "prior_fixes": args.prior_fixes,
        "skipped_findings": args.skipped_findings,
    }

    env = Environment(loader=FileSystemLoader(PROMPTS_DIR), keep_trailing_newline=True)
    template = env.get_template("audit.j2")
    print(template.render(data))


if __name__ == "__main__":
    main()
