#!/usr/bin/env python3
"""Render the audit prompt template with provided variables.

Usage:
    render-prompt --language PY --working-dir /path --round-num 1 --total-rounds 3 \
        --checks bugs,security [--framework django] [--instructions "..."] \
        [--focus src/]

Prints the round header to stderr (so Claude sees it), then the rendered
prompt to stdout (piped to run-review). Prior fixes and skipped findings
are read automatically from the session change log.
"""

import argparse
import json
import os
import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from bin.change_log import session_log_path
from bin.format_output import cmd_round_header
from bin.list_checks import load_check

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

    # Print round header to stderr (visible to Claude, not piped to run-review)
    elapsed = None
    log_path = session_log_path()
    if os.path.exists(log_path):
        with open(log_path, encoding="utf-8") as f:
            log_data = json.load(f)
        started_at = log_data.get("meta", {}).get("started_at", "")
        if started_at:
            from datetime import datetime, timezone

            start_dt = datetime.fromisoformat(started_at)
            elapsed = (datetime.now(timezone.utc) - start_dt).total_seconds()

    # Capture header output and print to stderr
    import io
    from contextlib import redirect_stdout

    buf = io.StringIO()
    with redirect_stdout(buf):
        cmd_round_header(args.round_num, args.total_rounds, elapsed)
    print(buf.getvalue(), file=sys.stderr, end="")

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
