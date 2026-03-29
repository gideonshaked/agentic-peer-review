#!/usr/bin/env python3
"""Argument parser for the agentic-peer-review plugin."""
import argparse
import json
import shutil
import sys


def main():
    parser = argparse.ArgumentParser(
        prog="peer-review",
        description="Iterative AI peer review with fix cycles",
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
        help="Number of review-fix cycles, 1-10 (default: 5)",
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
    parser.add_argument(
        "message",
        nargs="?",
        default="",
        help="Optional review instructions (e.g. \"Check auth for SQL injection, skip tech debt\")",
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

    if not 1 <= args.max_rounds <= 10:
        result = {
            "error": True,
            "message": "--max-rounds must be between 1 and 10",
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
            sys.exit(0)  # exit 0 so Claude can read the error message

    msg_display = f'"{args.message}"' if args.message else "none"
    focus_display = f'"{args.focus}"' if args.focus else "none"
    flags = []
    if args.worktree:
        flags.append("worktree")
    if args.log:
        flags.append(f"log={args.log}")
    if args.timeout != 300:
        flags.append(f"timeout={args.timeout}s")
    flags_display = ", ".join(flags) if flags else "none"

    result = {
        "error": False,
        "agent": args.agent,
        "max_rounds": args.max_rounds,
        "message": args.message,
        "focus": args.focus,
        "timeout": args.timeout,
        "worktree": args.worktree,
        "log": args.log,
        "status": f"**Agent:** {args.agent} | **Max rounds:** {args.max_rounds} | **Focus:** {focus_display} | **Message:** {msg_display} | **Flags:** {flags_display}",
    }
    print(json.dumps(result))


if __name__ == "__main__":
    main()
