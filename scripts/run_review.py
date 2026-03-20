#!/usr/bin/env python3
"""Run an external AI agent to review the codebase.

Reads the audit prompt from stdin, invokes the chosen CLI,
and prints the review output to stdout.
"""
import subprocess
import sys


AGENT_COMMANDS = {
    "claude": ["claude", "-p", "--allowedTools", "Read Glob Grep"],
    "codex": ["codex", "exec", "-s", "read-only", "-"],
    "gemini": ["gemini", "--sandbox", "--output-format", "text", "-p", ""],
}

TIMEOUT_SECONDS = 300


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in AGENT_COMMANDS:
        print(
            f"Usage: {sys.argv[0]} <claude|codex|gemini>  (reads prompt from stdin)",
            file=sys.stderr,
        )
        sys.exit(1)

    agent = sys.argv[1]
    prompt = sys.stdin.read()

    if not prompt.strip():
        print("Error: empty prompt on stdin", file=sys.stderr)
        sys.exit(1)

    cmd = list(AGENT_COMMANDS[agent])

    try:
        result = subprocess.run(
            cmd,
            input=prompt,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=TIMEOUT_SECONDS,
        )
    except FileNotFoundError:
        print(f"Error: {agent} CLI not found", file=sys.stderr)
        sys.exit(1)
    except subprocess.TimeoutExpired:
        print(f"Error: {agent} timed out after {TIMEOUT_SECONDS}s", file=sys.stderr)
        sys.exit(1)

    if result.returncode != 0:
        err = result.stderr.strip()
        print(f"Error: {agent} exited with code {result.returncode}", file=sys.stderr)
        if err:
            print(err, file=sys.stderr)
        sys.exit(result.returncode)

    output = result.stdout.strip()
    if output:
        print(output)


if __name__ == "__main__":
    main()
