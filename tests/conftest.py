"""Helpers: assemble a .pre-commit-config.yaml from catalog/ and run real pre-commit on fixtures."""

import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "catalog"
FIXTURES = ROOT / "tests" / "fixtures"
NOT_CONFIG = {"snippet.yaml", "README.md"}


def assemble(tools):
    """The hand-copy path: `repos:` followed by each tool's snippet, in order."""
    return b"repos:\n" + b"".join((CATALOG / t / "snippet.yaml").read_bytes() for t in tools)


def git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def make_repo(tmp_path, fixture, tools):
    """A git repo holding the fixture's files, the assembled config and each tool's config files, all staged."""
    repo = tmp_path / "repo"
    shutil.copytree(FIXTURES / fixture, repo)
    git(repo, "init", "-q")
    git(repo, "config", "user.email", "test@example.invalid")
    git(repo, "config", "user.name", "hookshelf test")
    git(repo, "config", "commit.gpgsign", "false")
    (repo / ".pre-commit-config.yaml").write_bytes(assemble(tools))
    for tool in tools:
        for f in (CATALOG / tool).iterdir():
            if f.is_file() and f.name not in NOT_CONFIG:
                shutil.copy(f, repo / f.name)
    git(repo, "add", "-A")
    return repo


def commit(repo, message="commit"):
    git(repo, "commit", "-q", "--no-verify", "-m", message)


def run_pre_commit(repo, *args):
    """Run pre-commit; return (names of failed hooks, output). Exit code must agree with the failures."""
    proc = subprocess.run(
        [sys.executable, "-m", "pre_commit", "run", "--color", "never", *args],
        cwd=repo, capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    out = proc.stdout + proc.stderr
    failed = set(re.findall(r"^(.+?)\.{3,}Failed$", proc.stdout, re.M))
    assert (proc.returncode != 0) == bool(failed), out
    return failed, out
