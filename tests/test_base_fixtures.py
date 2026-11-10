"""Base hooks (gitleaks, pre-commit-hooks): real pre-commit runs on tests/fixtures/base/."""

import re

import pytest

from conftest import commit, expect, git, make_repo, run_pre_commit, write

BASE = ["gitleaks", "pre-commit-hooks"]

# hook names as pre-commit prints them
GITLEAKS = "Detect hardcoded secrets"
HISTORY = "Detect hardcoded secrets (full git history)"
PRIVATE_KEY = "detect private key"
MERGE_CONFLICT = "check for merge conflicts"

ON_COMMIT = {GITLEAKS, PRIVATE_KEY, MERGE_CONFLICT}
IN_CI = ON_COMMIT | {HISTORY}


@pytest.mark.parametrize(
    "fixture,fail_on_commit,fail_in_ci",
    [
        ("base/clean", set(), set()),
        ("base/secret", {GITLEAKS}, {HISTORY}),
        ("base/secret-mcp", {GITLEAKS}, {HISTORY}),
        ("base/private-key", {GITLEAKS, PRIVATE_KEY}, {HISTORY, PRIVATE_KEY}),
    ],
)
def test_fixture(tmp_path, fixture, fail_on_commit, fail_in_ci):
    repo = make_repo(tmp_path, BASE, fixture)

    # a developer commits the fixture: hooks see the staged changes
    expect(*run_pre_commit(repo), ON_COMMIT, fail_on_commit)

    # CI: the same files, committed, with the manual stage included
    commit(repo)
    expect(*run_pre_commit(repo, "--all-files", "--hook-stage", "manual"), IN_CI, fail_in_ci)


def test_mcp_rule_comes_from_the_shipped_config(tmp_path):
    # MY_SERVICE_PAT matches no default gitleaks rule, only the optional MCP rule in .gitleaks.toml
    repo = make_repo(tmp_path, BASE, "base/secret-mcp")
    _, out = run_pre_commit(repo)
    assert re.search(r"RuleID:\s+mcp-config-secret", out), out


def test_history_hook_finds_a_secret_removed_in_a_later_commit(tmp_path):
    repo = make_repo(tmp_path, BASE, "base/secret")
    commit(repo, "add a secret")
    git(repo, "rm", "-q", "app.env")
    commit(repo, "remove it again")

    # --all-files alone misses it: the gitleaks hook only scans staged changes
    expect(*run_pre_commit(repo, "--all-files"), ON_COMMIT, set())

    # the history hook, as CI runs it, finds it in the earlier commit
    expect(*run_pre_commit(repo, "--all-files", "--hook-stage", "manual"), IN_CI, {HISTORY})


def test_merge_conflict_markers_block_during_a_merge(tmp_path):
    # check-merge-conflict only looks while a merge is in progress, so make a real conflict
    repo = make_repo(tmp_path, BASE)
    write(repo, "notes.txt", "base\n")
    commit(repo, "base")
    git(repo, "switch", "-q", "-c", "other")
    write(repo, "notes.txt", "theirs\n")
    commit(repo, "theirs")
    git(repo, "switch", "-q", "main")
    write(repo, "notes.txt", "ours\n")
    commit(repo, "ours")
    assert git(repo, "merge", "-q", "other", check=False).returncode != 0, "expected a conflict"
    git(repo, "add", "notes.txt")  # staged with the conflict markers still in it

    expect(*run_pre_commit(repo), ON_COMMIT, {MERGE_CONFLICT})
