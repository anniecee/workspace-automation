# AGENTS.md

Shared instructions for every AI coding agent working in this repo (Antigravity, Claude Code, and others).
This file is the single source of truth: `CLAUDE.md` imports it. Update this file, not the tool-specific
ones, when a project rule changes.

## Project

{{project_description}}

| Path | What lives there |
| --- | --- |
| `src/{{package_name}}/` | Source code |
| `tests/` | pytest suite |
| `docs/` | Architecture notes (`architecture.md`) |

## Commands

Requires [uv](https://docs.astral.sh/uv/). `uv run` works the same on Windows and Linux.

```bash
uv sync --extra dev          # install runtime + dev dependencies
uv run pytest                # test suite
uv run ruff check .          # lint
uv run ruff format .         # format
```

Before finishing any change, run `uv run pytest` and `uv run ruff check .` and make sure both pass.

## Hard rules

1. **Human punctuation only.** Never write em-dashes (U+2014) or en-dashes (U+2013) in code comments,
   docstrings, docs, or commit messages. Use a plain hyphen `-`. Comments are terse and only explain
   non-obvious logic.
2. **Secrets.** Never commit `.env`, private keys, or tokens. Add new settings to `.env.example` with blank
   values.
3. **Verify before declaring done.** Run the tests and linter. Do not report a task complete on unverified code.
4. **No destructive git.** No `git push --force`, `git reset --hard`, or `git clean`. Roll back with `git revert`.

## Git workflow

- `main` is protected: no direct pushes, no force pushes. Work on a branch (`feat/<slug>`, `fix/<slug>`)
  and open a pull request.
- Pull requests are squash-merged, so the PR title becomes the commit title. Use a conventional title
  (`feat:`, `fix:`, `chore:`, `docs:`, `ci:`) that explains why.
- Claude reviews every pull request (`.github/workflows/claude-review.yml`) and answers `@claude` mentions
  (`.github/workflows/claude.yml`). Both need the `CLAUDE_CODE_OAUTH_TOKEN` repository secret.
