"""Base hooks (gitleaks, pre-commit-hooks): real pre-commit runs on tests/fixtures/base/."""

import re

import pytest

from conftest import commit, git, make_repo, run_pre_commit

BASE = ["gitleaks", "pre-commit-hooks"]

# hook names as pre-commit prints them
GITLEAKS = "Detect hardcoded secrets"
HISTORY = "gitleaks (all commits)"
PRIVATE_KEY = "detect private key"


@pytest.mark.parametrize(
    "fixture,on_commit,in_ci",
    [
        ("base/clean", set(), set()),
        ("base/secret-generic", {GITLEAKS}, {HISTORY}),
        ("base/secret-mcp", {GITLEAKS}, {HISTORY}),
        ("base/private-key", {GITLEAKS, PRIVATE_KEY}, {HISTORY, PRIVATE_KEY}),
    ],
)
def test_fixture(tmp_path, fixture, on_commit, in_ci):
    repo = make_repo(tmp_path, fixture, BASE)

    # a developer commits the fixture: hooks see the staged changes
    failed, out = run_pre_commit(repo)
    assert failed == on_commit, out

    # CI: the same files, committed, with the manual stage included
    commit(repo)
    failed, out = run_pre_commit(repo, "--all-files", "--hook-stage", "manual")
    assert failed == in_ci, out


def test_mcp_rule_comes_from_the_shipped_config(tmp_path):
    # MY_SERVICE_PAT matches no default gitleaks rule, only the optional MCP rule in .gitleaks.toml
    repo = make_repo(tmp_path, "base/secret-mcp", BASE)
    _, out = run_pre_commit(repo)
    assert re.search(r"RuleID:\s+mcp-config-secret", out), out


def test_history_hook_finds_a_secret_removed_in_a_later_commit(tmp_path):
    repo = make_repo(tmp_path, "base/secret-generic", BASE)
    commit(repo, "add a secret")
    git(repo, "rm", "-q", "app.env")
    commit(repo, "remove it again")

    # --all-files alone misses it: the gitleaks hook only scans staged changes
    failed, out = run_pre_commit(repo, "--all-files")
    assert failed == set(), out

    # the history hook, as CI runs it, finds it in the earlier commit
    failed, out = run_pre_commit(repo, "--all-files", "--hook-stage", "manual")
    assert failed == {HISTORY}, out
