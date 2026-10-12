# Workspace Automation & Launch-Repo
 
This project provides tools and skills to automate the creation of standardized, agent-ready repositories and manage workspace workflows.
 
## Objectives
1. **Core CLI Tool (`launch_repo.py`)**:
   - Initialize git repository.
   - Configure `.gitignore` for Python/AI agents.
   - Generate `.env.example` with standard LLM/agent API keys.
   - Set up virtual environment (`venv` / `uv`) and dependency management.
   - Generate standardized Markdown documentation (`README.md`, `docs/architecture.md`).
2. **Antigravity Skill Integration**:
   - Provide a native Antigravity skill / slash command (`/launch-repo`) to trigger repository creation directly from chat.
   - Allow dynamic, context-aware customization of initial project files.
 
## Usage Guide

### 1. Command Line Interface (CLI)

Run `launch_repo.py` to bootstrap a new repository:

```powershell
# Basic usage (defaults to python-ai-agent in workspace root or ~/Projects)
python launch_repo.py my-new-agent

# Create a CLI tool with Git init and virtual environment
python launch_repo.py my-cli-tool --type python-cli --git --venv

# Preview generic project without writing files
python launch_repo.py my-tool --type python-generic --dry-run
```

#### Available Flags
| Flag | Description | Default |
| :--- | :--- | :--- |
| `name` / `--name` | Target project and directory name | *(Required)* |
| `--type` | Project archetype (`python-ai-agent`, `python-cli`, `python-generic`) | `python-ai-agent` |
| `--dest` | Destination root directory | Dynamic (`$PROJECTS_DIR` or `~/Projects`) |
| `--description` | Short project description | `"<name> project"` |
| `--git` | Initialize Git repository, initial commit, and auto-push to GitHub | `False` |
| `--github` | Create remote GitHub repo and push (auto-enabled when `--git` is set) | `True` *(if `--git`)* |
| `--no-github` | Keep Git local only; disable GitHub remote creation | `False` |
| `--public` | Make remote GitHub repository public (default is private) | `False` *(Private)* |
| `--venv` | Create virtual environment (`uv` if installed, or `venv`) | `False` |
| `--dry-run` | Preview file tree and actions without touching disk | `False` |
| `--overwrite` | Allow writing into an existing non-empty directory | `False` |

---

### 2. Antigravity Skill Integration

You can trigger repository creation directly in chat using the `/launch-repo` skill:
- *"Launch a new AI agent project called paper-summarizer"*
- *"Create a python-cli tool named log-parser with git and venv"*

---

### 3. What Gets Generated in New Repositories

Every newly created project automatically includes:
- **`README.md`**: Tailored quickstart, setup steps, and directory tree.
- **`docs/architecture.md`**: Mermaid diagram and component flow.
- **`.gitignore`**: Python, virtualenv, secrets, and agent cache exclusions.
- **`.env.example`**: Pre-configured environment variables and API keys.
- **`pyproject.toml`**: Modern packaging configuration with dev dependencies.
- **`src/<package_name>/`**: Starter source code tailored to the archetype.
- **`tests/`**: Basic `pytest` test suite.
- **`AGENTS.md` and `CLAUDE.md`**: Shared agent instructions (`CLAUDE.md` imports `AGENTS.md`), so Claude Code and Antigravity follow the same rules.
- **`.github/workflows/claude-review.yml` and `claude.yml`**: Claude reviews every pull request and answers `@claude` mentions. Both skip themselves until the `CLAUDE_CODE_OAUTH_TOKEN` repository secret exists.

### 4. GitHub Settings (`apply_repo_settings.py`)

`launch_repo.py --git` creates the GitHub repo, pushes the first commit, and then runs the standard settings. They are applied after the first push because the protection ruleset blocks direct pushes to `main`. Nothing is sent to Claude at that point: reviews only run on pull requests.

The standard settings are:
- Squash merge only (the PR title and body become the commit), and merged branches are deleted.
- A ruleset named `protect-default-branch` on the default branch: pull request required, no force pushes, no deletion, linear history, and no bypass for admins. Private repos need a paid GitHub plan for this.
- If `CLAUDE_CODE_OAUTH_TOKEN` is set in your environment, the launcher also stores it as the repo's Actions secret.

Run the same settings on existing repos. It is a dry run until you add `--apply`, and it needs `gh` logged in with admin rights:

```powershell
# Windows (PowerShell)
python apply_repo_settings.py --repo owner/name            # dry run
python apply_repo_settings.py --all                        # dry run for every repo you own (skips forks and archived)
python apply_repo_settings.py --all --apply

$env:CLAUDE_CODE_OAUTH_TOKEN = "<token from `claude setup-token`>"
python apply_repo_settings.py --repo owner/name --set-secret --apply
```

```bash
# Linux / macOS (bash)
python3 apply_repo_settings.py --repo owner/name            # dry run
python3 apply_repo_settings.py --all                        # dry run for every repo you own (skips forks and archived)
python3 apply_repo_settings.py --all --apply

export CLAUDE_CODE_OAUTH_TOKEN="<token from `claude setup-token`>"
python3 apply_repo_settings.py --repo owner/name --set-secret --apply
```

`--set-secret` only works with explicit `--repo` targets, so the token never lands on repos you did not name. Re-running is safe: repos that already match are left alone.

To keep merge commits or rebase merges for one repo, add it to `repo_settings_overrides.json`. The next run keeps the exception instead of reverting it:

```json
{ "owner/name": { "allow_rebase_merge": true } }
```

---

## Project Roadmap
- [x] Evaluation & Prioritization
- [x] Implement `launch_repo.py` CLI
- [x] Create Antigravity Skill definition (`skills/launch-repo/SKILL.md`)
- [x] Test repository creation on sample project
- [ ] Connect with Linear Idea-to-Project pipeline (Project #2)
