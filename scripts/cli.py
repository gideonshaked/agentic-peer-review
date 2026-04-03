#!/usr/bin/env python3
"""Unified CLI entrypoint for agentic-peer-review.

Usage: peer-review-cli <subcommand> [args...]

Subcommands:
    parse-args       Parse skill arguments
    detect-project   Detect project language and framework
    list-checks      List available checks
    render-prompt    Render the audit prompt (reads JSON from stdin)
    run-review       Run the review agent (reads prompt from stdin)
    format-output    Render formatted output (settings, round-header, summary)
    change-log       Manage the JSON change log (init, add-round, finalize, render-md)
    git-diff         Capture git diff as JSON
    worktree         Manage git worktrees (setup, commit, merge, teardown)
"""

import sys


SUBCOMMANDS = {
    "parse-args": "scripts.parse_args",
    "detect-project": "scripts.detect_project",
    "list-checks": "scripts.list_checks",
    "render-prompt": "scripts.render_prompt",
    "run-review": "scripts.run_review",
    "format-output": "scripts.format_output",
    "change-log": "scripts.change_log",
    "git-diff": "scripts.git_diff",
    "worktree": "scripts.worktree",
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__.strip())
        print(f"\nAvailable subcommands: {', '.join(sorted(SUBCOMMANDS))}")
        sys.exit(0)

    cmd = sys.argv[1]
    if cmd not in SUBCOMMANDS:
        print(f"Unknown subcommand: {cmd}", file=sys.stderr)
        print(f"Available: {', '.join(sorted(SUBCOMMANDS))}", file=sys.stderr)
        sys.exit(1)

    # Shift argv so the subcommand's main() sees its own args
    sys.argv = [f"peer-review-cli {cmd}"] + sys.argv[2:]

    module = __import__(SUBCOMMANDS[cmd], fromlist=["main"])
    module.main()


if __name__ == "__main__":
    main()
