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

Measured on a Windows laptop without Go: the first run took about 2–3 minutes and used about
320 MB of disk (the Go toolchain plus the gitleaks build). Later runs take seconds.

Networks that block `proxy.golang.org` or `go.dev` stop this install.

## Tuning

- A false positive on one line: add `# gitleaks:allow` at the end of that line.
- A file or path that should never be scanned: add an `[allowlist]` to `.gitleaks.toml`.
- Your own patterns: add `[[rules]]` at the bottom of `.gitleaks.toml`.

Provider docs: <https://github.com/gitleaks/gitleaks>
