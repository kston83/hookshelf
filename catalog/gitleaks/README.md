# gitleaks

**Recommended for every repo. Blocks the commit.**

gitleaks looks for secrets in your code: keys, tokens and passwords that shouldn't be in
git. Once a secret is pushed, anyone who can read the repo can use it, so it's much cheaper
to stop it at the commit.

## What it catches

Hardcoded secrets: cloud keys, tokens, passwords, private keys and ~200 other patterns
from the default gitleaks ruleset. `.gitleaks.toml` keeps the defaults and adds an optional
section for secrets pasted into AI coding agent / MCP server configs.

That optional section has two rules. They only look at agent and MCP config files
(`.mcp.json`, `mcp.json`, `mcp_config.json`, `claude_desktop_config.json`,
`.claude/settings.json`, `.claude/settings.local.json`, `.cursor/mcp.json`,
`.vscode/mcp.json` and `.gemini/settings.json`):

- `mcp-config-secret`: a key named like a secret (`API_KEY`, `GITHUB_PAT`, `clientSecret`
  ...) with a literal value. Keys such as `PATH` or `TOKEN_FILE`, and values that are file
  paths, don't count.
- `mcp-config-auth-header`: a hardcoded `Authorization` header (`Bearer`, `Basic` or
  `Token`).

gitleaks blocks from the first day. There's no warn mode, because a secret that gets
through can't be taken back.

## Set up

You need pre-commit and a `.pre-commit-config.yaml` first. See
[the setup guide](../../docs/setup.md).

The snippet adds two hooks:

| Hook | When | What it scans |
|---|---|---|
| `gitleaks` | every commit | staged changes only |
| `gitleaks-history` | CI (`--hook-stage manual`) | every commit in the history |

1. Paste `snippet.yaml` under `repos:` in `.pre-commit-config.yaml`. If other snippets are
   already there, leave a blank line between them.
2. Copy `.gitleaks.toml` to the repo root. gitleaks finds it there automatically. If your
   team doesn't use AI coding agents, you can delete the optional MCP section.
3. Run the commit hook once:

   ```sh
   pre-commit run gitleaks --all-files
   ```

   This installs gitleaks, which takes a while the first time (see
   [What installs locally](#what-installs-locally)). It passes even if old commits hold a
   secret, because this hook only looks at staged changes.
4. Scan the whole history once, to find secrets that are already committed:

   ```sh
   pre-commit run gitleaks-history --all-files --hook-stage manual
   ```

   Keep `--all-files`: without it, pre-commit skips the hook when nothing is staged. For
   each finding, see [A secret in an old commit](#a-secret-in-an-old-commit).

After that, `gitleaks` runs on every commit. CI should run the history scan, as
`pre-commit run --all-files --hook-stage manual` on a full (not shallow) checkout, because
`pre-commit run --all-files` alone doesn't find secrets that are already committed.

## When it fires

The hooks run with `--redact`, so gitleaks prints `REDACTED` instead of the secret. The
output is safe to paste into a ticket or a chat.

### A secret in a staged change

```text
Detect hardcoded secrets.................................................Failed
- hook id: gitleaks
- exit code: 1

Finding:     GITHUB_TOKEN=REDACTED
Secret:      REDACTED
RuleID:      github-pat
Entropy:     4.684184
File:        app.env
Line:        2
Fingerprint: app.env:github-pat:2

11:29PM WRN leaks found: 1
```

The commit didn't happen. `File` and `Line` say where the secret is, and `RuleID` says what
kind of secret gitleaks thinks it is.

If the secret was never committed:

1. Take it out of the file. Read it at run time from an environment variable or your
   secret store instead (Jenkins credentials, GitHub Actions secrets, a vault).
2. Stage the file again with `git add`. The hook checks what's staged, so an edit you
   haven't staged still fails.
3. Commit again.

If the secret was ever committed or pushed, on any branch or in any other repo, treat it as
leaked:

1. Revoke or rotate it first, wherever it was issued.
2. Then take it out of the file, as above.

Rewriting git history doesn't un-leak a secret. Clones, forks and CI logs may already have
it, so rotating it is what protects you.

### A secret in an old commit

`gitleaks-history` scans every commit, so it finds a secret even after a later commit
deleted it:

```text
Detect hardcoded secrets (full git history)..............................Failed
- hook id: gitleaks
- exit code: 1

Finding:     GITHUB_TOKEN=REDACTED
Secret:      REDACTED
RuleID:      github-pat
Entropy:     4.684184
File:        app.env
Line:        2
Commit:      49525d6949f5fb83851a8fbd2853f127b7b0cda4
Author:      hookshelf test
Email:       test@example.invalid
Date:        2026-11-10T05:30:08Z
Fingerprint: 49525d6949f5fb83851a8fbd2853f127b7b0cda4:app.env:github-pat:2

11:30PM WRN leaks found: 1
```

Anyone with a clone can still read that commit, so:

1. Treat the secret as leaked. Revoke or rotate it.
2. If it's still in the current code, take it out, as above.
3. Once it's rotated, stop the finding from failing CI: add its `Fingerprint` line to a
   `.gitleaksignore` file at the repo root, and commit it.

   ```text
   49525d6949f5fb83851a8fbd2853f127b7b0cda4:app.env:github-pat:2
   ```

   A history fingerprint includes the commit, so it ignores only that one finding.

### A secret in an AI agent or MCP config

```text
Detect hardcoded secrets.................................................Failed
- hook id: gitleaks
- exit code: 1

Finding:     "MY_SERVICE_PAT": "REDACTED"
Secret:      REDACTED
RuleID:      mcp-config-secret
Entropy:     4.562500
File:        .mcp.json
Line:        7
Fingerprint: .mcp.json:mcp-config-secret:7

11:29PM WRN leaks found: 1
```

`mcp-config-secret` means a token was pasted straight into the config. Put the token in an
environment variable and reference it instead:

```json
"env": {
  "MY_SERVICE_PAT": "${MY_TOKEN}"
}
```

The rules skip any value that starts with `$` or `{`, so `"${MY_TOKEN}"` and
`"${env:MY_TOKEN}"` both pass. Use the syntax your agent expands. For a header, write
`"Authorization": "Bearer ${MY_TOKEN}"`. If the token was ever committed or pushed, rotate
it too.

### A false positive

If gitleaks flags something that isn't a secret, such as a fake value in a test, add
`gitleaks:allow` in a comment at the end of that line, using the file's own comment syntax:

```hcl
test_token = "fake-value-for-unit-tests" # gitleaks:allow
```

gitleaks then skips that line, on commit and in the history scan.

Some files can't hold comments, such as JSON. For those, and for a finding in an old
commit, add the finding's `Fingerprint` line to `.gitleaksignore` at the repo root instead.
A fingerprint from the commit hook (`app.env:github-pat:2`) has no commit in it, so it
matches that rule on that line of that file from then on.

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

- **A false positive on one line:** add `# gitleaks:allow` at the end of that line. See
  [A false positive](#a-false-positive).
- **One finding, or one old commit:** add its fingerprint to `.gitleaksignore`.
- **A file or path that should never be scanned:** add an `[[allowlists]]` table to
  `.gitleaks.toml`. Since gitleaks 8.25.0 this replaces the older `[allowlist]`.

  ```toml
  [[allowlists]]
  description = "test keys"
  paths = ['''^tests/keys/''']
  ```

- **Your own patterns:** add `[[rules]]` at the bottom of `.gitleaks.toml`, under "Your
  organisation's rules below". For example:

  ```toml
  [[rules]]
  id = "acme-internal-token"
  description = "ACME internal token"
  regex = '''acme_[a-z0-9]{24}'''
  keywords = ["acme_"]
  ```

- **No AI coding agents:** delete the optional MCP section from `.gitleaks.toml`.

Provider docs: <https://github.com/gitleaks/gitleaks>
