# tflint

**Optional for Terraform. Warns (doesn't block) until you switch it.**

## What it catches

Terraform mistakes that `terraform validate` lets through: missing version constraints
for providers and Terraform, unused variables and locals, deprecated syntax. It uses the
`terraform` ruleset built into tflint, with the `recommended` preset.

## What installs locally

tflint ships no pre-commit hook, so the snippet is a short `repo: local` hook. On first
run pre-commit builds the pinned tflint with Go, and downloads Go first if it isn't
installed.
| Machine | First run | Disk |
|---|---|---|
| GitHub runners (Linux, Windows), Go installed | 1.4–2 min | about 80 MB |
| GitHub runners (macOS, Windows), pre-commit downloads Go | 0.5–2.5 min | 305–315 MB |
| Older Windows laptop (2017 i5, Defender on), no Go | about 10 min | about 335 MB |

Most of the time goes into compiling tflint, so a slow CPU hurts most here. Later runs
take seconds. To measure your own machine, run `uv run scripts/measure_install.py tflint`
from a clone of hookshelf.

Networks that block `proxy.golang.org` or `go.dev` stop this install.

## Files

- `snippet.yaml`: paste under `repos:` in `.pre-commit-config.yaml`. No config file is
  needed: tflint's defaults cover the built-in ruleset.

## Warn, then block

`args: [--force]` in the snippet prints findings, but the commit goes through. Remove that
line to block. In recursive mode tflint ignores `force` in config files, so this switch
lives in the hook.

## Tuning

- **One line:** add `# tflint-ignore: terraform_unused_declarations` above it.
- **Cloud rulesets** (AWS, Azure, Google): these need a `.tflint.hcl` **in each Terraform
  directory**, because `--recursive` reads the config from each module's own folder.
  They also need `tflint --init`, which downloads the plugin from GitHub. See
  <https://github.com/terraform-linters/tflint/blob/master/docs/user-guide/plugins.md>.
- **Updating:** `pre-commit autoupdate` doesn't update `repo: local` hooks. Bump the
  version in `additional_dependencies` by hand.

Provider docs: <https://github.com/terraform-linters/tflint>
