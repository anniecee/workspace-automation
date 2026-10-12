---
name: launch-repo
description: >-
  Automates the creation and setup of standardized, agent-ready repositories (AI agents, Python CLIs, and generic tools) with git, venvs, and configs. Use when the user asks to create, initialize, or launch a new repository or project.
---

# Launch Repo Skill

Use this skill to create and configure brand-new repositories with consistent best practices, directory layouts, environment configurations, and documentation.

---

## Tool Locations & Setup
- **Windows**: Local workspace directory or `$env:USERPROFILE\Projects\workspace-automation`
- **Linux**: Local shared directory or `$HOME/projects/workspace-automation`
- **GitHub Repository**: [anniecee/workspace-automation](https://github.com/anniecee/workspace-automation) (`git@github.com:anniecee/workspace-automation.git` or `https://github.com/anniecee/workspace-automation.git`)

> [!IMPORTANT] Repository Availability Check
> If the `workspace-automation` directory is not available locally, clone it from GitHub before executing:
> - **Windows**:
>   ```powershell
>   git clone https://github.com/anniecee/workspace-automation.git "$env:USERPROFILE\Projects\workspace-automation"
>   ```
> - **Linux**:
>   ```bash
>   git clone https://github.com/anniecee/workspace-automation.git "$HOME/projects/workspace-automation"
>   ```

---

## Workflow

1. **Gather Requirements**:
   - Determine the project name (e.g. `linear-workflow-sync`).
   - Determine the project type:
     - `python-ai-agent`: Multi-agent systems, LLM tools, or autonomous workflows.
     - `python-cli`: Standalone CLI utilities and tools.
     - `python-generic`: General-purpose Python packages.
   - Determine if Git initialization (`--git`) and virtual environment (`--venv`) are needed. Note: `--git` automatically creates a private repository on GitHub via `gh`, pushes the initial commit, and then applies squash-only merges and a protected `main` (use `--no-github` for local-only or `--public` for public).
   - Confirm target destination (defaults to dynamically resolved workspace root or `~/Projects`).

2. **Execute the Launcher**:
   Run `launch_repo.py` located in `workspace-automation`:
   ```powershell
   python <path-to-workspace-automation>/launch_repo.py <project-name> --type <type> --git --venv
   ```

3. **Verify Generation**:
   - Verify that the target folder was created with `.gitignore`, `.env.example`, `pyproject.toml`, `README.md`, and `src/`.
   - Report the status and next steps to the user.
