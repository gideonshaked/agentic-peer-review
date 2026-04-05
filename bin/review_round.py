#!/usr/bin/env python3
"""Build the audit prompt and run an external AI agent to review the codebase.

Prints the round header to stderr, builds the prompt from CLI args and
the session change log, invokes the agent, and prints the review output.

Usage:
    run-review --agent claude --timeout 300 --language Python --working-dir /path \
        --checks bugs,security --round-num 1 --total-rounds 3 \
        [--framework django] [--instructions "..."] [--focus src/]
"""

import argparse
import io
import json
import os
import subprocess
import sys
from contextlib import redirect_stdout
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from bin.change_log import session_log_path
from bin.format_output import cmd_round_header
from bin.list_checks import load_check

PROMPTS_DIR = Path(__file__).parent / "prompts"

AGENT_COMMANDS = {
    "claude": ["claude", "-p", "--allowedTools", "Read Glob Grep"],
    "codex": ["codex", "exec", "-s", "read-only", "-"],
    "gemini": ["gemini", "--sandbox", "--output-format", "text", "-p"],
}

DEFAULT_TIMEOUT = 300


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


def _render_prompt(args):
    """Build the audit prompt from CLI args and session state."""
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
    return template.render(data)


def _print_round_header(round_num, total_rounds):
    """Print round header to stderr from session timing data."""
    elapsed = None
    log_path = session_log_path()
    if os.path.exists(log_path):
        with open(log_path, encoding="utf-8") as f:
            log_data = json.load(f)
        started_at = log_data.get("meta", {}).get("started_at", "")
        if started_at:
            start_dt = datetime.fromisoformat(started_at)
            elapsed = (datetime.now(timezone.utc) - start_dt).total_seconds()

    buf = io.StringIO()
    with redirect_stdout(buf):
        cmd_round_header(round_num, total_rounds, elapsed)
    print(buf.getvalue(), file=sys.stderr, end="")


def main():
    parser = argparse.ArgumentParser(
        description="Build audit prompt and run review agent"
    )
    parser.add_argument(
        "--agent",
        choices=list(AGENT_COMMANDS),
        default="claude",
        help="AI agent to use",
    )
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    parser.add_argument("--language", required=True)
    parser.add_argument("--framework", default="")
    parser.add_argument("--working-dir", required=True)
    parser.add_argument("--instructions", default="")
    parser.add_argument("--focus", default="")
    parser.add_argument("--checks", required=True, help="Comma-separated check names")
    parser.add_argument("--round-num", type=int, required=True)
    parser.add_argument("--total-rounds", type=int, required=True)
    args = parser.parse_args()

    # Print round header
    _print_round_header(args.round_num, args.total_rounds)

    # Build prompt
    prompt = _render_prompt(args)

    if not prompt.strip():
        print("Error: empty prompt", file=sys.stderr)
        sys.exit(1)

    # Invoke agent
    cmd = list(AGENT_COMMANDS[args.agent])

    if args.agent == "gemini":
        cmd.append(prompt)
        stdin_data = None
    else:
        stdin_data = prompt

    try:
        result = subprocess.run(
            cmd,
            input=stdin_data,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=args.timeout,
        )
    except FileNotFoundError:
        print(f"Error: {args.agent} CLI not found", file=sys.stderr)
        sys.exit(1)
    except subprocess.TimeoutExpired:
        print(f"Error: {args.agent} timed out after {args.timeout}s", file=sys.stderr)
        sys.exit(1)

    err = result.stderr.strip()
    if err:
        print(err, file=sys.stderr)

    if result.returncode != 0:
        print(
            f"Error: {args.agent} exited with code {result.returncode}", file=sys.stderr
        )
        sys.exit(result.returncode)

    output = result.stdout.strip()
    if output:
        print(output)


if __name__ == "__main__":
    main()
