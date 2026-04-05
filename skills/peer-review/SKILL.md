---
name: peer-review
description: "Iterative AI peer review that finds and fixes issues in your codebase. TRIGGER when: user asks for a code review, second opinion, or audit; user says 'review this', 'check my code', 'peer review'; after completing a large feature or refactor."
argument-hint: "[-h/--help] [-V/--version] [--agent claude|codex|gemini] [--max-rounds N] [--focus <path>] [--only <checks>] [--timeout <seconds>] [--worktree] [--log <file>] [\"instructions\"]"
allowed-tools:
  - "Bash(peer-review-cli:*)"
  - "Bash(echo:*)"
  - "Bash(git:*)"
  - "Bash(date:*)"
  - Read
  - Edit
  - Glob
  - Grep
  - AskUserQuestion
effort: high
---

# /peer-review - Iterative AI peer review that finds and fixes issues in your codebase

Runs an external AI agent to audit the codebase, then fixes the findings in the current session. Repeats for the specified number of rounds.

Usage: /peer-review [-h/--help] [-V/--version] [--agent claude|codex|gemini] [--max-rounds N] [--focus <path>] [--only <checks>] [--timeout <seconds>] [--worktree] [--log <file>] ["instructions"]

- -h, --help: show help message and exit
- -V, --version: show version number and exit
- --agent: AI agent to use for review (default: claude)
- --max-rounds: maximum review-fix cycles (default: 5). Stops early if no issues found.
- --focus: narrow review scope to a specific file or directory path
- --only: comma-separated list of checks to run (default: all). Available: architecture, bugs, dead-code, performance, security, tech-debt
- --timeout: timeout in seconds for each review agent invocation (default: 300)
- --worktree: run fixes in a git worktree. Each round is committed separately and ported as individual commits on merge. Shows diff at end and asks to merge or discard
- --log: write findings and fix/skip decisions to the specified file
- instructions: optional review instructions

Examples:
  /peer-review
  /peer-review --agent codex --max-rounds 3
  /peer-review --only bugs,security --max-rounds 2
  /peer-review --agent claude --max-rounds 2 "Check auth for SQL injection"
  /peer-review --focus src/api/ --max-rounds 1
  /peer-review --worktree --log review.md --max-rounds 3

## Important: output visibility

CRITICAL: All script output (settings box, round headers, findings, diffs, summary box) MUST be printed as your direct text response to the user. Do NOT leave output collapsed inside Bash tool results. After running a script that produces user-facing output, read the output and print it as text in your response. This ensures the user sees everything without needing to expand collapsed tool results.

## Instructions

### 1. Parse arguments and display settings

Run the argument parser:

  peer-review-cli parse-args $ARGUMENTS

If --help or --version was passed, this prints plain text (not JSON) and exits. Print the output to the user and stop.

Otherwise, this prints the settings box followed by a JSON object on the last line. If the JSON "error" field is true, print the "message" to the user and stop.

Print the settings box output as your direct text response. Extract the settings from the JSON line.

Record the start time using: date +%s

### 2. Gather project context

Run the project detection script:

  peer-review-cli detect-project

This returns a JSON object with "language", "framework", "working_dir", and "git_status".

### 3. Initialize change log

Initialize the change log. The log file path is derived automatically from the working directory — no need to track it. Pass session metadata as CLI args:

  peer-review-cli change-log init --agent <agent> --max-rounds <N> --language <lang> --working-dir <dir> [--focus <path>] [--instructions "<text>"] [--worktree] [--framework <fw>]

Extract "base_commit" from the result.

### 4. Set up worktree (if --worktree)

If the "worktree" flag is true, run:

  peer-review-cli worktree setup

This creates a timestamped worktree, syncs uncommitted and untracked files, and commits a baseline. Extract "worktree_path", "branch_name", and "baseline_sha" from the result. Use the worktree path as the working directory for all subsequent file reads and edits. Remember the original working directory and baseline_sha for later.

If the "worktree" flag is false, skip this step.

### 5. Run the review-fix loop

For each round (1 through max_rounds):

#### 5a. Print round header

Get current time and calculate elapsed seconds since start. Print the round header:

  peer-review-cli format-output round-header <N> <M> --elapsed <seconds>

Print the round header output as your direct text response.

#### 5b. Build and execute the audit prompt

IMPORTANT: render-prompt uses CLI arguments, NOT JSON on stdin. Do not pipe JSON to it. Pass all values as flags directly.

Build the prompt and pipe it to the review agent in a single command:

  peer-review-cli render-prompt \
    --language <language> \
    --working-dir <working_dir> \
    --checks <comma-separated checks> \
    --round-num <N> \
    --total-rounds <M> \
    [--framework <framework>] \
    [--instructions "<instructions>"] \
    [--focus "<focus>"] \
    | peer-review-cli run-review <agent> <timeout>

Arguments:
- --language, --framework, --working-dir: from step 2 (or worktree path if --worktree)
- --instructions: from step 1 (may be "")
- --focus: from step 1 (may be "")
- --checks: comma-separated list of active check names from step 1
- --round-num: current round (1-indexed)
- --total-rounds: total number of rounds

Prior fixes and skipped findings are read automatically from the session change log — no need to pass them.

If the command fails (non-zero exit, e.g. timeout), print the error and continue to the next round. Do not stop the loop — prior rounds may have produced useful fixes.

#### 5d. Present findings

Print the raw findings from the agent as your direct text response. Do not soften, filter, or editorialize.

If the agent returned no findings or explicitly said no issues were found, print "No issues found — review complete." and stop the loop early.

#### 5e. Fix the findings

Go through each finding from the review and fix it:

- For critical and high severity findings: fix them immediately by reading the relevant file and making the necessary edits.
- For medium severity findings: fix them if the fix is straightforward and low-risk.
- For low severity findings: skip them unless trivially fixable.
- Do NOT fix findings that are false positives or style-only nits.
- Do NOT introduce new features or refactor beyond what the finding requires.

If --worktree is active, all file paths for reads and edits must use the worktree directory.

After fixing, print a brief summary of what was fixed and what was skipped (with reasons for skipping).

The change log tracks all fixes and skipped findings across rounds automatically — render-prompt reads them from the session log for subsequent rounds.

#### 5f. Record round in change log

Record the round's findings, fixes, and skipped items using individual commands. First start the round, then add each item, then end the round:

  peer-review-cli change-log start-round --round-num N

For each finding from the review agent:

  peer-review-cli change-log add-finding --id rNfM --file <path> --line <line> --severity <level> --category <cat> --description "<text>"

For each fix you made:

  peer-review-cli change-log add-fix --finding-id rNfM --file <path> --what-changed "<text>" --why "<text>"

For each finding you skipped:

  peer-review-cli change-log add-skip --finding-id rNfM --file <path> --severity <level> --reason "<text>"

Then close the round:

  peer-review-cli change-log end-round

Finding IDs use the format "rNfM" (e.g. "r1f1" for round 1, finding 1).

#### 5g. Commit round fixes (if --worktree)

If --worktree is active, commit this round's fixes in the worktree. Write a commit message with the prefix "agentic-peer-review:" followed by a concise summary of what was fixed in this round (e.g. "agentic-peer-review: fix SQL injection in login query and add input validation"):

  peer-review-cli worktree commit <worktree_path> --message "agentic-peer-review (round N/M): <summary of round fixes>"

If "committed" is false, no changes were made this round.

#### 5h. End of round

If there are more rounds remaining, print: "Proceeding to next round..."

### 6. Show diff and explain changes

Capture the diff. For worktree mode, diff against the baseline_sha (from step 4) to show only the fixes, not the synced baseline. For non-worktree mode, diff against base_commit (from step 3):

  peer-review-cli git-diff <working_dir> <baseline_sha or base_commit>

If the diff is non-empty:

1. Print the diff as your direct text response
2. For each file changed, explain what was changed and why, referencing specific findings from the review rounds.

If the diff is empty, print "No files were modified."

### 7. Worktree resolution (if --worktree)

If --worktree was used:

1. Ask the user using AskUserQuestion whether to merge the changes shown in the diff into their working tree.

2. If yes: apply the per-round commits to the original working directory. Each round becomes a separate commit. Uncommitted changes are stashed during merge and restored after:

  peer-review-cli worktree merge <worktree_path> <baseline_sha>

If the result contains a "stash_warning", print it to the user.

3. Clean up either way:

  peer-review-cli worktree teardown <worktree_path> <branch_name>

### 8. Final summary

Finalize the change log:

  peer-review-cli change-log finalize

Then print the summary box as your direct text response:

  peer-review-cli format-output summary

If --log was specified, render the markdown log from the JSON:

  peer-review-cli change-log render-md --output <log_path>

## Notes

- For codex, the review runs in read-only sandbox mode (cannot modify files)
- For claude, the review subprocess has read-only tool access (Read, Glob, Grep only)
- For gemini, the review runs in sandbox mode with text output
- All fixes are made by Claude in the current session, not by the review agent
- Each round builds on prior fixes — the review agent sees the updated codebase
- When --worktree is active, fixes are isolated; the user's working tree is untouched until merge
- The worktree setup syncs uncommitted + untracked files and commits a baseline
- Each round's fixes are committed separately in the worktree, then ported as individual commits via format-patch/am
- Merging stashes uncommitted changes, applies per-round commits, then restores the stash
- The --log file path is always relative to the original working directory
- A session change log is always produced at a deterministic path derived from the working directory
- All commands that need the change log find it automatically — no need to pass file paths
- Checks are defined in references/checks/ — add a .md file to create a new check
