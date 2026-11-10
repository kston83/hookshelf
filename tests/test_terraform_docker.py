"""Terraform and Docker (checkov, tflint, hadolint): real pre-commit runs on tests/fixtures/.

Everything here starts in warn mode: findings print, but the commit goes through. Each
tool's warn switch is one line (soft-fail, --force, no-fail); deleting it makes the
same findings block.
"""

import os
import re
import shlex
import subprocess

import pytest

from conftest import CATALOG, FIXTURES, commit, expect, make_repo, run_pre_commit, write

BASE = ["gitleaks", "pre-commit-hooks"]
BASE_HOOKS = {"Detect hardcoded secrets", "detect private key", "check for merge conflicts"}
CHECKOV, TFLINT, HADOLINT = "Checkov", "tflint", "Hadolint"

STACKS = {
    "terraform": (BASE + ["checkov", "tflint"], BASE_HOOKS | {CHECKOV, TFLINT}),
    "docker": (BASE + ["checkov", "hadolint"], BASE_HOOKS | {CHECKOV, HADOLINT}),
}

# the checks .checkov.yaml suggests skipping, read from its comments
SUGGESTED_SKIPS = set(re.findall(r"^#\s+- (CKV\w+)", (CATALOG / "checkov" / ".checkov.yaml").read_text(), re.M))


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
    if "id: tflint" in (repo / ".pre-commit-config.yaml").read_text():
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
    """The first line in a README section's code blocks that starts with `prefix`."""
    text = (CATALOG / "checkov" / "README.md").read_text(encoding="utf-8")
    section = text.split(f"### {heading}\n", 1)[1]
    return next(line.strip() for line in section.splitlines() if line.strip().startswith(prefix))


def test_checkov_baseline_blocks_only_new_findings(tmp_path):
    repo = make_repo(tmp_path, ["checkov"], "terraform/insecure")
    commit(repo)

    # step 1 of the README, run as written (uv runs pytest, and sets UV to its own path)
    command = readme_command("Baseline the backlog", "uvx ")
    rev = re.search(r"rev: (\S+)", (CATALOG / "checkov" / "snippet.yaml").read_text()).group(1)
    assert f"checkov=={rev} " in command, (rev, command)
    uv = os.environ.get("UV", "uv")
    proc = subprocess.run([uv, "tool", "run", *shlex.split(command)[1:]], cwd=repo,
                          capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "CKV_AWS_24" in (repo / ".checkov.baseline").read_text()

    # step 3: uncomment the baseline lines and delete soft-fail. The old findings pass.
    edit(repo / ".checkov.yaml", "# baseline:", "baseline:")
    edit(repo / ".checkov.yaml", "# output-baseline-as-skipped:", "output-baseline-as-skipped:")
    block_mode(repo)
    results, out = run_pre_commit(repo, "--all-files")
    expect(results, out, {CHECKOV}, set())
    assert not findings(out)[CHECKOV], out
    assert re.search(r"Failed checks: 0, Skipped checks: [1-9]", out), out

    # a new finding blocks, and only it is reported
    write(repo, "rdp.tf", (FIXTURES / "terraform" / "new-finding" / "rdp.tf").read_text())
    results, out = run_pre_commit(repo, "--all-files")
    expect(results, out, {CHECKOV}, {CHECKOV})
    assert "CKV_AWS_25" in findings(out)[CHECKOV] and "CKV_AWS_24" not in out, out


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
