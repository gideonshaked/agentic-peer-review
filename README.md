# agentic-peer-review

A Claude Code plugin that runs iterative peer review using external AI agents. It spawns a read-only reviewer (Claude, Codex, or Gemini CLI), presents the findings, fixes them in your session, and repeats for N rounds.

## Install

From GitHub via HTTPS:

```
claude plugin add https://github.com/gideonshaked/agentic-peer-review.git
```

From GitHub via SSH:

```
claude plugin add git@github.com:gideonshaked/agentic-peer-review.git
```

From a local directory:

```
claude plugin add /path/to/agentic-peer-review
```

During development:

```
claude --plugin-dir /path/to/agentic-peer-review
```

## Usage

```
/peer-review
/peer-review --agent codex --max-rounds 3
/peer-review --only bugs,security --max-rounds 2
/peer-review --focus src/api/ --max-rounds 1
/peer-review --worktree --log review.md --max-rounds 3
/peer-review --agent gemini --max-rounds 2 "Check auth for SQL injection"
```

| Flag | Default | Description |
|------|---------|-------------|
| `--agent` | `claude` | Review agent: `claude`, `codex`, or `gemini` |
| `--max-rounds` | `5` | Number of review-fix cycles (1-10) |
| `--focus` | none | Narrow review to a specific file or directory |
| `--only` | all | Comma-separated list of checks to run |
| `--timeout` | `300` | Timeout in seconds for each agent invocation |
| `--worktree` | off | Run fixes in a git worktree; ask to merge at end |
| `--log` | none | Write findings and decisions to the specified file |
| `"instructions"` | none | Additional review instructions |

### Checks

By default, all checks run: `bugs`, `security`, `dead-code`, `tech-debt`, `architecture`, `performance`. Use `--only` to run a subset:

```
/peer-review --only bugs,security
```

Checks are defined as individual markdown files in `references/checks/`. To add a custom check, drop a `.md` file in that directory describing what to look for.

### Worktree mode

With `--worktree`, all fixes happen in an isolated git worktree. Your working tree stays untouched. After all rounds, you see the full diff and choose whether to merge the changes back.

### Change log

Every review session produces a structured JSON change log in `/tmp/`, tracking all findings, fixes, and skip decisions per round. When `--log` is specified, a formatted markdown log is also rendered from the JSON.

## How it works

Each round:

1. Builds an audit prompt (via Jinja2 template) with project context, active checks, user instructions, and prior-round history
2. Spawns the chosen AI agent in read-only/sandbox mode to review the codebase
3. Presents the raw findings
4. Fixes critical/high issues, evaluates medium ones, skips low/false positives
5. Records findings and decisions in the JSON change log

After all rounds, the full git diff is shown with explanations of each change. In worktree mode, you're asked whether to merge.

The reviewer also checks `~/.claude/CLAUDE.md` and any project-level `CLAUDE.md` for your conventions, so findings include violations of your own standards.

## Requirements

- [Claude Code](https://claude.ai/code)
- For `--agent codex`: [Codex CLI](https://github.com/openai/codex) (`npm install -g @openai/codex`)
- For `--agent gemini`: [Gemini CLI](https://github.com/google-gemini/gemini-cli)
