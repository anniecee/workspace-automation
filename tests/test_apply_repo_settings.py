import json
import subprocess

import pytest

import apply_repo_settings as ars

REPO = "me/demo"
WRONG_SETTINGS = {
    "allow_squash_merge": True,
    "allow_merge_commit": True,
    "allow_rebase_merge": True,
    "delete_branch_on_merge": False,
}


class FakeGh:
    """Stands in for gh: records every call and answers from canned data."""

    def __init__(self, repo=None, rulesets=None, live_ruleset=None, fail_on=None, owned=None):
        self.repo = WRONG_SETTINGS if repo is None else repo
        self.rulesets = rulesets or []
        self.live_ruleset = live_ruleset or {}
        self.fail_on = fail_on
        self.owned = owned or []
        self.calls = []

    def __call__(self, args, stdin=None):
        args = list(args)
        self.calls.append((args, stdin))
        if self.fail_on and any(self.fail_on in part for part in args):
            return subprocess.CompletedProcess(args, 1, "", "HTTP 403: Upgrade to GitHub Pro")
        return subprocess.CompletedProcess(args, 0, json.dumps(self._answer(args)), "")

    def _answer(self, args):
        if args[:2] == ["repo", "list"]:
            return [{"nameWithOwner": name} for name in self.owned]
        if args == ["api", "user"]:
            return {"login": "me"}
        if "-X" in args or args[0] == "secret":
            return {}
        path = args[1]
        if path.endswith("/rulesets"):
            return self.rulesets
        if "/rulesets/" in path:
            return self.live_ruleset
        return self.repo

    def writes(self):
        return [(a, s) for a, s in self.calls if "-X" in a or a[0] == "secret"]


def matching_live_ruleset():
    live = ars.ruleset_payload()
    live["id"] = 7
    live["rules"][3]["parameters"]["allowed_merge_methods"] = ["squash"]
    return live


def test_default_policy_is_squash_only_with_a_protected_default_branch():
    assert ars.merge_settings() == {
        "allow_squash_merge": True,
        "allow_merge_commit": False,
        "allow_rebase_merge": False,
        "squash_merge_commit_title": "PR_TITLE",
        "squash_merge_commit_message": "PR_BODY",
        "delete_branch_on_merge": True,
    }
    ruleset = ars.ruleset_payload()
    assert ruleset["enforcement"] == "active"
    assert ruleset["bypass_actors"] == []
    assert ruleset["conditions"]["ref_name"]["include"] == ["~DEFAULT_BRANCH"]
    assert sorted(rule["type"] for rule in ruleset["rules"]) == [
        "deletion",
        "non_fast_forward",
        "pull_request",
        "required_linear_history",
    ]


def test_dry_run_makes_no_changes():
    fake = FakeGh()
    lines = ars.apply_to_repo(REPO, apply=False, runner=fake)
    assert any("would update merge settings" in line for line in lines)
    assert any("would create ruleset" in line for line in lines)
    assert fake.writes() == []


def test_apply_patches_settings_and_creates_ruleset():
    fake = FakeGh()
    ars.apply_to_repo(REPO, apply=True, runner=fake)
    (patch_args, patch_body), (post_args, post_body) = fake.writes()
    assert patch_args[:4] == ["api", "-X", "PATCH", f"repos/{REPO}"]
    assert json.loads(patch_body) == ars.merge_settings()
    assert post_args[:4] == ["api", "-X", "POST", f"repos/{REPO}/rulesets"]
    assert json.loads(post_body) == ars.ruleset_payload()


def test_already_correct_repo_is_left_alone():
    fake = FakeGh(
        repo=ars.merge_settings(),
        rulesets=[{"id": 7, "name": ars.RULESET_NAME}],
        live_ruleset=matching_live_ruleset(),
    )
    lines = ars.apply_to_repo(REPO, apply=True, runner=fake)
    assert fake.writes() == []
    assert lines == [f"{REPO}: merge settings already correct", f"{REPO}: ruleset {ars.RULESET_NAME} already correct"]


def test_drifted_ruleset_is_updated_in_place():
    live = matching_live_ruleset()
    live["enforcement"] = "evaluate"
    fake = FakeGh(repo=ars.merge_settings(), rulesets=[{"id": 7, "name": ars.RULESET_NAME}], live_ruleset=live)
    ars.apply_to_repo(REPO, apply=True, runner=fake)
    ((args, body),) = fake.writes()
    assert args[:4] == ["api", "-X", "PUT", f"repos/{REPO}/rulesets/7"]
    assert json.loads(body)["enforcement"] == "active"


def test_ruleset_with_an_extra_rule_counts_as_drift():
    live = matching_live_ruleset()
    live["rules"].append({"type": "creation"})
    assert not ars.ruleset_matches(live, ars.ruleset_payload())


def test_override_re_enables_a_merge_method():
    fake = FakeGh()
    ars.apply_to_repo(REPO, apply=True, runner=fake, overrides={"allow_rebase_merge": True})
    body = json.loads(fake.writes()[0][1])
    assert body["allow_rebase_merge"] is True
    assert body["allow_squash_merge"] is True
    assert body["allow_merge_commit"] is False


def test_bad_overrides_are_rejected():
    with pytest.raises(ValueError, match="unsupported override"):
        ars.merge_settings({"delete_branch_on_merge": False})
    with pytest.raises(ValueError, match="at least one merge method"):
        ars.merge_settings({"allow_squash_merge": False})


def test_secret_value_travels_over_stdin_only():
    fake = FakeGh()
    line = ars.set_secret(REPO, "s3cret-token", apply=True, runner=fake)
    ((args, stdin),) = fake.writes()
    assert args == ["secret", "set", ars.SECRET_NAME, "--repo", REPO]
    assert stdin == "s3cret-token"
    assert "s3cret-token" not in line


def test_secret_dry_run_makes_no_call():
    fake = FakeGh()
    assert "would set secret" in ars.set_secret(REPO, "", apply=False, runner=fake)
    assert fake.calls == []


def test_gh_failure_becomes_gh_error():
    fake = FakeGh(fail_on="rulesets")
    with pytest.raises(ars.GhError, match="Upgrade to GitHub Pro"):
        ars.apply_to_repo(REPO, apply=False, runner=fake)


def test_main_dry_run_prints_banner_and_summary(capsys):
    assert ars.main(["--repo", REPO], runner=FakeGh()) == 0
    out = capsys.readouterr().out
    assert "Dry run" in out
    assert "1 ok, 0 failed" in out


def test_main_rejects_set_secret_with_all(capsys):
    assert ars.main(["--all", "--set-secret", "--apply"], runner=FakeGh()) == 2
    assert "explicit --repo" in capsys.readouterr().err


def test_main_needs_the_secret_in_the_environment(monkeypatch, capsys):
    monkeypatch.delenv(ars.SECRET_NAME, raising=False)
    assert ars.main(["--repo", REPO, "--set-secret", "--apply"], runner=FakeGh()) == 2
    assert "empty or not set" in capsys.readouterr().err


def test_main_sets_the_secret_when_applying(monkeypatch):
    monkeypatch.setenv(ars.SECRET_NAME, "tok")
    fake = FakeGh(
        repo=ars.merge_settings(), rulesets=[{"id": 7, "name": ars.RULESET_NAME}], live_ruleset=matching_live_ruleset()
    )
    assert ars.main(["--repo", REPO, "--set-secret", "--apply"], runner=fake) == 0
    assert [a[0] for a, _ in fake.writes()] == ["secret"]


def test_main_keeps_going_after_one_repo_fails(capsys):
    class FailsForFirst(FakeGh):
        def __call__(self, args, stdin=None):
            if "me/private" in " ".join(args):
                return subprocess.CompletedProcess(args, 1, "", "HTTP 403")
            return super().__call__(args, stdin)

    fake = FailsForFirst()
    assert ars.main(["--repo", "me/private", "--repo", "me/public", "--apply"], runner=fake) == 1
    captured = capsys.readouterr()
    assert "me/private: FAILED: HTTP 403" in captured.err
    assert "1 ok, 1 failed" in captured.out
    assert any("repos/me/public" in " ".join(args) for args, _ in fake.writes())


def test_main_applies_per_repo_overrides(tmp_path):
    overrides = tmp_path / "overrides.json"
    overrides.write_text(json.dumps({"Me/Demo": {"allow_merge_commit": True}}), encoding="utf-8")
    fake = FakeGh()
    assert ars.main(["--repo", REPO, "--apply", "--overrides", str(overrides)], runner=fake) == 0
    assert json.loads(fake.writes()[0][1])["allow_merge_commit"] is True


def test_list_owned_repos_is_sorted():
    assert ars.list_owned_repos(FakeGh(owned=["me/b", "me/a"])) == ["me/a", "me/b"]


def test_bare_repo_name_gets_the_gh_user():
    assert ars.resolve_repo("demo", FakeGh()) == "me/demo"
    assert ars.resolve_repo("other/demo", FakeGh()) == "other/demo"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("https://github.com/me/demo\n", "me/demo"),
        ("https://github.com/me/demo.git", "me/demo"),
        ("git@github.com:me/my.repo.git\n", "me/my.repo"),
        ("created repository", None),
    ],
)
def test_repo_from_url(text, expected):
    assert ars.repo_from_url(text) == expected


def test_missing_overrides_file_means_no_overrides(tmp_path):
    assert ars.load_overrides(tmp_path / "nope.json") == {}
