# AGENTS.md

Shared instructions for every AI coding agent working in this repo (Antigravity, Claude Code, and others).
This file is the single source of truth: `CLAUDE.md` imports it. Update this file, not the tool-specific
ones, when a project rule changes.

## Project

Repo launcher and GitHub settings tooling. `launch_repo.py` generates a standardized, agent-ready Python
repo from `templates/`, can create a private GitHub repo for it, and then applies the standard settings.
`apply_repo_settings.py` applies the same settings to existing repos. The `/launch-repo` skill in agent-brain
and `scaffold.py` in idea-to-tickets both call `launch_repo.py`.

| Path | What lives there |
| --- | --- |
| `launch_repo.py` | Launcher CLI: renders templates, runs `git init`, `gh repo create`, then the settings step |
| `apply_repo_settings.py` | Squash-only merges, default-branch ruleset, optional Claude token secret |
| `repo_settings_overrides.json` | Per-repo exceptions to the squash-only rule (empty by default) |
| `templates/common/` | Files copied into every new repo (`AGENTS.md`, `CLAUDE.md`, `.github/workflows/`, docs) |
| `templates/python_*/` | Archetype files (`python_ai_agent`, `python_cli`, `python_generic`) |
| `skills/launch-repo/`, `.agents/skills/launch-repo/` | The `/launch-repo` skill for Claude Code and Antigravity |
| `tests/` | pytest suite. It never calls `gh` or the network |

## Commands

Requires [uv](https://docs.astral.sh/uv/). There is no `pyproject.toml`, so tools run through `uv run --with`.

```bash
uv run --with pytest pytest                  # test suite (offline)
uvx ruff check .                             # lint

python launch_repo.py my-tool --type python-generic --dry-run
python apply_repo_settings.py --repo owner/name            # dry run
python apply_repo_settings.py --repo owner/name --apply    # make the changes
```

Before finishing any change, run the tests and the linter and make sure both pass.

## Hard rules

1. **Human punctuation only.** Never write em-dashes (U+2014) or en-dashes (U+2013) in code comments,
   docstrings, docs, templates, or commit messages. Use a plain hyphen `-`. Templates are copied into every
   new repo, so a bad dash here spreads everywhere.
2. **Templates are the source for every new repo.** Keep the placeholders `{{project_name}}`,
   `{{package_name}}` and `{{project_description}}`. GitHub Actions expressions must keep a space after the
   braces (`${{ secrets.X }}`) so the renderer leaves them alone.
3. **Workflows stay in sync.** `.github/workflows/claude*.yml` must match `templates/common/.github/workflows/`
   byte for byte. A test enforces it. Change the template first, then copy it here.
4. **Secrets never reach a command line or a log.** `apply_repo_settings.py` passes the token over stdin only.
   Never print it.
5. **Offline tests.** Tests use a fake `gh` runner. No real `gh` calls and no network.
6. **Cross-platform.** The user develops on Windows (PowerShell) and agents may run on Linux. Use `pathlib`,
   avoid shell-specific code in Python, and give both PowerShell and bash variants in docs when they differ.
7. **No destructive git.** No `git push --force`, `git reset --hard`, or `git clean`. Roll back with `git revert`.

## Git workflow

- `main` is protected: no direct pushes, no force pushes. Work on a branch (`feat/<slug>`, `fix/<slug>`)
  and open a pull request.
- Pull requests are squash-merged, so the PR title becomes the commit title. Use a conventional title
  (`feat:`, `fix:`, `chore:`, `docs:`, `ci:`) that explains why.
- Claude reviews every pull request (`.github/workflows/claude-review.yml`) and answers `@claude` mentions
  (`.github/workflows/claude.yml`). Both need the `CLAUDE_CODE_OAUTH_TOKEN` repository secret.
