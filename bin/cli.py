#!/usr/bin/env python3
"""Unified CLI entrypoint for agentic-peer-review.

Usage: peer-review-cli <subcommand> [args...]

Subcommands:
    init             Initialize session (parse args, detect project, create log, setup worktree)
    parse-args       Parse skill arguments (standalone, used by init internally)
    detect-project   Detect project language and framework
    list-checks      List available checks
    render-prompt    Render the audit prompt
    run-review       Run the review agent (reads prompt from stdin)
    format-output    Render formatted output (settings, round-header, summary)
    change-log       Manage the JSON change log
    git-diff         Capture git diff as JSON
    worktree         Manage git worktrees (setup, commit, merge, teardown)
"""

import sys


SUBCOMMANDS = {
    "init": "bin.init",
    "parse-args": "bin.parse_args",
    "detect-project": "bin.detect_project",
    "list-checks": "bin.list_checks",
    "render-prompt": "bin.render_prompt",
    "run-review": "bin.run_review",
    "format-output": "bin.format_output",
    "change-log": "bin.change_log",
    "git-diff": "bin.git_diff",
    "worktree": "bin.worktree",
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__.strip())
        print(f"\nAvailable subcommands: {', '.join(sorted(SUBCOMMANDS))}")
        sys.exit(0)

    if sys.argv[1] in ("-V", "--version"):
        from importlib.metadata import version

        print(version("agentic-peer-review"))
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
