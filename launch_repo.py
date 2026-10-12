#!/usr/bin/env python3
"""
launch_repo.py - Automated repository launcher for personal AI projects, CLIs, and tools.
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import apply_repo_settings


def sanitize_names(name: str) -> Tuple[str, str]:
    """
    Sanitize and format project and package names.
    Returns (project_name, package_name).
    """
    # Clean project name: lowercase, letters, numbers, hyphens, underscores
    project_name = re.sub(r"[^\w\-_]", "-", name.strip().lower())
    project_name = re.sub(r"-+", "-", project_name).strip("-_")
    if not project_name:
        raise ValueError(f"Invalid project name: '{name}'")

    # Python package name must be valid identifier (snake_case)
    package_name = re.sub(r"[^\w]", "_", project_name)
    package_name = re.sub(r"_+", "_", package_name).strip("_")
    if package_name[0].isdigit():
        package_name = f"pkg_{package_name}"

    return project_name, package_name


def get_default_dest() -> Path:
    """Resolve default destination directory for new repositories.

    Checks environment overrides, sibling workspace structures, and system defaults.
    """
    env_dest = os.getenv("PROJECTS_DIR") or os.getenv("WORKSPACE_ROOT") or os.getenv("AI_HUB_ROOT")
    if env_dest:
        dest = Path(env_dest)
        if (dest / "Personal").is_dir():
            return dest / "Personal"
        return dest

    # Dynamic sibling resolution in AI Hub structure:
    # workspace-automation lives in <hub>/Shared/workspace-automation.
    # Check if sibling <hub>/Personal exists.
    try:
        hub_root = Path(__file__).resolve().parents[2]
        personal_dir = hub_root / "Personal"
        if personal_dir.is_dir():
            return personal_dir
    except (IndexError, OSError):
        pass

    # Standard platform fallback
    if os.name == "nt":
        return Path.home() / "Projects"
    return Path("/home/ubuntu/projects") if Path("/home/ubuntu/projects").is_dir() else Path.home() / "projects"


def render_template(content: str, context: Dict[str, str]) -> str:
    """Perform simple template substitution for {{key}} placeholders."""
    result = content
    for key, value in context.items():
        result = result.replace(f"{{{{{key}}}}}", value)
    return result


def get_template_dir() -> Path:
    """Locate the templates directory relative to this script."""
    template_dir = Path(__file__).resolve().parent / "templates"
    if not template_dir.exists():
        raise FileNotFoundError(f"Templates directory not found at: {template_dir}")
    return template_dir


ARCHETYPE_ALIASES = {
    "ai-agent": "python-ai-agent",
    "python-agent": "python-ai-agent",
    "generic": "python-generic",
}


def collect_files_to_generate(
    template_dir: Path,
    archetype: str,
    context: Dict[str, str],
) -> List[Tuple[Path, Path]]:
    """
    Collect source template files and their relative destination paths.
    Returns a list of (template_source_file, relative_dest_path).
    """
    files_to_copy: List[Tuple[Path, Path]] = []
    package_name = context["package_name"]

    # 1. Common templates
    common_dir = template_dir / "common"
    if common_dir.exists():
        for root, _, files in os.walk(common_dir):
            for file in files:
                src_path = Path(root) / file
                rel_path = src_path.relative_to(common_dir)
                files_to_copy.append((src_path, rel_path))

    # 2. Archetype templates (resolve aliases if any)
    canonical_type = ARCHETYPE_ALIASES.get(archetype, archetype)
    arch_key = canonical_type.replace("-", "_")
    arch_dir = template_dir / arch_key
    if not arch_dir.exists():
        raise ValueError(
            f"Unknown project type '{archetype}'. Available templates: python-ai-agent, python-cli, python-generic"
        )

    for root, _, files in os.walk(arch_dir):
        for file in files:
            src_path = Path(root) / file
            rel_path = src_path.relative_to(arch_dir)
            parts = list(rel_path.parts)
            # Map src/ -> src/<package_name>/
            if parts and parts[0] == "src":
                parts.insert(1, package_name)
                dest_rel_path = Path(*parts)
            else:
                dest_rel_path = rel_path
            files_to_copy.append((src_path, dest_rel_path))

    return files_to_copy


def protect_new_repo(repo_url: str, project_name: str) -> None:
    """Apply the standard merge settings and main protection to a repo that was just pushed.

    Runs after the first push because the protection ruleset blocks direct pushes to main.
    A failure only prints a warning, the repository itself is already created.
    """
    try:
        repo = apply_repo_settings.repo_from_url(repo_url) or apply_repo_settings.resolve_repo(project_name)
        for line in apply_repo_settings.apply_to_repo(repo, apply=True):
            print(f" [+] {line}")
        token = os.getenv(apply_repo_settings.SECRET_NAME)
        if token:
            print(f" [+] {apply_repo_settings.set_secret(repo, token, apply=True)}")
        else:
            print(f" [i] {apply_repo_settings.SECRET_NAME} is not set, so Claude review stays idle until the secret exists.")
    except (apply_repo_settings.GhError, ValueError, OSError) as e:
        print(f" [!] Could not apply GitHub settings: {e}", file=sys.stderr)
        script = Path(__file__).resolve().with_name("apply_repo_settings.py")
        print(f'     Run later: python "{script}" --repo {project_name} --apply', file=sys.stderr)


def launch(
    name: str,
    project_type: str = "python-ai-agent",
    dest_root: Optional[str] = None,
    description: Optional[str] = None,
    init_git: bool = False,
    init_github: bool = False,
    is_public: bool = False,
    create_venv: bool = False,
    dry_run: bool = False,
    overwrite: bool = False,
) -> int:
    """Main launch routine."""
    dest_root = dest_root or str(get_default_dest())
    project_type = ARCHETYPE_ALIASES.get(project_type, project_type)
    project_name, package_name = sanitize_names(name)
    project_desc = description or f"{project_name} project"

    dest_dir = Path(dest_root).resolve() / project_name

    context = {
        "project_name": project_name,
        "package_name": package_name,
        "project_description": project_desc,
    }

    template_dir = get_template_dir()
    files_to_generate = collect_files_to_generate(template_dir, project_type, context)

    # Ensure UTF-8 output in Windows consoles if supported
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    if hasattr(sys.stderr, "reconfigure"):
        try:
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    print("=" * 60)
    print(f">> Launch-Repo: {project_name}")
    print(f"   Type:        {project_type}")
    print(f"   Package:     {package_name}")
    print(f"   Destination: {dest_dir}")
    print(f"   Git Init:    {init_git}")
    print(f"   GitHub Push: {init_git and init_github}")
    print(f"   Venv:        {create_venv}")
    print(f"   Dry Run:     {dry_run}")
    print("=" * 60)

    if dest_dir.exists() and any(dest_dir.iterdir()):
        if not overwrite and not dry_run:
            print(f"[!] Error: Destination directory '{dest_dir}' already exists and is not empty.", file=sys.stderr)
            print("    Use --overwrite to proceed anyway.", file=sys.stderr)
            return 1
        elif overwrite:
            print("[!] Warning: Target directory exists. Overwrite enabled.")

    # Process files
    for src_file, rel_dest in files_to_generate:
        target_file = dest_dir / rel_dest
        if dry_run:
            print(f" [dry-run] Would create: {rel_dest}")
        else:
            target_file.parent.mkdir(parents=True, exist_ok=True)
            try:
                content = src_file.read_text(encoding="utf-8")
                rendered = render_template(content, context)
                target_file.write_text(rendered, encoding="utf-8")
            except UnicodeDecodeError:
                # Binary files if any
                shutil.copy2(src_file, target_file)
            print(f" [+] Created: {rel_dest}")

    if dry_run:
        if init_git:
            print(" [dry-run] Would run: git init && git add . && git commit")
            if init_github:
                vis = "public" if is_public else "private"
                print(f" [dry-run] Would run: gh repo create {project_name} --{vis} --source=. --remote=origin --push")
                print(f" [dry-run] Would run: apply_repo_settings.py --repo {project_name} --apply")
        if create_venv:
            print(" [dry-run] Would create virtual environment (.venv)")
        print("\n[+] Dry run complete! No files were modified.")
        return 0

    # Git initialization
    if init_git:
        try:
            print("\n[*] Initializing Git repository...")
            subprocess.run(["git", "init"], cwd=dest_dir, check=True, capture_output=True, text=True)
            subprocess.run(["git", "add", "."], cwd=dest_dir, check=True, capture_output=True, text=True)
            subprocess.run(
                ["git", "commit", "-m", f"Initial commit for {project_name} from launch-repo"],
                cwd=dest_dir,
                check=True,
                capture_output=True,
                text=True,
            )
            print(" [+] Git repository initialized and initial commit created.")
        except Exception as e:
            print(f" [!] Git initialization failed: {e}", file=sys.stderr)

        # GitHub Remote Creation & Push
        if init_github:
            gh_path = shutil.which("gh")
            if not gh_path:
                print("\n[i] GitHub CLI ('gh') not found. Skipping GitHub repository creation.")
            else:
                visibility_flag = "--public" if is_public else "--private"
                print(f"\n[*] Creating GitHub repository ({'public' if is_public else 'private'}) & pushing...")
                gh_cmd = [
                    "gh", "repo", "create",
                    project_name,
                    visibility_flag,
                    "--source=.",
                    "--remote=origin",
                    "--push",
                    "-d", project_desc,
                ]
                try:
                    res = subprocess.run(gh_cmd, cwd=dest_dir, check=True, capture_output=True, text=True)
                    out_text = res.stdout.strip() or f"https://github.com/{project_name}"
                    print(f" [+] GitHub repository created & pushed: {out_text}")
                    protect_new_repo(out_text, project_name)
                except subprocess.CalledProcessError as e:
                    err_msg = (e.stderr or e.stdout or str(e)).strip()
                    print(f" [!] GitHub repository creation failed: {err_msg}", file=sys.stderr)

    # Virtual Environment
    if create_venv:
        print("\n[*] Setting up virtual environment...")
        uv_path = shutil.which("uv")
        try:
            if uv_path:
                print(" [i] Found 'uv', creating venv using uv...")
                subprocess.run(["uv", "venv"], cwd=dest_dir, check=True)
            else:
                print(" [i] 'uv' not found. Using 'python -m venv'...")
                subprocess.run([sys.executable, "-m", "venv", ".venv"], cwd=dest_dir, check=True)
            print(" [+] Virtual environment created at .venv")
        except Exception as e:
            print(f" [!] Failed to create virtual environment: {e}", file=sys.stderr)

    # Summary
    print("\n" + "=" * 60)
    print(f"[+] Successfully launched {project_name}!")
    print("\nNext steps:")
    print(f"  cd \"{dest_dir}\"")
    if os.name == "nt":
        print("  .venv\\Scripts\\activate")
    else:
        print("  source .venv/bin/activate")
    print("  pip install -e \".[dev]\"")
    print("=" * 60)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Launch a new standardized repository with best practices.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "name",
        nargs="?",
        help="Name of the project/repository (e.g. my-cool-agent).",
    )
    parser.add_argument(
        "--name",
        dest="flag_name",
        help="Alternative flag to specify project name.",
    )
    parser.add_argument(
        "--type",
        choices=["python-ai-agent", "python-cli", "python-generic", "ai-agent", "generic"],
        default="python-ai-agent",
        help="Template archetype to use.",
    )
    parser.add_argument(
        "--dest",
        default=str(get_default_dest()),
        help="Parent directory where the project directory will be created.",
    )
    parser.add_argument(
        "--description",
        help="Short description of the project.",
    )
    parser.add_argument(
        "--git",
        action="store_true",
        help="Initialize a Git repository with an initial commit.",
    )
    parser.add_argument(
        "--github",
        dest="github",
        action="store_true",
        default=None,
        help="Create a remote GitHub repository and push (default: True when --git is enabled).",
    )
    parser.add_argument(
        "--no-github",
        dest="github",
        action="store_false",
        help="Disable remote GitHub repository creation even when --git is enabled.",
    )
    parser.add_argument(
        "--public",
        action="store_true",
        help="Make the remote GitHub repository public (default: private).",
    )
    parser.add_argument(
        "--venv",
        action="store_true",
        help="Create a Python virtual environment (.venv).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview generated files and commands without writing to disk.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow writing into an existing non-empty directory.",
    )

    args = parser.parse_args()

    project_name = args.flag_name or args.name
    if not project_name:
        parser.print_help()
        print("\n❌ Error: Project name is required.", file=sys.stderr)
        return 1

    init_git = args.git or (args.github is True)
    init_github = args.github if args.github is not None else init_git

    return launch(
        name=project_name,
        project_type=args.type,
        dest_root=args.dest,
        description=args.description,
        init_git=init_git,
        init_github=init_github,
        is_public=args.public,
        create_venv=args.venv,
        dry_run=args.dry_run,
        overwrite=args.overwrite,
    )


if __name__ == "__main__":
    sys.exit(main())
