"""Terraform and Docker (checkov, tflint, hadolint): real pre-commit runs on tests/fixtures/.

Everything here starts in warn mode: findings print, but the commit goes through. Each
tool's warn switch is one line (soft-fail, --force, no-fail); deleting it makes the
same findings block.
"""

import json
import os
import re
import shlex

import pytest

from conftest import CATALOG, FIXTURES, commit, expect, git, make_repo, run_pre_commit, write

BASE = ["gitleaks", "pre-commit-hooks"]
BASE_HOOKS = {"Detect hardcoded secrets", "detect private key", "check for merge conflicts"}
CHECKOV, TFLINT, HADOLINT = "Checkov", "tflint", "Hadolint"

STACKS = {
    "terraform": (BASE + ["checkov", "tflint"], BASE_HOOKS | {CHECKOV, TFLINT}),
    "docker": (BASE + ["checkov", "hadolint"], BASE_HOOKS | {CHECKOV, HADOLINT}),
}

# the checks .checkov.yaml suggests skipping, read from its comments
CHECKOV_YAML = (CATALOG / "checkov" / ".checkov.yaml").read_text(encoding="utf-8")
SUGGESTED_SKIPS = set(re.findall(r"^#\s+- (CKV\w+)", CHECKOV_YAML, re.M))


def findings(out):
    """Finding IDs per tool, from the hooks' verbose output."""
    return {
        CHECKOV: set(re.findall(r"^Check: (CKV2?_\w+):", out, re.M)),
        TFLINT: set(re.findall(r"\((terraform_\w+)\)$", out, re.M)),
        HADOLINT: set(re.findall(r"\b(DL\d{4}|SC\d{4})\b", out)),
    }


def edit(path, old, new):
    text = path.read_text(encoding="utf-8")
    assert old in text, f"{old!r} not in {path.name}"
    path.write_text(text.replace(old, new), encoding="utf-8", newline="\n")


def block_mode(repo):
    """Delete each tool's warn switch, as a team does once it's ready to block."""
    if (repo / ".checkov.yaml").exists():
        edit(repo / ".checkov.yaml", "soft-fail: true\n", "")
    if (repo / ".hadolint.yaml").exists():
        edit(repo / ".hadolint.yaml", "no-fail: true\n", "")
    if "id: tflint" in (repo / ".pre-commit-config.yaml").read_text(encoding="utf-8"):
        edit(repo / ".pre-commit-config.yaml", "        args: [--force]\n", "")


@pytest.mark.parametrize(
    "stack,expected",
    [
        ("terraform", {CHECKOV: {"CKV_AWS_24", "CKV_AWS_53"}, TFLINT: {"terraform_required_providers"}}),
        ("docker", {CHECKOV: {"CKV_DOCKER_1", "CKV_DOCKER_7"}, HADOLINT: {"DL3004", "DL3007"}}),
    ],
)
def test_insecure_fixture_warns_then_blocks(tmp_path, stack, expected):
    tools, hooks = STACKS[stack]
    repo = make_repo(tmp_path, tools, f"{stack}/insecure")

    # warn mode: every hook passes, and the findings are printed
    results, out = run_pre_commit(repo, "--all-files")
    expect(results, out, hooks, set())
    found = findings(out)
    for tool, ids in expected.items():
        assert ids <= found[tool], (tool, found[tool], out)

    # block mode: the same findings now fail
    block_mode(repo)
    results, out = run_pre_commit(repo, "--all-files")
    expect(results, out, hooks, set(expected))


def readme_command(heading, prefix):
    """The one line in a README section that starts with `prefix`, the section ending at the next heading."""
    text = (CATALOG / "checkov" / "README.md").read_text(encoding="utf-8")
    start = re.search(rf"^### {re.escape(heading)}\n", text, re.M)
    assert start, f"no '### {heading}' heading in catalog/checkov/README.md"
    section = re.split(r"^#", text[start.end():], maxsplit=1, flags=re.M)[0]
    lines = [line.strip() for line in section.splitlines() if line.strip().startswith(prefix)]
    assert len(lines) == 1, f"want one line starting {prefix!r} under '### {heading}', got {lines}"
    return lines[0]


def copy_fixture(repo, fixture, into=""):
    for f in sorted(p for p in (FIXTURES / fixture).rglob("*") if p.is_file()):
        write(repo, into + f.relative_to(FIXTURES / fixture).as_posix(), f.read_text(encoding="utf-8"))


BASELINE = "Checkov (write .checkov.baseline)"


@pytest.mark.parametrize(
    # into: the folder the backlog goes in. old: one of its findings, and the address the
    # baseline records it under. new: a finding in the new-finding fixture that old lacks.
    "stack,into,old,address,new",
    [
        ("terraform", "", "CKV_AWS_24", "aws_security_group.ssh_open", "CKV_AWS_25"),
        # a Dockerfile's address is its path, written with the OS's separator
        ("docker", "app/", "CKV_DOCKER_4", f"/app{os.sep}Dockerfile.ADD", "CKV_DOCKER_3"),
    ],
    ids=["terraform", "docker"],
)
def test_checkov_baseline_blocks_only_new_findings(tmp_path, stack, into, old, address, new):
    repo = make_repo(tmp_path, ["checkov"])
    copy_fixture(repo, f"{stack}/insecure", into)
    commit(repo)

    # step 1 of the README, run as written
    command = readme_command("Baseline the backlog", "pre-commit run ")
    args = shlex.split(command)[2:]
    results, out = run_pre_commit(repo, *args)
    expect(results, out, {BASELINE}, set())
    baseline = json.loads((repo / ".checkov.baseline").read_text(encoding="utf-8"))
    recorded = {r["resource"]: r["check_ids"] for f in baseline["failed_checks"] for r in f["findings"]}
    assert old in recorded.get(address, ()), recorded

    # step 3: uncomment the baseline lines, delete soft-fail and commit. The old findings pass.
    edit(repo / ".checkov.yaml", "# baseline:", "baseline:")
    edit(repo / ".checkov.yaml", "# output-baseline-as-skipped:", "output-baseline-as-skipped:")
    block_mode(repo)
    commit(repo)
    results, out = run_pre_commit(repo, "--all-files")
    expect(results, out, {CHECKOV}, set())
    assert not findings(out)[CHECKOV], out
    assert re.search(r"Failed checks: 0, Skipped checks: [1-9]", out), out

    # regenerating in block mode passes, and leaves the committed baseline as it was
    expect(*run_pre_commit(repo, *args), {BASELINE}, set())
    assert not git(repo, "status", "--porcelain").stdout, git(repo, "diff").stdout

    # a commit that adds a new finding is blocked, and only the new finding is reported
    copy_fixture(repo, f"{stack}/new-finding")
    git(repo, "add", "-A")
    results, out = run_pre_commit(repo)
    expect(results, out, {CHECKOV}, {CHECKOV})
    assert new in findings(out)[CHECKOV] and old not in out, out


@pytest.mark.parametrize("stack", ["terraform", "docker"])
def test_secure_fixture_is_clean_once_suggested_skips_apply(tmp_path, stack):
    tools, hooks = STACKS[stack]
    repo = make_repo(tmp_path, tools, f"{stack}/secure")

    # as shipped: only the checks .checkov.yaml suggests skipping show up
    results, out = run_pre_commit(repo, "--all-files")
    expect(results, out, hooks, set())
    found = findings(out)
    assert found[CHECKOV] <= SUGGESTED_SKIPS, (found[CHECKOV] - SUGGESTED_SKIPS, out)
    assert not found[TFLINT] and not found[HADOLINT], out

    # uncomment the suggestions and block: nothing left to report
    edit(repo / ".checkov.yaml", "# skip-check:", "skip-check:")
    for check in SUGGESTED_SKIPS:
        edit(repo / ".checkov.yaml", f"#   - {check} ", f"  - {check} ")
    block_mode(repo)
    results, out = run_pre_commit(repo, "--all-files")
    expect(results, out, hooks, set())
    assert not any(findings(out).values()), out
