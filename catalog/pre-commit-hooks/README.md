# pre-commit-hooks

**Recommended for every repo. Blocks the commit.**

pre-commit-hooks is pre-commit's own set of small checks. hookshelf uses two of them: one
stops private keys getting into git, the other stops a half-resolved merge from being
committed.

## What it catches

- `detect-private-key`: a file containing a private key header (RSA, EC, DSA, OpenSSH,
  PGP and others).
- `check-merge-conflict`: leftover conflict markers (`<<<<<<<`) while a merge or rebase is in
  progress.

Both block from the first day. There's no warn mode, because neither is ever right to
commit.

## Set up

You need pre-commit and a `.pre-commit-config.yaml` first. See
[the setup guide](../../docs/setup.md).

1. Paste `snippet.yaml` under `repos:` in `.pre-commit-config.yaml`. If other snippets are
   already there, leave a blank line between them. There's no config file to copy.
2. Run the key check once on every file in the repo:

   ```sh
   pre-commit run detect-private-key --all-files
   ```

   This installs both hooks (see [What installs locally](#what-installs-locally)) and lists
   any private key that's already committed. `check-merge-conflict` only looks during a
   merge, so there's nothing to run it on yet.

## When it fires

### detect-private-key

```text
detect private key.......................................................Failed
- hook id: detect-private-key
- exit code: 1

Private key found: deploy_key
```

gitleaks, if you use it, fails on the same file too, with `RuleID: private-key`.

1. Take the key out of the repo, keep the file on disk, and stop it being staged again:

   ```sh
   git rm --cached deploy_key
   echo deploy_key >> .gitignore
   git add .gitignore
   ```

   Keep the key in your secret store instead (Jenkins credentials, GitHub Actions
   secrets, a vault).
2. If the key was ever committed or pushed, treat it as leaked. Make a new key pair and
   remove the old public key everywhere it's trusted. Rewriting git history doesn't
   un-leak it.

If the file is a test key that's meant to be in the repo, exclude its path. See
[Tuning](#tuning).

### check-merge-conflict

```text
check for merge conflicts................................................Failed
- hook id: check-merge-conflict
- exit code: 1

notes.txt:1: Merge conflict string '<<<<<<<' found
notes.txt:3: Merge conflict string '=======' found
notes.txt:5: Merge conflict string '>>>>>>>' found
```

You staged a file that still has conflict markers in it.

1. Open each file listed. Keep the lines you want, and delete the `<<<<<<<`, `=======` and
   `>>>>>>>` lines.
2. Stage the file again with `git add`, then commit.

During a rebase, `git rebase --continue` commits without running pre-commit hooks
(checked with git 2.43), so this check only catches markers if you run `git commit` or
`pre-commit run` before you continue.

## What installs locally

A small Python package in pre-commit's cache: 12–17 MB. The first run takes a few seconds
on GitHub's runners and about a minute on an older Windows laptop (2017 i5, Defender on).

## Tuning

To also check for conflict markers outside a merge, add `args: [--assume-in-merge]` to
`check-merge-conflict`. Then a line that's exactly `=======` fails too, such as a
reStructuredText underline seven characters long.

```yaml
      - id: check-merge-conflict
        args: [--assume-in-merge]
```

Exclude a path that legitimately holds a key-like test file:

```yaml
      - id: detect-private-key
        exclude: ^tests/keys/
```

gitleaks finds the same keys, so if you use it, also add an `[[allowlists]]` table for the
path to `.gitleaks.toml`. See
[gitleaks tuning](../gitleaks/README.md#tuning).

Provider docs: <https://github.com/pre-commit/pre-commit-hooks>
