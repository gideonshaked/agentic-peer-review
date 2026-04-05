#!/usr/bin/env python3
"""Render the audit prompt template with provided variables.

Usage:
    render-prompt --language PY --working-dir /path --round-num 1 --total-rounds 3 \
        --checks bugs,security [--framework django] [--instructions "..."] \
        [--focus src/]

Prior fixes and skipped findings are read automatically from the session
change log — no need to pass them as arguments.
"""

import argparse
import json
import os
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from bin.list_checks import load_check
from bin.change_log import session_log_path

PROMPTS_DIR = Path(__file__).parent / "prompts"


def _read_prior_context(round_num):
    """Read prior fixes and skipped findings from the session change log."""
    prior_fixes = ""
    skipped_findings = ""

    if round_num <= 1:
        return prior_fixes, skipped_findings

    log_path = session_log_path()
    if not os.path.exists(log_path):
        return prior_fixes, skipped_findings

    with open(log_path, encoding="utf-8") as f:
        data = json.load(f)

    fix_lines = []
    skip_lines = []
    for rnd in data.get("rounds", []):
        for fix in rnd.get("fixes", []):
            fix_lines.append(
                f"- [{fix.get('finding_id', '')}] {fix.get('file', '')}: "
                f"{fix.get('what_changed', '')} ({fix.get('why', '')})"
            )
        for skip in rnd.get("skipped", []):
            skip_lines.append(
                f"- [{skip.get('finding_id', '')}] {skip.get('file', '')} "
                f"({skip.get('severity', '')}): {skip.get('reason', '')}"
            )

    if fix_lines:
        prior_fixes = "\n".join(fix_lines)
    if skip_lines:
        skipped_findings = "\n".join(skip_lines)

    return prior_fixes, skipped_findings


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
    args = parser.parse_args()

    prior_fixes, skipped_findings = _read_prior_context(args.round_num)

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
