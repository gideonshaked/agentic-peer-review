<h1 align="center"><code>agentic-peer-review</code></h1>

A Claude Code plugin that peer-reviews your code with AI agents. `agentic-peer-review` spawns an AI code reviewer (Claude, Codex, or Gemini), implements the recommended fixes, and repeats until the reviewer is satisfied with the codebase.

<h3 align="center">Quickstart</h3>

Open Claude Code and paste the following:

```
/plugin marketplace add gideonshaked/agentic-peer-review@v1.1.3
```

```
/plugin install agentic-peer-review@agentic-peer-review
```

Then run peer review on the current workspace:

```
/peer-review
```

<p align="center">
  <a href="#install">Install</a> &bull;
  <a href="#usage">Usage</a> &bull;
  <a href="#options">Options</a>
</p>

## Install

### Getting started

From the terminal:

```bash
claude plugin marketplace add gideonshaked/agentic-peer-review@v1.1.3
claude plugin install agentic-peer-review@agentic-peer-review
```

Or from inside Claude Code:

```
/plugin marketplace add gideonshaked/agentic-peer-review@v1.1.3
```

```
/plugin install agentic-peer-review@agentic-peer-review
```

### Install from latest commit

From the terminal:

```bash
claude plugin marketplace add gideonshaked/agentic-peer-review
claude plugin install agentic-peer-review@agentic-peer-review
```

Or from inside Claude Code:

```
/plugin marketplace add gideonshaked/agentic-peer-review
```

```
/plugin install agentic-peer-review@agentic-peer-review
```

### Updating

From the terminal:

```bash
claude plugin marketplace update agentic-peer-review
claude plugin update agentic-peer-review@agentic-peer-review
```

Or from inside Claude Code:

```
/plugin marketplace update agentic-peer-review
```

Then open `/plugin`, go to the **Installed** tab, and update the plugin from there.

### Requirements

- [Claude Code](https://code.claude.com/docs/en/quickstart)
- [uv](https://docs.astral.sh/uv/#installation)
- [Codex CLI](https://github.com/openai/codex) (only required for using OpenAI Codex as a reviewer agent)
- [Gemini CLI](https://github.com/google-gemini/gemini-cli) (only required for using Google Gemini as a reviewer agent)

## Usage

### Help

To see all available options, in Claude Code run:

```
/peer-review -h
```

```
usage: peer-review [-h] [-V] [--agent {claude,codex,gemini}]
                   [--max-rounds MAX_ROUNDS] [--focus FOCUS]
                   [--timeout TIMEOUT] [--worktree] [--log LOG] [--only ONLY]
                   [--skip SKIP]
                   [instructions]

  Iterative AI peer review that finds and fixes issues in your codebase

  positional arguments:
    instructions          Optional review instructions

  options:
    -h, --help            show this help message and exit
    -V, --version         show program's version number and exit
    --agent {claude,codex,gemini}
                          AI agent to use for review (default: claude)
    --max-rounds MAX_ROUNDS
                          Maximum review-fix cycles (default: 5). Stops early if
                          no issues found.
    --focus FOCUS         Narrow review scope to a specific file or directory
                          path
    --timeout TIMEOUT     Timeout in seconds for each review agent invocation
                          (default: 300)
    --worktree            Run fixes in a git worktree. Each round is committed
                          separately and ported as individual commits on merge.
                          Shows diff at end and asks to merge or discard
    --log LOG             Write findings and fix/skip decisions to the specified
                          file
    --only ONLY           Comma-separated list of checks to run (default: all).
                          Available: architecture, bugs, dead-code, performance,
                          security, tech-debt
    --skip SKIP           Comma-separated list of checks to exclude. Available:
                          architecture, bugs, dead-code, performance, security,
                          tech-debt
```

### Options

| Flag | Description |
|------|-------------|
| `-h`, `--help` | Show help message and exit |
| `-V`, `--version` | Show version number and exit |
| `--agent` | Review agent: `claude` (default), `codex`, or `gemini` |
| `--max-rounds` | Maximum review-fix cycles (default: 5). Stops early if no issues found. |
| `--focus <file or dir>` | Narrow the review to a specific file or directory |
| `--only <check,check,...>` | Only run specific checks. See [checks](#checks) below. |
| `--skip <check,check,...>` | Exclude specific checks. Cannot be used with `--only`. |
| `--timeout` | Timeout per agent invocation in seconds (default: 300) |
| `--worktree` | Run all fixes in an isolated git worktree. Each round is committed separately and ported as individual commits on merge. |
| `--log` | Write a structured review log to the specified file |
| `instructions` | Give the reviewer agent specific instructions on what to focus on, what to skip, etc. |

### Checks

By default all checks run. Use `--only` to select a subset, or `--skip` to exclude specific checks:

| Check | What it looks for |
|-------|-------------------|
| `bugs` | Logic errors, off-by-one, null access, race conditions, unhandled edge cases |
| `security` | Injection, auth flaws, secrets in code, insecure defaults, missing validation |
| `dead-code` | Unreachable code, unused imports/variables/functions, obsolete config |
| `tech-debt` | Hardcoded values, copy-paste logic, missing error handling, TODO markers |
| `architecture` | Coupling, layering violations, circular dependencies, misplaced responsibilities |
| `performance` | Unnecessary allocations, N+1 queries, blocking calls, missing caching |
