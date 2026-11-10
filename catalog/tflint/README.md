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
Measured on a Windows laptop without Go: the first run took about 10 minutes and used about
335 MB of disk (the Go toolchain, tflint's modules and the build). Later runs take seconds.

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
