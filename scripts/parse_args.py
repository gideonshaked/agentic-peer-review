#!/usr/bin/env python3
"""Argument parser for the agent-peer-review plugin."""
import argparse
import json
import shutil
import sys


def main():
    parser = argparse.ArgumentParser(
        prog="peer-review",
        description="Iterative AI peer review with fix cycles",
    )
    parser.add_argument(
        "--model",
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
        "focus",
        nargs="*",
        help="Optional focus area or file path",
    )

    args = parser.parse_args()

    if not 1 <= args.max_rounds <= 10:
        parser.error("--max-rounds must be between 1 and 10")

    # Check if the chosen CLI is installed (claude is always available in-session)
    if args.model != "claude":
        install_hints = {
            "codex": "Install Codex CLI: npm install -g @openai/codex",
            "gemini": "Install Gemini CLI: see https://github.com/google-gemini/gemini-cli",
        }
        if shutil.which(args.model) is None:
            result = {
                "error": True,
                "message": f"{args.model} CLI not found. {install_hints[args.model]}",
            }
            print(json.dumps(result))
            sys.exit(0)  # exit 0 so Claude can read the error message

    result = {
        "error": False,
        "model": args.model,
        "max_rounds": args.max_rounds,
        "focus": " ".join(args.focus) if args.focus else "",
    }
    print(json.dumps(result))


if __name__ == "__main__":
    main()
