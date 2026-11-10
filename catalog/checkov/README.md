# checkov

**Recommended for Terraform and Docker. Warns (doesn't block) until you switch it.**

## What it catches

Misconfigurations in Terraform and Dockerfiles, for example:

- Terraform: security groups open to `0.0.0.0/0`, public S3 buckets, unencrypted storage,
  missing logging (AWS, Azure and GCP checks).
- Dockerfiles: `latest` base image tags, running as root, `ADD` from a URL, SSH exposed.

## What installs locally

The hook is `language: python`. On first run pre-commit installs checkov and its
dependencies, about 100 Python packages, into its cache.
| Machine | First run | Disk |
|---|---|---|
| GitHub runners (Linux, macOS, Windows) | 0.6–1.2 min | 290–335 MB |
| Older Windows laptop (2017 i5, Defender on) | about 6 min | about 360 MB |

Later runs take a few seconds. To measure your own machine, run
`uv run scripts/measure_install.py checkov` from a clone of hookshelf.

On Windows, pre-commit clones checkov's whole repo, which has paths up to 173 characters
long. With pre-commit's default cache (`%USERPROFILE%\.cache\pre-commit`) that fits within
Windows' 260-character limit. If you set `PRE_COMMIT_HOME` to a deep folder, the install
fails with `Filename too long`. Fix it with `git config --global core.longpaths true`.

checkov doesn't read OpenTofu's `.tofu` files (checked with 3.4.3).

## Files

- `snippet.yaml`: paste under `repos:` in `.pre-commit-config.yaml`. It overrides the
  provider hook's `files:`, which only covers `.tf`, so that tfvars, Terraform JSON and
  Dockerfiles trigger a scan too.
- `.checkov.yaml`: copy to the repo root, where checkov finds it automatically.

## Warn, then block

`soft-fail: true` in `.checkov.yaml` prints findings, but the commit goes through.
Delete that line once the findings are cleaned up, and checkov blocks commits that add new
ones.

## Tuning

- **A check that doesn't apply to your team:** `.checkov.yaml` has commented-out
  suggestions under `skip-check:`. Uncomment them, or add your own, with a reason.
- **One resource only:** put `# checkov:skip=CKV_AWS_24: reason` inside the Terraform
  resource block, or as a comment in the Dockerfile.
- **More frameworks** (Kubernetes, Helm ...): add them to `framework:`.

Provider docs: <https://www.checkov.io/>
