#!/usr/bin/env python3
"""
apply_repo_settings.py - Apply the standard GitHub settings to repositories.

Standard settings:
  * Squash merge only. The PR title and body become the commit, merged branches are deleted.
  * A ruleset on the default branch: pull request required, no force pushes, no deletion,
    linear history, and no bypass for admins.
  * Optionally the CLAUDE_CODE_OAUTH_TOKEN Actions secret (explicit repos only).

Dry run by default, pass --apply to change anything. Needs the GitHub CLI (`gh`), logged in as a
user with admin rights on the target repositories. Branch rulesets on private repositories need
a paid GitHub plan.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from collections.abc import Callable, Sequence
from pathlib import Path

RULESET_NAME = "protect-default-branch"
SECRET_NAME = "CLAUDE_CODE_OAUTH_TOKEN"
OVERRIDES_FILE = Path(__file__).resolve().parent / "repo_settings_overrides.json"
MERGE_METHOD_KEYS = ("allow_squash_merge", "allow_merge_commit", "allow_rebase_merge")

# A runner takes gh arguments plus optional stdin and returns the finished process.
Runner = Callable[[Sequence[str], "str | None"], subprocess.CompletedProcess]


class GhError(RuntimeError):
    """A gh call failed."""


def run_gh(args: Sequence[str], stdin: str | None = None) -> subprocess.CompletedProcess:
    """Run gh and capture its output. A non-zero exit does not raise."""
    return subprocess.run(["gh", *args], input=stdin, capture_output=True, text=True, encoding="utf-8")


def gh_json(runner: Runner, args: Sequence[str], stdin: str | None = None):
    """Run gh through the runner and parse stdout as JSON (None when stdout is empty)."""
    proc = runner(args, stdin)
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()
        raise GhError(detail or f"gh {' '.join(args)} exited with {proc.returncode}")
    return json.loads(proc.stdout) if proc.stdout.strip() else None


def merge_settings(overrides: dict | None = None) -> dict:
    """Repository merge settings: squash only, unless a per-repo override re-enables a method."""
    settings = {
        "allow_squash_merge": True,
        "allow_merge_commit": False,
        "allow_rebase_merge": False,
        "squash_merge_commit_title": "PR_TITLE",
        "squash_merge_commit_message": "PR_BODY",
        "delete_branch_on_merge": True,
    }
    for key, value in (overrides or {}).items():
        if key not in MERGE_METHOD_KEYS:
            raise ValueError(f"unsupported override '{key}', allowed: {', '.join(MERGE_METHOD_KEYS)}")
        settings[key] = bool(value)
    if not any(settings[key] for key in MERGE_METHOD_KEYS):
        raise ValueError("at least one merge method must stay enabled")
    return settings


def ruleset_payload() -> dict:
    """Ruleset for the default branch. The empty bypass list means admins are bound by it too."""
    return {
        "name": RULESET_NAME,
        "target": "branch",
        "enforcement": "active",
        "bypass_actors": [],
        "conditions": {"ref_name": {"include": ["~DEFAULT_BRANCH"], "exclude": []}},
        "rules": [
            {"type": "deletion"},
            {"type": "non_fast_forward"},
            {"type": "required_linear_history"},
            {
                "type": "pull_request",
                "parameters": {
                    "required_approving_review_count": 0,
                    "dismiss_stale_reviews_on_push": False,
                    "require_code_owner_review": False,
                    "require_last_push_approval": False,
                    "required_review_thread_resolution": False,
                },
            },
        ],
    }


def ruleset_matches(live: dict, desired: dict) -> bool:
    """True when the live ruleset already has everything the desired one sets."""
    for key in ("target", "enforcement", "bypass_actors"):
        if live.get(key) != desired[key]:
            return False
    want_ref = desired["conditions"]["ref_name"]
    have_ref = live.get("conditions", {}).get("ref_name", {})
    if have_ref.get("include") != want_ref["include"] or have_ref.get("exclude", []) != want_ref["exclude"]:
        return False
    have = {rule["type"]: rule.get("parameters") or {} for rule in live.get("rules", [])}
    want = {rule["type"]: rule.get("parameters") or {} for rule in desired["rules"]}
    if have.keys() != want.keys():
        return False
    return all(have[kind].get(key) == value for kind, params in want.items() for key, value in params.items())


def apply_to_repo(repo: str, *, apply: bool, runner: Runner = run_gh, overrides: dict | None = None) -> list[str]:
    """Apply merge settings and the default-branch ruleset. Returns one log line per step."""
    settings = merge_settings(overrides)
    lines: list[str] = []

    current = gh_json(runner, ["api", f"repos/{repo}"]) or {}
    changed = sorted(key for key, value in settings.items() if current.get(key) != value)
    if changed:
        verb = "update" if apply else "would update"
        lines.append(f"{repo}: {verb} merge settings ({', '.join(changed)})")
        if apply:
            # Send every field: GitHub wants the squash title and message set together.
            gh_json(runner, ["api", "-X", "PATCH", f"repos/{repo}", "--input", "-"], json.dumps(settings))
    else:
        lines.append(f"{repo}: merge settings already correct")

    desired = ruleset_payload()
    rulesets = gh_json(runner, ["api", f"repos/{repo}/rulesets"]) or []
    found = next((item for item in rulesets if item.get("name") == RULESET_NAME), None)
    if found is None:
        lines.append(f"{repo}: {'create' if apply else 'would create'} ruleset {RULESET_NAME}")
        if apply:
            gh_json(runner, ["api", "-X", "POST", f"repos/{repo}/rulesets", "--input", "-"], json.dumps(desired))
        return lines

    live = gh_json(runner, ["api", f"repos/{repo}/rulesets/{found['id']}"]) or {}
    if ruleset_matches(live, desired):
        lines.append(f"{repo}: ruleset {RULESET_NAME} already correct")
    else:
        lines.append(f"{repo}: {'update' if apply else 'would update'} ruleset {RULESET_NAME}")
        if apply:
            path = f"repos/{repo}/rulesets/{found['id']}"
            gh_json(runner, ["api", "-X", "PUT", path, "--input", "-"], json.dumps(desired))
    return lines


def set_secret(repo: str, value: str, *, apply: bool, runner: Runner = run_gh, name: str = SECRET_NAME) -> str:
    """Set an Actions secret. The value goes over stdin so it never appears in a command line."""
    if not apply:
        return f"{repo}: would set secret {name}"
    proc = runner(["secret", "set", name, "--repo", repo], value)
    if proc.returncode != 0:
        raise GhError((proc.stderr or proc.stdout or "").strip() or f"could not set secret {name}")
    return f"{repo}: set secret {name}"


def repo_from_url(text: str) -> str | None:
    """Pull owner/name out of a GitHub URL, or None when there is no match."""
    match = re.search(r"github\.com[/:]([\w.-]+/[\w.-]+?)(?:\.git)?(?:\s|$)", text)
    return match.group(1) if match else None


def resolve_repo(name: str, runner: Runner = run_gh) -> str:
    """Accept OWNER/NAME as is. A bare name belongs to the logged-in gh user."""
    if "/" in name:
        return name
    user = gh_json(runner, ["api", "user"]) or {}
    if not user.get("login"):
        raise GhError("could not read the logged-in gh user")
    return f"{user['login']}/{name}"


def list_owned_repos(runner: Runner = run_gh) -> list[str]:
    """Every non-fork, non-archived repository owned by the logged-in gh user."""
    data = gh_json(runner, ["repo", "list", "--limit", "1000", "--no-archived", "--source", "--json", "nameWithOwner"])
    return sorted(item["nameWithOwner"] for item in data or [])


def load_overrides(path: Path = OVERRIDES_FILE) -> dict[str, dict]:
    """Per-repo exceptions, keyed by lowercase owner/name: {"owner/name": {"allow_rebase_merge": true}}."""
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {repo.lower(): values for repo, values in data.items()}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Apply squash-only merges and default-branch protection to GitHub repositories.",
    )
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument(
        "--repo",
        action="append",
        metavar="OWNER/NAME",
        help="Repository to update (repeatable). A bare name belongs to the logged-in gh user.",
    )
    target.add_argument("--all", action="store_true", help="Every non-fork, non-archived repository you own.")
    parser.add_argument("--apply", action="store_true", help="Make the changes. Without it this is a dry run.")
    parser.add_argument(
        "--set-secret",
        action="store_true",
        help=f"Also set the {SECRET_NAME} Actions secret from the environment (needs --repo, not --all).",
    )
    parser.add_argument(
        "--secret-env",
        default=SECRET_NAME,
        help="Environment variable that holds the secret value.",
    )
    parser.add_argument(
        "--overrides",
        type=Path,
        default=OVERRIDES_FILE,
        help="JSON file with per-repo merge method exceptions.",
    )
    return parser


def main(argv: Sequence[str] | None = None, runner: Runner = run_gh) -> int:
    args = build_parser().parse_args(argv)

    if args.set_secret and args.all:
        print("--set-secret needs explicit --repo targets, not --all.", file=sys.stderr)
        return 2
    secret_value = ""
    if args.set_secret and args.apply:
        secret_value = os.environ.get(args.secret_env, "")
        if not secret_value:
            print(f"Environment variable {args.secret_env} is empty or not set.", file=sys.stderr)
            return 2

    try:
        repos = list_owned_repos(runner) if args.all else [resolve_repo(name, runner) for name in args.repo]
        overrides = load_overrides(args.overrides)
    except (GhError, OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if not args.apply:
        print("Dry run: nothing will be changed. Pass --apply to make these changes.\n")

    failed = 0
    for repo in repos:
        try:
            lines = apply_to_repo(repo, apply=args.apply, runner=runner, overrides=overrides.get(repo.lower()))
            if args.set_secret:
                lines.append(set_secret(repo, secret_value, apply=args.apply, runner=runner))
        except (GhError, ValueError) as exc:
            failed += 1
            print(f"{repo}: FAILED: {exc}", file=sys.stderr)
            continue
        print("\n".join(lines))

    print(f"\n{len(repos) - failed} ok, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
