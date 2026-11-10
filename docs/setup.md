# Set up hookshelf by hand

This walks you through adding hookshelf's hooks to one of your repos. At the end your
repo has a `.pre-commit-config.yaml` and a config file or two, and nothing in it depends
on hookshelf.

## Before you start

[pre-commit](https://pre-commit.com/) is a tool that runs checks ("hooks") when you
`git commit`. You list the hooks in `.pre-commit-config.yaml`, and pre-commit downloads and
installs each one the first time it runs, into its own cache. If a blocking hook finds
something, the commit doesn't happen.

You need git, and pre-commit itself, which needs Python 3.11 or later (as of pre-commit
4.7.0). Install it with one of these:

```sh
uv tool install pre-commit     # any OS, with uv: https://docs.astral.sh/uv/
pipx install pre-commit        # any OS, with pipx: https://pipx.pypa.io/
brew install pre-commit        # macOS or Linux, with Homebrew
```

If your shell can't find `pre-commit` afterwards, run `uv tool update-shell` or
`pipx ensurepath`, then open a new terminal. Check it works:

```sh
pre-commit --version
```

Then get a copy of hookshelf to copy from. Clone it next to your repo, so that from inside
your repo it's at `../hookshelf`:

```sh
git clone https://github.com/kston83/hookshelf
```

Or download the ZIP from GitHub, unzip it next to your repo and rename the
`hookshelf-main` folder to `hookshelf`. You only need it during setup.

## 1. Pick your tools

[`catalog/stacks.yaml`](../catalog/stacks.yaml) lists the tools for each stack. Every repo
gets `base`. Add `terraform` if the repo has Terraform, and `docker` if it has
Dockerfiles. Take the recommended tools unless you have a reason not to; the optional ones
add more checks and more first-run install time.

| Stack | Recommended | Optional |
|---|---|---|
| base | gitleaks, pre-commit-hooks | |
| terraform | checkov | tflint |
| docker | checkov | hadolint |

checkov covers both Terraform and Docker, so list it once. This guide uses base plus
terraform: gitleaks, pre-commit-hooks and checkov.

## 2. Build `.pre-commit-config.yaml`

The file is a `repos:` line, then each tool's `catalog/<tool>/snippet.yaml`, with a blank
line between snippets. Each snippet already has a comment saying what it catches and
whether it blocks or warns.

You can paste it together in an editor, or run this from your repo's root. Change the tool
names to the ones you picked. In bash (Git Bash on Windows, or any macOS or Linux shell):

```sh
{
  echo "repos:"
  cat ../hookshelf/catalog/gitleaks/snippet.yaml
  echo
  cat ../hookshelf/catalog/pre-commit-hooks/snippet.yaml
  echo
  cat ../hookshelf/catalog/checkov/snippet.yaml
} > .pre-commit-config.yaml
```

In Windows PowerShell:

```powershell
$catalog = Resolve-Path ..\hookshelf\catalog
$tools = "gitleaks", "pre-commit-hooks", "checkov"
$snippets = $tools | ForEach-Object { [IO.File]::ReadAllText("$catalog\$_\snippet.yaml") }
[IO.File]::WriteAllText("$PWD\.pre-commit-config.yaml", "repos:`n" + ($snippets -join "`n"))
```

Both write UTF-8 without a BOM and with LF line endings. The PowerShell version avoids
`Set-Content` and `Out-File`, which in Windows PowerShell 5.1 add a BOM or CRLF line
endings.

**Already have a `.pre-commit-config.yaml`?** Don't overwrite it. Paste each snippet at the
end of its `repos:` list, with a blank line between snippets. Our snippets indent
`- repo:` by two spaces. If your file starts `- repo:` at the beginning of the line,
re-indent the pasted lines to match: mixed indentation can parse as one repo nested inside
another, and pre-commit then fails with `Missing required key: id`. If your file already
lists a repo we use, such as `pre-commit/pre-commit-hooks`, add our hook ids to that entry
instead of listing the repo twice.

## 3. Copy the config files

Some tools read a config file from the repo root. Copy the ones for your tools:

| Tool | Config file |
|---|---|
| gitleaks | `catalog/gitleaks/.gitleaks.toml` |
| checkov | `catalog/checkov/.checkov.yaml` |
| hadolint | `catalog/hadolint/.hadolint.yaml` |

pre-commit-hooks and tflint need none. For this guide's tools:

```sh
cp ../hookshelf/catalog/gitleaks/.gitleaks.toml .
cp ../hookshelf/catalog/checkov/.checkov.yaml .
```

In PowerShell:

```powershell
Copy-Item ..\hookshelf\catalog\gitleaks\.gitleaks.toml .
Copy-Item ..\hookshelf\catalog\checkov\.checkov.yaml .
```

## 4. Install the git hook

```sh
pre-commit install
```

This writes `.git/hooks/pre-commit`, which makes git run pre-commit on every commit. It
prints `pre-commit installed at .git/hooks/pre-commit` (with backslashes on Windows).
Files under `.git/` aren't committed, so every developer runs `pre-commit install` once in
each clone.

## 5. Run every hook once

Stage the new files first. `pre-commit run --all-files` only checks files git tracks, so
anything untracked is skipped.

```sh
git add .pre-commit-config.yaml .gitleaks.toml .checkov.yaml
pre-commit run --all-files
```

The first run installs each tool into pre-commit's cache (`~/.cache/pre-commit`, or
`%USERPROFILE%\.cache\pre-commit` on Windows). You'll see lines like:

```text
[INFO] Initializing environment for https://github.com/pre-commit/pre-commit-hooks.
[INFO] Installing environment for https://github.com/pre-commit/pre-commit-hooks.
[INFO] Once installed this environment will be reused.
[INFO] This may take a few minutes...
```

How long that takes and how much disk it uses depends on the tool and the machine. Each
tool's README has measured numbers:
[gitleaks](../catalog/gitleaks/README.md#what-installs-locally),
[pre-commit-hooks](../catalog/pre-commit-hooks/README.md#what-installs-locally),
[checkov](../catalog/checkov/README.md#what-installs-locally),
[tflint](../catalog/tflint/README.md#what-installs-locally),
[hadolint](../catalog/hadolint/README.md#what-installs-locally). Later runs take seconds.

Warn-mode tools (checkov, tflint, hadolint) report `Passed` and print their findings below.
On a repo with existing Terraform, expect a list like this:

```text
Checkov..................................................................Passed
- hook id: checkov
- duration: 12.02s

terraform scan results:

Passed checks: 9, Failed checks: 13, Skipped checks: 0

Check: CKV_AWS_24: "Ensure no security groups allow ingress from 0.0.0.0:0 to port 22"
	FAILED for resource: aws_security_group.ssh_open
	File: \main.tf:9-20
```

That's the backlog you'll work through, or baseline and track, before switching the tool
to block (see [Move from warn to block](#move-from-warn-to-block)). If gitleaks or
pre-commit-hooks fails, fix that before you commit: those findings block.

## 6. Commit

```sh
git commit -m "Add pre-commit security hooks"
```

The hooks run on this commit too. From now on the team owns these files. Tell everyone to
run `pre-commit install` after they pull.

## Day to day

On `git commit`, pre-commit runs each hook on the staged files it cares about. A hook with
nothing to check shows `(no files to check)Skipped`. If a blocking hook fails, the commit
doesn't happen: fix the file, `git add` it, and commit again. Each tool's README shows its
real output and what to do: [gitleaks](../catalog/gitleaks/README.md#when-it-fires),
[pre-commit-hooks](../catalog/pre-commit-hooks/README.md#when-it-fires),
[checkov](../catalog/checkov/README.md#when-it-fires),
[tflint](../catalog/tflint/README.md#when-it-fires),
[hadolint](../catalog/hadolint/README.md#when-it-fires).

The `gitleaks` hook only scans staged changes, so it won't find a secret that was committed
before you set this up. To scan the whole history, run
`pre-commit run --all-files --hook-stage manual` on a full (not shallow) checkout. See
[gitleaks](../catalog/gitleaks/README.md).

## Skip one hook, once

Set `SKIP` to the hook's id. The id is in the `- hook id:` line of the output.

```sh
SKIP=checkov git commit -m "..."
```

In PowerShell:

```powershell
$env:SKIP = "checkov"; git commit -m "..."; Remove-Item Env:SKIP
```

The other hooks still run. Don't use `git commit --no-verify` instead: it skips every hook,
including gitleaks, and a secret that reaches a shared branch has to be rotated, not just
deleted.

## Move from warn to block

checkov, tflint and hadolint start in warn mode so a team's existing backlog doesn't stop
every commit. Once a tool's findings are cleaned up or suppressed, switch it to block, one
tool at a time: [checkov](../catalog/checkov/README.md#warn-then-block),
[tflint](../catalog/tflint/README.md#warn-then-block),
[hadolint](../catalog/hadolint/README.md#warn-then-block).

checkov scans the whole repo, so once it blocks, a finding in any file stops the commit.
If its backlog is too big to clear first, record it in a baseline: commits are then only
blocked by new findings. The baselined findings aren't accepted, just tracked somewhere
else. Put them in your issue tracker with an owner, and work them down. See
[Baseline the backlog](../catalog/checkov/README.md#baseline-the-backlog).

## Keep versions current

```sh
pre-commit autoupdate
git diff .pre-commit-config.yaml
```

`autoupdate` moves each `rev` to the newest tag on the provider's default branch. That
isn't always the newest release, so read the diff before you commit it. For example, on
9 November 2026 it moved gitleaks from `v8.30.1` back to `v8.30.0`. Revert any line that
goes backwards. It doesn't touch `repo: local` hooks, so bump tflint's version in
`additional_dependencies` by hand. Then run `pre-commit run --all-files` again.

## Windows and network notes

- **Go-based hooks.** gitleaks and tflint are built with Go. pre-commit downloads Go
  itself if it isn't installed, on any OS. Networks that block `proxy.golang.org` or
  `go.dev` stop that install.
- **Long paths.** checkov's install fails with `Filename too long` if `PRE_COMMIT_HOME`
  points to a deep folder. Fix it with `git config --global core.longpaths true`. See
  [checkov](../catalog/checkov/README.md#what-installs-locally).
