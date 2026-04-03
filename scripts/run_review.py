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
    "gemini": ["gemini", "--sandbox", "--output-format", "text", "-p"],
}

DEFAULT_TIMEOUT = 300


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in AGENT_COMMANDS:
        print(
            f"Usage: {sys.argv[0]} <claude|codex|gemini> [timeout_seconds]  (reads prompt from stdin)",
            file=sys.stderr,
        )
        sys.exit(1)

    agent = sys.argv[1]
    try:
        timeout = int(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_TIMEOUT
    except ValueError:
        print(f"Error: invalid timeout value: {sys.argv[2]}", file=sys.stderr)
        sys.exit(1)
    prompt = sys.stdin.read()

    if not prompt.strip():
        print("Error: empty prompt on stdin", file=sys.stderr)
        sys.exit(1)

    cmd = list(AGENT_COMMANDS[agent])

    # gemini takes the prompt as the -p value; claude/codex read from stdin
    if agent == "gemini":
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
            timeout=timeout,
        )
    except FileNotFoundError:
        print(f"Error: {agent} CLI not found", file=sys.stderr)
        sys.exit(1)
    except subprocess.TimeoutExpired:
        print(f"Error: {agent} timed out after {timeout}s", file=sys.stderr)
        sys.exit(1)

    err = result.stderr.strip()
    if err:
        print(err, file=sys.stderr)

    if result.returncode != 0:
        print(f"Error: {agent} exited with code {result.returncode}", file=sys.stderr)
        sys.exit(result.returncode)

    output = result.stdout.strip()
    if output:
        print(output)


if __name__ == "__main__":
    main()
