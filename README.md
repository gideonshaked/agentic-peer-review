<h1 align="center">agentic-peer-review</h1>

A Claude Code plugin that peer-reviews your code with AI agents.
Spawns an AI code reviewer (Claude, Codex, or Gemini), implements the recommended fixes,
and repeats until the reviewer is satisfied with the codebase.

```bash
# Review with Codex for up to 3 rounds, only checking bugs and security, in an isolated worktree, with a log file and custom instructions.
/agentic-peer-review:peer-review --agent codex --max-rounds 3 --only bugs,security --worktree --log review.md "focus on the auth module"
```

<p align="center">
  <a href="#install">Install</a> &bull;
  <a href="#usage">Usage</a> &bull;
  <a href="#options">Options</a> &bull;
  <a href="#checks">Checks</a>
</p>


## Install

### Getting started

Add the marketplace and install the plugin:

```bash
/plugin marketplace add gideonshaked/agentic-peer-review
/plugin install agentic-peer-review@agentic-peer-review
```

### Requirements

- [Claude Code](https://claude.ai/code)
- [Codex](https://github.com/openai/codex) (only required for using OpenAI Codex as a reviewer agent)
- [Gemini CLI](https://github.com/google-gemini/gemini-cli) (only required for using Google Gemini as a reviewer agent)

## Usage

### Help output

```
/agentic-peer-review:peer-review -h
usage: peer-review [-h] [--agent {claude,codex,gemini}]
                   [--max-rounds MAX_ROUNDS] [--focus FOCUS]
                   [--timeout TIMEOUT] [--worktree] [--log LOG] [--only ONLY]
                   [instructions]

Iterative AI peer review that finds and fixes issues

positional arguments:
  instructions          Optional review instructions

options:
  -h, --help            show this help message and exit
  --agent {claude,codex,gemini}
                        AI agent to use for review (default: claude)
  --max-rounds MAX_ROUNDS
                        Maximum review-fix cycles (default: 5). Stops early if
                        no issues found.
  --focus FOCUS         Narrow review scope to a specific file or directory
                        path
  --timeout TIMEOUT     Timeout in seconds for each review agent invocation
                        (default: 300)
  --worktree            Run fixes in a git worktree; show diff at end and ask
                        to merge or discard
  --log LOG             Write findings and fix/skip decisions to the specified
                        file
  --only ONLY           Comma-separated list of checks to run (default: all).
                        Available: architecture, bugs, dead-code, performance,
                        security, tech-debt
```

### Options

| Flag | Description |
|------|-------------|
| `--agent` | Review agent: `claude` (default), `codex`, or `gemini` |
| `--max-rounds` | Maximum review-that finds and fixes issues (default: 5). Stops early if no issues found. |
| `--focus <file or dir>` | Narrow the review to a specific file or directory |
| `--only <check,check,...>` | Only run specific checks. See [checks](#checks) below. |
| `--timeout` | Timeout per agent invocation in seconds (default: 300) |
| `--worktree` | Run all fixes in an isolated git worktree. Shows diff at end and asks to merge. |
| `--log` | Write a structured review log to the specified file |
| `instructions` | Give the reviewer agent specific instructions on what to focus on, what to skip, etc. |

### Checks

By default all checks run. Use `--only` to select a subset:

| Check | What it looks for |
|-------|-------------------|
| `bugs` | Logic errors, off-by-one, null access, race conditions, unhandled edge cases |
| `security` | Injection, auth flaws, secrets in code, insecure defaults, missing validation |
| `dead-code` | Unreachable code, unused imports/variables/functions, obsolete config |
| `tech-debt` | Hardcoded values, copy-paste logic, missing error handling, TODO markers |
| `architecture` | Coupling, layering violations, circular dependencies, misplaced responsibilities |
| `performance` | Unnecessary allocations, N+1 queries, blocking calls, missing caching |
