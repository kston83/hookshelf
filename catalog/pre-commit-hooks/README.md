# pre-commit-hooks

**Recommended for every repo. Blocks the commit.**

## What it catches

- `detect-private-key`: a file containing a private key header
  (`BEGIN RSA PRIVATE KEY`, `BEGIN OPENSSH PRIVATE KEY` ...).
- `check-merge-conflict`: leftover conflict markers (`<<<<<<<`) while a merge or rebase is in
  progress.

## What installs locally

A small Python package in pre-commit's cache. It takes a few seconds on first run.

## Tuning

Exclude a path that legitimately holds a key-like test file:

```yaml
      - id: detect-private-key
        exclude: ^tests/keys/
```

Provider docs: <https://github.com/pre-commit/pre-commit-hooks>
