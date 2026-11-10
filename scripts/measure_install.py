# /// script
# requires-python = ">=3.14"
# dependencies = ["pre-commit==4.7.0"]
# ///
"""Measure each catalog tool's first pre-commit install on this machine.

From a clone of this repo:

    uv run scripts/measure_install.py                # every tool in catalog/
    uv run scripts/measure_install.py checkov tflint # only these
    uv run scripts/measure_install.py --without-go   # hide Go, like a laptop without it

Each tool installs into its own empty pre-commit cache, which is deleted afterwards.
Nothing outside that cache is changed. Paste the table it prints into an issue or chat.
"""

import argparse
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

CATALOG = Path(__file__).resolve().parents[1] / "catalog"
ENDPOINTS = ["https://github.com", "https://pypi.org/simple/", "https://proxy.golang.org", "https://go.dev/dl/"]


def reachable(url):
    try:
        urllib.request.urlopen(urllib.request.Request(url, method="HEAD"), timeout=10)
        return "yes"
    except urllib.error.HTTPError as e:  # the server answered, so the network path is open
        return f"yes (HTTP {e.code})"
    except Exception as e:  # any failure means a pre-commit install from there would fail too
        return f"no ({type(e).__name__})"


def disk_use(path):
    total = 0
    for root, _, files in os.walk(path):
        for f in files:
            try:
                total += os.lstat(os.path.join(root, f)).st_size
            except OSError:
                pass
    return total


def env_without_go():
    go = "go.exe" if os.name == "nt" else "go"
    dirs = os.environ["PATH"].split(os.pathsep)
    go_dirs = [d for d in dirs if (Path(d) / go).is_file()]
    if any(shutil.which("git", path=d) for d in go_dirs):
        sys.exit("--without-go: Go is in the same folder as git (e.g. /usr/bin), so it can't be hidden.")
    path = [d for d in dirs if d not in go_dirs]
    return {**os.environ, "PATH": os.pathsep.join(path), "GOROOT": ""}


def measure(tool, env):
    # A short cache path: on Windows, checkov's install fails with deep paths (260-char limit).
    home = Path.home() / ".cache" / "hookshelf-measure" / tool
    shutil.rmtree(home, ignore_errors=True)
    env = {**env, "PRE_COMMIT_HOME": str(home)}
    pre_commit = [sys.executable, "-m", "pre_commit"]
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as repo:
        subprocess.run(["git", "init", "-q", repo], check=True)
        config = b"repos:\n" + (CATALOG / tool / "snippet.yaml").read_bytes()
        Path(repo, ".pre-commit-config.yaml").write_bytes(config)
        start = time.monotonic()
        proc = subprocess.run([*pre_commit, "install-hooks"], cwd=repo, env=env, capture_output=True, text=True)
        seconds = time.monotonic() - start
    size = disk_use(home)
    if proc.returncode:
        log = home / "pre-commit.log"
        detail = log.read_text(errors="replace") if log.exists() else proc.stdout + proc.stderr
        print(f"\n{tool} failed to install:\n" + "\n".join(detail.splitlines()[:25]), file=sys.stderr)
    subprocess.run([*pre_commit, "clean"], env=env, capture_output=True)  # handles read-only Go files
    shutil.rmtree(home, ignore_errors=True)
    return ("ok" if proc.returncode == 0 else "FAILED"), seconds, size


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("tools", nargs="*", help="tool folders under catalog/ (default: all)")
    parser.add_argument("--without-go", action="store_true", help="hide Go from PATH")
    args = parser.parse_args()
    tools = args.tools or sorted(p.parent.name for p in CATALOG.glob("*/snippet.yaml"))
    env = env_without_go() if args.without_go else dict(os.environ)
    go = shutil.which("go", path=env["PATH"])

    print(f"| Machine | {platform.platform()}, {platform.machine()}, {os.cpu_count()} logical CPUs |")
    print("|---|---|")
    print(f"| CPU | {os.environ.get('PROCESSOR_IDENTIFIER') or platform.processor() or 'unknown'} |")
    print(f"| Python / Go | {platform.python_version()} / {'yes' if go else 'no (pre-commit downloads it)'} |")
    for url in ENDPOINTS:
        print(f"| Reach {url} | {reachable(url)} |")
    print("\n| Tool | Result | First install | Disk |\n|---|---|---|---|", flush=True)
    for tool in tools:
        result, seconds, size = measure(tool, env)
        print(f"| {tool} | {result} | {seconds / 60:.1f} min | {size / 2**20:.0f} MB |", flush=True)
    shutil.rmtree(Path.home() / ".cache" / "hookshelf-measure", ignore_errors=True)


if __name__ == "__main__":
    main()
