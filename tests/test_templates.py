from pathlib import Path

import pytest

import apply_repo_settings
import launch_repo

ROOT = Path(__file__).resolve().parent.parent
WORKFLOWS = ("claude.yml", "claude-review.yml")


@pytest.mark.parametrize("name", WORKFLOWS)
def test_own_workflows_match_the_templates(name):
    own = ROOT / ".github" / "workflows" / name
    template = ROOT / "templates" / "common" / ".github" / "workflows" / name
    assert own.read_text(encoding="utf-8") == template.read_text(encoding="utf-8")


@pytest.mark.parametrize("project_type", ["python-ai-agent", "python-cli", "python-generic"])
def test_new_repos_get_agent_files_and_workflows(tmp_path, project_type):
    code = launch_repo.launch(
        "demo-tool", project_type=project_type, dest_root=str(tmp_path), description="Demo project"
    )
    assert code == 0
    project = tmp_path / "demo-tool"
    for rel in ("AGENTS.md", "CLAUDE.md", ".github/workflows/claude.yml", ".github/workflows/claude-review.yml"):
        assert (project / rel).is_file(), rel

    agents = (project / "AGENTS.md").read_text(encoding="utf-8")
    assert "Demo project" in agents
    assert "src/demo_tool/" in agents
    assert "{{" not in agents

    # The renderer must leave GitHub Actions expressions alone.
    review = (project / ".github" / "workflows" / "claude-review.yml").read_text(encoding="utf-8")
    assert "${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}" in review


@pytest.mark.parametrize("path", sorted((ROOT / "templates" / "common").rglob("*.md")))
def test_templates_use_plain_hyphens(path):
    text = path.read_text(encoding="utf-8")
    assert chr(0x2014) not in text
    assert chr(0x2013) not in text


def test_protect_new_repo_applies_settings_and_secret(monkeypatch, capsys):
    calls = []
    monkeypatch.setattr(
        apply_repo_settings, "apply_to_repo", lambda repo, **kw: calls.append(("settings", repo)) or ["done"]
    )
    monkeypatch.setattr(
        apply_repo_settings, "set_secret", lambda repo, value, **kw: calls.append(("secret", value)) or "secret set"
    )
    monkeypatch.setenv(apply_repo_settings.SECRET_NAME, "tok")
    launch_repo.protect_new_repo("https://github.com/me/demo-tool\n", "demo-tool")
    assert calls == [("settings", "me/demo-tool"), ("secret", "tok")]
    assert "tok" not in capsys.readouterr().out


def test_protect_new_repo_without_a_token_says_so(monkeypatch, capsys):
    monkeypatch.setattr(apply_repo_settings, "apply_to_repo", lambda repo, **kw: [])
    monkeypatch.delenv(apply_repo_settings.SECRET_NAME, raising=False)
    launch_repo.protect_new_repo("https://github.com/me/demo-tool", "demo-tool")
    assert "is not set" in capsys.readouterr().out


def test_protect_new_repo_failure_only_warns(monkeypatch, capsys):
    def boom(repo, **kw):
        raise apply_repo_settings.GhError("HTTP 403")

    monkeypatch.setattr(apply_repo_settings, "apply_to_repo", boom)
    launch_repo.protect_new_repo("https://github.com/me/demo-tool", "demo-tool")
    err = capsys.readouterr().err
    assert "HTTP 403" in err
    assert 'apply_repo_settings.py" --repo demo-tool --apply' in err
