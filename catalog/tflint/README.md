# tflint

**Optional for Terraform. Warns (doesn't block) until you switch it.**

tflint is a linter for Terraform. It points out code that works today but is easy to
break, such as a provider with no version constraint, so you fix it before an upgrade does.

## What it catches

Terraform mistakes that `terraform validate` lets through: missing version constraints
for providers and Terraform, unused variables and locals, deprecated syntax. It uses the
`terraform` ruleset built into tflint, with the `recommended` preset.

## Set up

You need pre-commit installed and a `.pre-commit-config.yaml` in your repo. If you don't
have those yet, start with [setup](../../docs/setup.md).

1. Paste [`snippet.yaml`](snippet.yaml) under `repos:` in `.pre-commit-config.yaml`. Leave
   a blank line between it and the snippet above it. No config file is needed: tflint's
   defaults cover the built-in ruleset.
2. Install the hook and see what it finds today:

   ```sh
   pre-commit run tflint --all-files
   ```

   The first run builds tflint, which takes a while. See
   [What installs locally](#what-installs-locally). In warn mode the hook prints its
   findings and still says `Passed`.

## When it fires

The hook runs when a commit includes a `.tf`, `.tf.json` or `.tfvars` file. It then runs
`tflint --recursive`, which checks every Terraform directory in the repo, not just the
files you changed.

Here's a run on an insecure Terraform file, in warn mode:

```text
tflint...................................................................Passed
- hook id: tflint
- duration: 3.59s

2 issue(s) found:

Warning: terraform "required_version" attribute is required (terraform_required_version)

  on main.tf line 1:

Reference: https://github.com/terraform-linters/tflint-ruleset-terraform/blob/v0.17.0/docs/rules/terraform_required_version.md

Warning: Missing version constraint for provider "aws" in `required_providers` (terraform_required_providers)

  on main.tf line 26:
  26: resource "aws_s3_bucket_public_access_block" "public" {

Reference: https://github.com/terraform-linters/tflint-ruleset-terraform/blob/v0.17.0/docs/rules/terraform_required_providers.md
```

The commit goes through. In block mode (see [Warn, then block](#warn-then-block)) the same
issues print, but the hook fails and the commit stops:

```text
tflint...................................................................Failed
- hook id: tflint
- duration: 0.21s
- exit code: 2
```

For each issue:

1. Read the rule name in parentheses (`terraform_required_providers`) and the file and
   line.
2. Open the `Reference` link under it. It explains the rule and how to fix it.
3. Fix the code, then commit again.
4. Or, if the rule doesn't apply, ignore it with a comment or in `.tflint.hcl`. See
   [Tuning](#tuning).

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

## Warn, then block

`args: [--force]` in the snippet prints findings, but the commit goes through. Remove that
line to block. In recursive mode tflint ignores `force` in config files, so this switch
lives in the hook.

Because tflint checks the whole repo, a blocking tflint stops any commit that touches a
Terraform file while an issue remains anywhere in the repo. Fix or ignore everything it
reports before you switch.

## Tuning

- **One line:** add `# tflint-ignore: terraform_unused_declarations` on the line above it.
- **One file:** add `# tflint-ignore-file: terraform_required_version` as the first line
  of the file.
- **A rule that doesn't apply to a directory:** turn it off in a `.tflint.hcl` in that
  directory. The `recommended` preset still applies to every other rule.

  ```hcl
  rule "terraform_required_providers" {
    enabled = false
  }
  ```

  `--recursive` reads `.tflint.hcl` from each Terraform directory, so a file at the repo
  root doesn't reach modules in subfolders. Put one in each directory that needs it.
- **Cloud rulesets** (AWS, Azure, Google): enable the plugin in the `.tflint.hcl` of each
  Terraform directory, for the same reason, and run `tflint --init`, which downloads the
  plugin from GitHub. See
  <https://github.com/terraform-linters/tflint/blob/master/docs/user-guide/plugins.md>.
- **Updating:** `pre-commit autoupdate` doesn't update `repo: local` hooks. Bump the
  version in `additional_dependencies` by hand.

Provider docs: <https://github.com/terraform-linters/tflint>
