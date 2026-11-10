# gitleaks

**Recommended for every repo. Blocks the commit.**

## What it catches

Hardcoded secrets: cloud keys, tokens, passwords, private keys and ~200 other patterns
from the default gitleaks ruleset. `.gitleaks.toml` keeps the defaults and adds an optional
section for secrets pasted into AI coding agent / MCP server configs.

## Two hooks

| Hook | When | What it scans |
|---|---|---|
| `gitleaks` | every commit | staged changes only |
| `gitleaks-history` | CI (`--hook-stage manual`) | every commit in the history |

`pre-commit run --all-files` does **not** find secrets that were already committed,
because the `gitleaks` hook only looks at staged changes. That is why CI runs:

```sh
pre-commit run --all-files --hook-stage manual
```

with a full (not shallow) checkout.

## What installs locally

The hook is `language: golang`. On first run pre-commit builds gitleaks with Go, and
downloads Go first if it isn't installed. Everything lives in pre-commit's cache
(`~/.cache/pre-commit`, or `%USERPROFILE%\.cache\pre-commit` on Windows).

| Machine | First run | Disk |
|---|---|---|
| GitHub runners (Linux, Windows), Go installed | 0.5–1.2 min | about 40 MB |
| GitHub runners (macOS, Windows), pre-commit downloads Go | under 1 min | about 275 MB |
| Older Windows laptop (2017 i5, Defender on), no Go | 2–3 min | about 320 MB |

Later runs take seconds. To measure your own machine, run
`uv run scripts/measure_install.py gitleaks` from a clone of hookshelf.

Networks that block `proxy.golang.org` or `go.dev` stop this install.

## Tuning

- A false positive on one line: add `# gitleaks:allow` at the end of that line.
- A file or path that should never be scanned: add an `[allowlist]` to `.gitleaks.toml`.
- Your own patterns: add `[[rules]]` at the bottom of `.gitleaks.toml`.

Provider docs: <https://github.com/gitleaks/gitleaks>
