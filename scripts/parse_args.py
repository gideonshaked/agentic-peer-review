#!/usr/bin/env python3
"""Argument parser for the agentic-peer-review plugin."""

import argparse
import json
import shutil
import sys

from scripts.list_checks import get_available_checks


def main():
    parser = argparse.ArgumentParser(
        prog="peer-review",
        description="Iterative AI peer review that finds and fixes issues in your codebase",
        exit_on_error=False,
    )
    parser.add_argument(
        "--agent",
        choices=["claude", "codex", "gemini"],
        default="claude",
        help="AI agent to use for review (default: claude)",
    )
    parser.add_argument(
        "--max-rounds",
        type=int,
        default=5,
        help="Maximum review-fix cycles (default: 5). Stops early if no issues found.",
    )
    parser.add_argument(
        "--focus",
        default="",
        help="Narrow review scope to a specific file or directory path",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Timeout in seconds for each review agent invocation (default: 300)",
    )
    parser.add_argument(
        "--worktree",
        action="store_true",
        default=False,
        help="Run fixes in a git worktree; show diff at end and ask to merge or discard",
    )
    parser.add_argument(
        "--log",
        default="",
        help="Write findings and fix/skip decisions to the specified file",
    )
    all_checks = get_available_checks()
    parser.add_argument(
        "--only",
        default="",
        help=f"Comma-separated list of checks to run (default: all). Available: {', '.join(all_checks)}",
    )
    parser.add_argument(
        "instructions",
        nargs="?",
        default="",
        help="Optional review instructions",
    )

    try:
        args = parser.parse_args()
    except argparse.ArgumentError as e:
        result = {
            "error": True,
            "message": f"Invalid arguments: {e}",
        }
        print(json.dumps(result))
        sys.exit(0)

    if args.timeout < 1:
        result = {
            "error": True,
            "message": "--timeout must be a positive integer",
        }
        print(json.dumps(result))
        sys.exit(0)

    if args.max_rounds < 1:
        result = {
            "error": True,
            "message": "--max-rounds must be at least 1",
        }
        print(json.dumps(result))
        sys.exit(0)

    # Check if the chosen CLI is installed (claude is always available in-session)
    if args.agent != "claude":
        install_hints = {
            "codex": "Install Codex CLI: npm install -g @openai/codex",
            "gemini": "Install Gemini CLI: see https://github.com/google-gemini/gemini-cli",
        }
        if shutil.which(args.agent) is None:
            result = {
                "error": True,
                "message": f"{args.agent} CLI not found. {install_hints.get(args.agent, '')}",
            }
            print(json.dumps(result))
            sys.exit(0)

    # Resolve checks (all_checks already set above for --help text)
    if args.only:
        requested = [c.strip() for c in args.only.split(",")]
        invalid = [c for c in requested if c not in all_checks]
        if invalid:
            result = {
                "error": True,
                "message": f"Unknown check(s): {', '.join(invalid)}. Available: {', '.join(all_checks)}",
            }
            print(json.dumps(result))
            sys.exit(0)
        active_checks = requested
    else:
        active_checks = all_checks

    result = {
        "error": False,
        "agent": args.agent,
        "max_rounds": args.max_rounds,
        "instructions": args.instructions,
        "focus": args.focus,
        "timeout": args.timeout,
        "worktree": args.worktree,
        "log": args.log,
        "checks": active_checks,
        "all_checks": all_checks,
    }
    print(json.dumps(result))


if __name__ == "__main__":
    main()
