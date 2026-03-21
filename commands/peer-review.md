---
description: "Iterative peer review using an external AI agent (claude, codex, or gemini) with automatic fix cycles. Runs N rounds of: external agent audits -> Claude fixes -> repeat."
argument-hint: "[--agent claude|codex|gemini] [--max-rounds N] [\"review instructions\"]"
allowed-tools: ["Bash(uv:*)", "Bash(echo:*)", "Bash(git:*)", "Read", "Edit", "Glob", "Grep"]
---

# /peer-review - Iterative AI peer review with fix cycles

Runs an external AI agent to audit the codebase, then fixes the findings in the current session. Repeats for the specified number of rounds.

Usage: /peer-review [--agent claude|codex|gemini] [--max-rounds N] ["message"]

- --agent: which AI agent CLI to use for review (default: claude)
- --max-rounds: number of review-fix cycles, 1-10 (default: 5)
- message: optional quoted string with review instructions — what to focus on, what to skip, etc.

Examples:
  /peer-review
  /peer-review --agent codex --max-rounds 3
  /peer-review --agent claude --max-rounds 2 "Check the auth module for SQL injection vulnerabilities, do not check for tech debt"
  /peer-review --agent gemini --max-rounds 1 "Focus on error handling in src/api/"

## Instructions

### 1. Parse arguments

Run the argument parser:

  uv run --directory "${CLAUDE_PLUGIN_ROOT}" python -m scripts.parse_args $ARGUMENTS

This returns a JSON object. If the "error" field is true, print the "message" to the user and stop — do not proceed with the review loop.

Otherwise, extract "agent", "max_rounds", and "message" from the JSON output. Print the "status" field from the result.

### 2. Gather project context

Run the project detection script:

  uv run --directory "${CLAUDE_PLUGIN_ROOT}" python -m scripts.detect_project

This returns a JSON object with "language", "framework", "working_dir", and "git_status". Use the language and framework values when building the audit prompt.

### 3. Run the review-fix loop

For each round (1 through max_rounds):

#### 3a. Build the audit prompt

Build a JSON object and pipe it to the render script. The fields are:

- "language", "framework", "working_dir": from the step 2 detection result
- "message": from the step 1 parsed arguments
- "round_num": current round (1-indexed)
- "total_rounds": total number of rounds
- "prior_fixes": summary of fixes from prior rounds ("" if round 1)
- "skipped_findings": summary of skipped findings from prior rounds ("" if round 1)

  echo '{ ... }' | uv run --directory "${CLAUDE_PLUGIN_ROOT}" python -m scripts.render_prompt

#### 3b. Execute the review agent

Pipe the rendered prompt directly into the run_review script, passing the agent name as an argument. The script handles CLI differences, timeouts (5 min), and error reporting internally.

  echo '{ ... }' | uv run --directory "${CLAUDE_PLUGIN_ROOT}" python -m scripts.render_prompt | uv run --directory "${CLAUDE_PLUGIN_ROOT}" python -m scripts.run_review <agent>

Or as two steps if you already have the rendered prompt saved from step 4a:

  echo "<rendered_prompt>" | uv run --directory "${CLAUDE_PLUGIN_ROOT}" python -m scripts.run_review <agent>

If the command fails (non-zero exit), print the error and stop the loop — do not crash.

#### 3c. Present findings

Print a header: "## Round N/M — Review by <agent>"

Print the raw findings from the agent. Do not soften, filter, or editorialize.

If the agent returned no findings or explicitly said no issues were found, print "No issues found — review complete." and stop the loop early.

#### 3d. Fix the findings

Go through each finding from the review and fix it:

- For critical and high severity findings: fix them immediately by reading the relevant file and making the necessary edits.
- For medium severity findings: fix them if the fix is straightforward and low-risk.
- For low severity findings: skip them unless trivially fixable.
- Do NOT fix findings that are false positives or style-only nits.
- Do NOT introduce new features or refactor beyond what the finding requires.

After fixing, print a brief summary of what was fixed and what was skipped (with reasons for skipping).

Keep a running log of all fixes made AND all findings intentionally skipped (with reasons) across rounds to feed into the next round's prompt. This prevents the reviewer from re-reporting known skipped issues.

#### 3e. End of round

After fixing, if there are more rounds remaining, print: "Proceeding to round N+1..."

### 4. Final summary

After all rounds complete (or after early exit), print:

"## Peer Review Complete"

Then summarize:
- Total rounds completed
- Total findings across all rounds
- Total fixes applied
- Any findings that were intentionally skipped and why

## Notes

- For codex, the review runs in read-only sandbox mode (cannot modify files)
- For claude, the review subprocess has read-only tool access (Read, Glob, Grep only)
- For gemini, the review runs in sandbox mode with text output (-p --sandbox --output-format text)
- All fixes are made by Claude in the current session, not by the review agent
- Each round builds on prior fixes — the review agent sees the updated codebase
