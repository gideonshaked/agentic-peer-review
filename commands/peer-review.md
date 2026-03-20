---
description: "Iterative peer review using an external AI agent (claude, codex, or gemini) with automatic fix cycles. Runs N rounds of: external agent audits → Claude fixes → repeat."
argument-hint: "<agent> <rounds> [focus area or file path]"
---

# /peer-review - Iterative AI peer review with fix cycles

Runs an external AI agent to audit the codebase, then fixes the findings in the current session. Repeats for the specified number of rounds.

Usage: /peer-review <agent> <rounds> [focus area or file path]

- agent: claude, codex, or gemini
- rounds: number of review-fix cycles (1-10)
- focus: optional file path or topic (e.g. "error handling", "src/api.py")

Examples:
  /peer-review codex 3
  /peer-review claude 2 src/auth/
  /peer-review gemini 1 error handling

## Instructions

### 1. Parse arguments from $ARGUMENTS

Split $ARGUMENTS into three parts:
- First word: the agent name (must be one of: claude, codex, gemini)
- Second word: the number of rounds (must be a positive integer, max 10)
- Remaining words (if any): the focus area or file path

If the agent name is missing or invalid, print the usage line above and stop.
If the number of rounds is missing or not a valid number, default to 1.

### 2. Validate the agent CLI is available

Run `which <agent>` to confirm the CLI is installed. For claude, check `which claude`. For codex, check `which codex`. For gemini, check `which gemini`.

If the CLI is not found, tell the user to install it and stop:
- claude: "Install Claude Code: see https://docs.anthropic.com/en/docs/claude-code"
- codex: "Install Codex CLI: npm install -g @openai/codex"
- gemini: "Install Gemini CLI: npm install -g @anthropic-ai/gemini-cli or see https://github.com/google-gemini/gemini-cli"

### 3. Gather project context

Run these commands to understand the project:
- `git status` to see current state
- `git diff --stat HEAD` to see recent changes
- Check for common project files (package.json, Cargo.toml, pyproject.toml, go.mod, etc.)
- Note the current working directory and primary language

### 4. Run the review-fix loop

For each round (1 through N):

#### 4a. Build the audit prompt

Start with this base prompt:

"You are a senior code reviewer performing a thorough audit. Examine this codebase for bugs, logic errors, dead code, security vulnerabilities, tech debt, and architectural issues. For each finding, report: 1) File path 2) Line number or range 3) Severity: critical, high, medium, or low 4) Category: bug, security, dead-code, tech-debt, architecture, or performance 5) A clear explanation of the problem and why it matters. Format findings as a numbered list. Only report genuine issues — no style nits or subjective preferences."

Then append context:
- Add the project language, framework, and working directory
- If this is round 2+, add: "Previous rounds already fixed some issues. Focus on finding NEW problems, not issues that were already addressed. Here is a summary of what was fixed in prior rounds:" followed by the summary from prior rounds.
- If a focus area was specified:
  - If it looks like a file path (contains / or .), add: "Focus your audit on: <path>"
  - Otherwise, add: "Focus on this category: <topic>"
- If no focus area, add: "Do a broad sweep of the entire codebase."

#### 4b. Execute the review agent

Run the appropriate CLI command based on the chosen agent:

For codex:
  codex exec -s read-only "<full_prompt>"

For claude:
  claude -p --allowedTools "Read Glob Grep" "<full_prompt>"

For gemini:
  gemini -p "<full_prompt>" --sandbox --output-format text

Capture the full output.

#### 4c. Present findings

Print a header: "## Round N/M — Review by <agent>"

Print the raw findings from the agent. Do not soften, filter, or editorialize.

If the agent returned no findings or explicitly said no issues were found, print "No issues found — review complete." and stop the loop early.

#### 4d. Fix the findings

Go through each finding from the review and fix it:

- For critical and high severity findings: fix them immediately by reading the relevant file and making the necessary edits.
- For medium severity findings: fix them if the fix is straightforward and low-risk.
- For low severity findings: skip them unless trivially fixable.
- Do NOT fix findings that are false positives or style-only nits.
- Do NOT introduce new features or refactor beyond what the finding requires.

After fixing, print a brief summary of what was fixed and what was skipped (with reasons for skipping).

Keep a running log of all fixes made across rounds to feed into the next round's prompt.

#### 4e. End of round

After fixing, if there are more rounds remaining, print: "Proceeding to round N+1..."

### 5. Final summary

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
