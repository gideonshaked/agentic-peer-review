#!/usr/bin/env python3
"""Unified CLI entrypoint for agentic-peer-review.

Usage: peer-review-cli <subcommand> [args...]

Subcommands:
    init             Initialize session (parse args, detect project, create log, setup worktree)
    review-round     Build audit prompt, print round header, run review agent
    finalize         Finalize session (summary box, optional markdown log)
    change-log       Manage the JSON change log
    git-diff         Capture git diff as JSON
    worktree         Manage git worktrees (setup, commit, merge, teardown)
"""

import sys


SUBCOMMANDS = {
    "init": "bin.commands.init",
    "review-round": "bin.commands.review_round",
    "change-log": "bin.commands.change_log",
    "git-diff": "bin.commands.git_diff",
    "worktree": "bin.commands.worktree",
}

# finalize is a shortcut handled separately in main() — list it for --help
ALL_COMMANDS = sorted(list(SUBCOMMANDS) + ["finalize"])


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__.strip())
        print(f"\nAvailable subcommands: {', '.join(ALL_COMMANDS)}")
        sys.exit(0)

    if sys.argv[1] in ("-V", "--version"):
        from importlib.metadata import version

        print(version("agentic-peer-review"))
        sys.exit(0)

    cmd = sys.argv[1]

    # Shortcut: "finalize" → "change-log finalize"
    if cmd == "finalize":
        sys.argv = ["peer-review-cli finalize"] + sys.argv[2:]
        from bin.commands.change_log import cmd_finalize

        cmd_finalize()
        sys.exit(0)

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
