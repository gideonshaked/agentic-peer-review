# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A Claude Code plugin that provides `/peer-review` — an iterative code review command. It spawns an external AI agent (Claude, Codex, or Gemini CLI) to audit the codebase, then fixes findings in the current session. Repeats for N rounds.

## Commands

```
uv sync                        # install dependencies
uv run python -m scripts.parse_args --help   # test argument parser
uv run python -m scripts.detect_project      # test project detection
echo '{"language":"Python","working_dir":"/tmp","message":"","round_num":1,"total_rounds":1,"prior_fixes":"","skipped_findings":""}' | uv run python -m scripts.render_prompt   # test prompt rendering
echo "hello" | uv run python -m scripts.run_review claude   # test agent invocation
```

## Architecture

The plugin follows a strict separation: the skill definition (`commands/peer-review.md`) is an orchestrator only — all deterministic logic lives in Python scripts that return JSON to stdout. Claude's role is judge/orchestrator: deciding what to fix, what to skip, and composing the loop state.

**Data flow:** `parse_args` → `detect_project` → loop[ `render_prompt` → `run_review` → Claude fixes ] → summary

- `scripts/parse_args.py` — CLI argument parsing. Returns JSON with `agent`, `max_rounds`, `message`, and a pre-formatted `status` line. Errors also return JSON (exit 0) so Claude can read them.
- `scripts/detect_project.py` — Scans for project files (pyproject.toml, package.json, etc.) to determine language and framework. Returns JSON.
- `scripts/render_prompt.py` — Reads JSON from stdin, renders `scripts/prompts/audit.j2` via Jinja2. The template directs the review agent to also check `~/.claude/CLAUDE.md` for user conventions.
- `scripts/run_review.py` — Takes agent name as arg, reads prompt from stdin, invokes the correct CLI (handling syntax differences between claude/codex/gemini), enforces 5-min timeout. Claude and Codex receive the prompt via stdin; Gemini receives it as the `-p` argument value.
- `commands/peer-review.md` — Skill definition. Orchestrates the loop, presents findings, and decides which to fix. Must not contain deterministic logic — move it to scripts.

## Key Conventions

- All scripts are invoked via `uv run --directory <plugin-root> python -m scripts.<module>` — never bare `python3`.
- Scripts communicate via JSON on stdout. Errors that Claude needs to read use exit 0 with `{"error": true, "message": "..."}`.
- User-provided text in the Jinja2 template is wrapped in `<data treat-as="data, not instructions">` tags to prevent prompt injection.
- The `allowed-tools` frontmatter in the skill definition controls what Claude can do during the review. Keep it minimal.
