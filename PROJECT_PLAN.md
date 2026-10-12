# Project Plan: Workspace Automation & Launch-Repo

## Context
This project is **Project #1** in our overall productivity and automation roadmap:
1. **Repo Creation Automation (This Project)**
2. Idea & Project Management Workflow (Linear pipeline)
3. Job Search & Application Assistant
4. LLM Wiki / Knowledge Base
5. Daily AI News & Capabilities Digest

## Architecture & Design
- **Engine**: Python script (`launch_repo.py`) supporting flags:
  - `--name <project-name>`: Project directory name.
  - `--type <type>`: Template type (`python-ai-agent`, `python-cli`, `python-generic`).
  - `--dest <path>`: Target directory (defaults to dynamic workspace root or `~/Projects`).
  - `--git`: Initialize git repository and create initial commit.
  - `--venv`: Set up Python virtual environment (e.g. `uv` or `python -m venv`).
- **Skill Wrapper**: An Antigravity skill (`skills/launch-repo/SKILL.md`) that wraps the CLI and enables chat-based invocation (`/launch-repo`).

## Implementation Checklist
- [x] Create `launch_repo.py` script with argument parsing and template rendering.
- [x] Add templates for `.gitignore`, `.env.example`, and structured `README.md`.
- [x] Create the Antigravity Skill configuration (`skills/launch-repo/SKILL.md`).
- [x] Test end-to-end repo creation with a dummy project.
