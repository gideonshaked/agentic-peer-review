---
name: peer-review
description: "Iterative peer review using an external AI agent (claude, codex, or gemini) with automatic fix cycles. Runs N rounds of: external agent audits -> Claude fixes -> repeat."
argument-hint: "[--agent claude|codex|gemini] [--max-rounds N] [--focus <path>] [--timeout <seconds>] [--worktree] [--log <file>] [\"message\"]"
allowed-tools:
  - "Bash(uv:*)"
  - "Bash(echo:*)"
  - "Bash(git:*)"
  - Read
  - Edit
  - Glob
  - Grep
  - AskUserQuestion
---

# /peer-review - Iterative AI peer review with fix cycles

Runs an external AI agent to audit the codebase, then fixes the findings in the current session. Repeats for the specified number of rounds.

Usage: /peer-review [--agent claude|codex|gemini] [--max-rounds N] [--focus path] [--timeout seconds] [--worktree] [--log file] ["message"]

- --agent: which AI agent CLI to use for review (default: claude)
- --max-rounds: number of review-fix cycles, 1-10 (default: 5)
- --focus: narrow the review to a specific file or directory
- --timeout: timeout in seconds for each agent invocation (default: 300)
- --worktree: run all fixes in a git worktree; show diff at end and ask to merge or discard
- --log: write findings and fix/skip decisions to the specified file
- message: optional quoted string with review instructions

Examples:
  /peer-review
  /peer-review --agent codex --max-rounds 3
  /peer-review --agent claude --max-rounds 2 "Check auth for SQL injection, skip tech debt"
  /peer-review --focus src/api/ --max-rounds 1
  /peer-review --worktree --log review.md --max-rounds 3

## Instructions

### 1. Parse arguments

Run the argument parser:

  uv run --directory "${CLAUDE_SKILL_DIR}/.." python -m scripts.parse_args $ARGUMENTS

This returns a JSON object. If the "error" field is true, print the "message" to the user and stop.

Otherwise, extract all fields from the result. Print the "status" field.

### 2. Gather project context

Run the project detection script:

  uv run --directory "${CLAUDE_SKILL_DIR}/.." python -m scripts.detect_project

This returns a JSON object with "language", "framework", "working_dir", and "git_status".

### 3. Set up worktree (if --worktree)

If the "worktree" flag is true:

1. Create a branch name: peer-review/<timestamp> (e.g. peer-review/20260402-053800)
2. Create a worktree:

  git worktree add /tmp/peer-review-worktree -b <branch-name>

3. For the rest of the review loop, use the worktree path as the working directory for all file reads and edits. The review agent also runs against the worktree. Remember the original working directory for later.

If the "worktree" flag is false, skip this step.

### 4. Run the review-fix loop

For each round (1 through max_rounds):

#### 4a. Build the audit prompt

Build a JSON object and pipe it to the render script. The fields are:

- "language", "framework", "working_dir": from step 2 (or worktree path if --worktree)
- "message": from step 1
- "focus": from step 1 (may be "")
- "round_num": current round (1-indexed)
- "total_rounds": total number of rounds
- "prior_fixes": summary of fixes from prior rounds ("" if round 1)
- "skipped_findings": summary of skipped findings from prior rounds ("" if round 1)

  echo '{ ... }' | uv run --directory "${CLAUDE_SKILL_DIR}/.." python -m scripts.render_prompt

#### 4b. Execute the review agent

Pipe the rendered prompt into the run_review script, passing the agent name and timeout as arguments.

  echo '{ ... }' | uv run --directory "${CLAUDE_SKILL_DIR}/.." python -m scripts.render_prompt | uv run --directory "${CLAUDE_SKILL_DIR}/.." python -m scripts.run_review <agent> <timeout>

If the command fails (non-zero exit), print the error and stop the loop.

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

If --worktree is active, all file paths for reads and edits must use the worktree directory.

After fixing, print a brief summary of what was fixed and what was skipped (with reasons for skipping).

Keep a running log of all fixes made AND all findings intentionally skipped (with reasons) across rounds to feed into the next round's prompt.

#### 4e. Write to log file (if --log)

If a log file was specified, append to it after each round using echo with >> redirection. Write the round header, the raw findings, and the fix/skip decisions. The log file path is always relative to the original working directory, not the worktree.

#### 4f. End of round

After fixing, if there are more rounds remaining, print: "Proceeding to round N+1..."

### 5. Worktree resolution (if --worktree)

After the loop completes, if --worktree was used:

1. Show the full diff of changes made in the worktree:

  git -C /tmp/peer-review-worktree diff HEAD~..HEAD

Or if multiple commits were made, diff against the original branch.

2. Ask the user using AskUserQuestion whether to merge the changes into their working tree.

3. If yes: from the original working directory, run:

  git merge <branch-name>

4. Clean up either way:

  git worktree remove /tmp/peer-review-worktree
  git branch -D <branch-name>

(Only delete the branch if the user chose not to merge.)

### 6. Final summary

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
- For gemini, the review runs in sandbox mode with text output
- All fixes are made by Claude in the current session, not by the review agent
- Each round builds on prior fixes — the review agent sees the updated codebase
- When --worktree is active, fixes are isolated; the user's working tree is untouched until merge
- The --log file path is always relative to the original working directory
