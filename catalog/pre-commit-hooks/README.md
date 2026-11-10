# pre-commit-hooks

**Recommended for every repo. Blocks the commit.**

## What it catches

- `detect-private-key`: a file containing a private key header (RSA, EC, DSA, OpenSSH,
  PGP and others).
- `check-merge-conflict`: leftover conflict markers (`<<<<<<<`) while a merge or rebase is in
  progress.

## What installs locally

A small Python package in pre-commit's cache: 12–17 MB. The first run takes a few seconds
on GitHub's runners and about a minute on an older Windows laptop (2017 i5, Defender on).

## Tuning

To also check for conflict markers outside a merge, add `args: [--assume-in-merge]` to
`check-merge-conflict`.

Exclude a path that legitimately holds a key-like test file:

```yaml
      - id: detect-private-key
        exclude: ^tests/keys/
```

Provider docs: <https://github.com/pre-commit/pre-commit-hooks>
