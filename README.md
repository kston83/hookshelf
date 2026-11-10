# hookshelf

Curated, pinned pre-commit security hooks that you copy into your repo and own.

It's for teams that want secrets, Terraform and Dockerfiles checked on every commit
without building the setup themselves. You copy a few plain files from here, and your repo
never depends on this one again.

## What you get

Every repo gets the base stack. Add terraform or docker if the repo has them. Recommended
tools are the default; optional ones add more checks.

| Tool | Stack | Catches | On a finding |
|---|---|---|---|
| [gitleaks](catalog/gitleaks/README.md) | base, recommended | Hardcoded secrets | Blocks |
| [pre-commit-hooks](catalog/pre-commit-hooks/README.md) | base, recommended | Private keys, leftover merge conflict markers | Blocks |
| [checkov](catalog/checkov/README.md) | terraform and docker, recommended | Terraform and Dockerfile misconfigurations | Warns |
| [tflint](catalog/tflint/README.md) | terraform, optional | Terraform mistakes and deprecated syntax | Warns |
| [hadolint](catalog/hadolint/README.md) | docker, optional | Dockerfile best practices, shell mistakes in `RUN` | Warns |

The stacks live in [`catalog/stacks.yaml`](catalog/stacks.yaml).

## Quick start

[docs/setup.md](docs/setup.md) walks through each step, with commands for bash and
PowerShell.

1. Install [pre-commit](https://pre-commit.com/) (it needs Python 3.11 or later), for
   example with `uv tool install pre-commit` or `pipx install pre-commit`.
2. Clone this repo next to yours: `git clone https://github.com/kston83/hookshelf`.
3. In your repo, create `.pre-commit-config.yaml`: a `repos:` line, then each tool's
   `catalog/<tool>/snippet.yaml`, with a blank line between snippets.
4. Copy each tool's config file to your repo root: `.gitleaks.toml`, plus `.checkov.yaml`
   or `.hadolint.yaml` if you use those tools.
5. Run `pre-commit install`, `git add` the new files, then `pre-commit run --all-files`.
   The first run installs each tool. Commit when it's done.

## How it works

- **You own plain files.** After setup your repo has `.pre-commit-config.yaml` and a
  config file per tool. If this repo disappeared, yours would keep working.
- **Hooks come from the providers.** Every hook comes from the tool provider's own repo at
  a pinned version. tflint ships no pre-commit hook, so its snippet is a short
  `repo: local` hook that has pre-commit build the pinned tflint release.
- **Secrets block, everything else warns.** gitleaks and pre-commit-hooks stop the commit.
  checkov, tflint and hadolint print findings but let the commit through, until you switch
  each one to block.
- **Free and open source.** No accounts or API keys.

## How long does the first install take on my machine?

Each tool's README gives a range measured on GitHub's runners and an older Windows laptop.
To measure a DevOps laptop or a Jenkins agent, install [uv](https://docs.astral.sh/uv/)
and run:

```sh
git clone https://github.com/kston83/hookshelf
cd hookshelf
uv run scripts/measure_install.py
```

It installs each tool into its own temporary pre-commit cache, deletes the cache
afterwards, and prints a table to paste back. The table also shows whether the machine can
reach GitHub, PyPI and the Go proxy. Add `--without-go` to see what a machine without Go
gets.

## Working on this repo

[docs/design.md](docs/design.md) sets the goal, principles and non-goals. This repo uses
[uv](https://docs.astral.sh/uv/) and Python 3.14 (uv installs it for you):

```sh
uv sync
uv run pytest
```

The fixture tests run real pre-commit. The gitleaks rule tests also need a `gitleaks`
binary on PATH; without one they skip locally, while CI installs the pinned version.

## License

Apache-2.0
