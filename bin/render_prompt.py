#!/usr/bin/env python3
"""Render the audit prompt template with provided variables.

Usage:
    render-prompt --language PY --working-dir /path --round-num 1 --total-rounds 3 \
        --checks bugs,security [--framework django] [--instructions "..."] \
        [--focus src/] [--prior-fixes-file /tmp/fixes.txt] \
        [--skipped-findings-file /tmp/skipped.txt]

All simple string args are passed directly. Multi-line values (prior_fixes,
skipped_findings) are read from files to avoid shell escaping issues.
"""

import argparse
import sys
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
    parser.add_argument(
        "--prior-fixes-file",
        default="",
        help="Path to file containing prior fixes summary",
    )
    parser.add_argument(
        "--skipped-findings-file",
        default="",
        help="Path to file containing skipped findings summary",
    )
    args = parser.parse_args()

    prior_fixes = ""
    if args.prior_fixes_file:
        prior_fixes = Path(args.prior_fixes_file).read_text(encoding="utf-8").strip()

    skipped_findings = ""
    if args.skipped_findings_file:
        skipped_findings = (
            Path(args.skipped_findings_file).read_text(encoding="utf-8").strip()
        )

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
        "prior_fixes": prior_fixes,
        "skipped_findings": skipped_findings,
    }

    env = Environment(loader=FileSystemLoader(PROMPTS_DIR), keep_trailing_newline=True)
    template = env.get_template("audit.j2")
    print(template.render(data))


if __name__ == "__main__":
    main()
