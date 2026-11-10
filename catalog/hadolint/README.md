# hadolint

**Optional for Docker. Warns (doesn't block) until you switch it.**

## What it catches

Dockerfile best practices (unpinned base images and packages, `sudo`, `latest` tags,
relative `WORKDIR`), plus ShellCheck findings inside `RUN` instructions.

## What installs locally

The hook comes from `AleksaC/hadolint-py`, which packages the hadolint binary as a Python
wheel, so you need neither Docker nor a system install.
| Machine | First run | Disk |
|---|---|---|
| GitHub runners (Linux, macOS, Windows) | under 15 s | 120–210 MB |
| Older Windows laptop (2017 i5, Defender on) | under 1 min | about 180 MB |

The disk is the hadolint binary plus a Python environment. Later runs take well under a
second. To measure your own machine, run `uv run scripts/measure_install.py hadolint`
from a clone of hookshelf.

## Files

- `snippet.yaml`: paste under `repos:` in `.pre-commit-config.yaml`.
- `.hadolint.yaml`: copy to the repo root, where hadolint finds it automatically.

## Warn, then block

`no-fail: true` in `.hadolint.yaml` prints findings, but the commit goes through. Delete
that line to block on findings at or above `failure-threshold` (`error` as shipped). Lower
it to `warning` to block on more.

## Tuning

- **A rule that doesn't apply:** add it to `ignored:` with a reason.
- **One line:** put `# hadolint ignore=DL3008` on the line above the instruction.
- **Approved registries only:** uncomment `trustedRegistries:`.

Provider docs: <https://github.com/hadolint/hadolint>
