"""Helpers: assemble a .pre-commit-config.yaml from catalog/ and run real pre-commit on fixtures.

Fixtures hold <FAKE_...> markers instead of secrets. The markers are filled in when a fixture
is copied into a throwaway repo, so nothing secret-looking is ever committed to this repo.
"""

import random
import re
import string
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "catalog"
FIXTURES = ROOT / "tests" / "fixtures"
NOT_CONFIG = {"snippet.yaml", "README.md"}


def _fake_secrets():
    rng = random.Random(20261109)
    alnum = string.ascii_letters + string.digits

    def word(n, chars=alnum):
        return "".join(rng.choice(chars) for _ in range(n))

    key = "PRIVATE" + " KEY-----"  # split so this file never looks like a key itself
    body = "\n".join(word(64, alnum + "+/") for _ in range(6))
    return {
        "<FAKE_GITHUB_PAT>": "ghp_" + word(36),
        "<FAKE_MCP_TOKEN>": word(32),
        "<FAKE_PRIVATE_KEY>": f"-----BEGIN RSA {key}\n{body}\n-----END RSA {key}",
    }


SECRETS = _fake_secrets()


def assemble(tools):
    """The hand-copy path: `repos:`, then each tool's snippet, separated by a blank line."""
    return b"repos:\n" + b"\n".join((CATALOG / t / "snippet.yaml").read_bytes() for t in tools)


def git(repo, *args, check=True):
    return subprocess.run(["git", "-C", str(repo), *args], check=check, capture_output=True, text=True)


def write(repo, rel, text):
    f = repo / rel
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_bytes(text.encode("utf-8"))


def make_repo(tmp_path, tools, fixture=None):
    """A git repo with the assembled config, each tool's config files and the fixture, all staged."""
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    for key, value in [("user.email", "test@example.invalid"), ("user.name", "hookshelf test"),
                       ("commit.gpgsign", "false"), ("core.autocrlf", "false")]:
        git(repo, "config", key, value)
    (repo / ".pre-commit-config.yaml").write_bytes(assemble(tools))
    for tool in tools:
        for f in (CATALOG / tool).iterdir():
            if f.is_file() and f.name not in NOT_CONFIG:
                (repo / f.name).write_bytes(f.read_bytes())
    if fixture:
        src = FIXTURES / fixture
        for f in sorted(p for p in src.rglob("*") if p.is_file()):
            text = f.read_text(encoding="utf-8")
            for marker, value in SECRETS.items():
                text = text.replace(marker, value)
            write(repo, f.relative_to(src).as_posix(), text)
    git(repo, "add", "-A")
    return repo


def commit(repo, message="commit"):
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "--no-verify", "-m", message)


STATUS = re.compile(r"^(.+?)\.{3,}(?:\([^)]*\))?(Passed|Failed|Skipped)$", re.M)


def run_pre_commit(repo, *args):
    """Run pre-commit; return ({hook name: Passed/Failed/Skipped}, output)."""
    proc = subprocess.run(
        [sys.executable, "-m", "pre_commit", "run", "--color", "never", *args],
        cwd=repo, capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    out = proc.stdout + proc.stderr
    results = dict(STATUS.findall(proc.stdout))
    assert (proc.returncode != 0) == ("Failed" in results.values()), out
    return results, out


def expect(results, out, hooks, failing):
    """Every hook in `hooks` ran and reported a verdict: Failed if in `failing`, else Passed.

    A hook that was skipped or never ran (a typo in its id, a stage it doesn't belong to)
    can't pass for the expected result.
    """
    assert results == {h: "Failed" if h in failing else "Passed" for h in hooks}, out
