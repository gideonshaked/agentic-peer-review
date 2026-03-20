# agent-peer-review

A Claude Code plugin that runs iterative peer review using external AI agents. It spawns a read-only reviewer (Claude, Codex, or Gemini CLI), presents the findings, fixes them in your session, and repeats for N rounds.

## Install

```
claude plugin add /path/to/agent-peer-review
```

Or during development:

```
claude --plugin-dir /path/to/agent-peer-review
```

## Usage

```
/peer-review
/peer-review --agent codex --max-rounds 3
/peer-review --agent gemini --max-rounds 2 "Focus on auth, skip tech debt"
```

| Flag | Default | Description |
|------|---------|-------------|
| `--agent` | `claude` | Review agent: `claude`, `codex`, or `gemini` |
| `--max-rounds` | `5` | Number of review-fix cycles (1-10) |
| `"message"` | none | Custom review instructions |

The message lets you steer the review — tell it what to focus on, what to skip, or what categories to ignore. The default audit checks for bugs, security issues, dead code, tech debt, and architecture problems.

## How it works

Each round:

1. Builds an audit prompt (via Jinja2 template) with project context, user instructions, and prior-round history
2. Spawns the chosen AI agent in read-only/sandbox mode to review the codebase
3. Presents the raw findings
4. Fixes critical/high issues, evaluates medium ones, skips low/false positives
5. Logs what was fixed and skipped so the next round doesn't re-report known issues

The reviewer also checks `~/.claude/CLAUDE.md` and any project-level `CLAUDE.md` for your conventions, so findings include violations of your own standards.

## Requirements

- [Claude Code](https://claude.ai/code)
- For `--agent codex`: [Codex CLI](https://github.com/openai/codex) (`npm install -g @openai/codex`)
- For `--agent gemini`: [Gemini CLI](https://github.com/google-gemini/gemini-cli)
