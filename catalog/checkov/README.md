# checkov

**Recommended for Terraform and Docker. Warns (doesn't block) until you switch it.**

checkov reads your Terraform and Dockerfiles and flags insecure settings, like an open
security group or a public bucket, while they're still a one-line fix in your editor.

## What it catches

Misconfigurations in Terraform and Dockerfiles, for example:

- Terraform: security groups open to `0.0.0.0/0`, public S3 buckets, unencrypted storage,
  missing logging (AWS, Azure and GCP checks).
- Dockerfiles: `latest` base image tags, running as root, `ADD` from a URL, SSH exposed.

## Set up

You need pre-commit installed and a `.pre-commit-config.yaml` in your repo. If you don't
have those yet, start with [setup](../../docs/setup.md).

1. Paste [`snippet.yaml`](snippet.yaml) under `repos:` in `.pre-commit-config.yaml`. Leave
   a blank line between it and the snippet above it.
2. Copy [`.checkov.yaml`](.checkov.yaml) to your repo root. checkov finds it there
   automatically.
3. Install the hook and see what it finds today:

   ```sh
   pre-commit run checkov --all-files
   ```

   The first run installs checkov, which takes a while. See
   [What installs locally](#what-installs-locally). In warn mode the hook prints its
   findings and still says `Passed`.

The snippet overrides the provider hook's `files:`, which only covers `.tf`, so that
tfvars, Terraform JSON and Dockerfiles trigger a scan too.

## When it fires

The hook runs when a commit includes a `.tf`, `.tf.json` or `.tfvars` file, or a
Dockerfile. It then scans the whole repo, not just the files you changed, so findings in
files you didn't touch show up too. To stop old findings from blocking commits once you
switch to block, see [Baseline the backlog](#baseline-the-backlog).

Here's a trimmed run on an insecure Terraform file, in warn mode:

```text
Checkov..................................................................Passed
- hook id: checkov
- duration: 16.03s

terraform scan results:

Passed checks: 9, Failed checks: 13, Skipped checks: 0

Check: CKV_AWS_24: "Ensure no security groups allow ingress from 0.0.0.0:0 to port 22"
	FAILED for resource: aws_security_group.ssh_open
	File: \main.tf:9-20
Check: CKV_AWS_53: "Ensure S3 bucket has block public ACLS enabled"
	FAILED for resource: aws_s3_bucket_public_access_block.public
	File: \main.tf:26-32
...
```

The commit goes through. In block mode (see [Warn, then block](#warn-then-block)) the same
findings print, but the hook fails and the commit stops:

```text
Checkov..................................................................Failed
- hook id: checkov
- duration: 10.13s
- exit code: 1
```

For each finding:

1. Read the check ID (`CKV_AWS_24`), the resource and the file and line range. The quoted
   text says what checkov expects.
2. If you need more, look the ID up in checkov's policy index:
   [Terraform](https://www.checkov.io/5.Policy%20Index/terraform.html),
   [Dockerfile](https://www.checkov.io/5.Policy%20Index/dockerfile.html).
3. Fix the code, then commit again.
4. Or, if the check doesn't apply, skip it with a reason. Skip one resource inline, or skip
   the check for the whole repo in `.checkov.yaml`. See [Tuning](#tuning).

checkov itself only scans Dockerfiles named `Dockerfile`, `Dockerfile.<anything>`,
`<anything>.Dockerfile` or `<anything>.dockerfile`. A commit that changes a
`Containerfile` or a file like `Dockerfile-prod` runs the hook, but checkov doesn't report
anything in those files (checked with 3.4.3).

## What installs locally

The hook is `language: python`. On first run pre-commit installs checkov and its
dependencies, about 100 Python packages, into its cache.

| Machine | First run | Disk |
|---|---|---|
| GitHub runners (Linux, macOS, Windows) | 0.6–1.2 min | 290–335 MB |
| Older Windows laptop (2017 i5, Defender on) | about 6 min | about 360 MB |

Later runs skip the install, but each run still starts checkov and scans the whole repo.
On a Windows 11 machine that took 10–16 s for a small repo. To measure your own machine,
run `uv run scripts/measure_install.py checkov` from a clone of hookshelf.

On Windows, pre-commit clones checkov's whole repo, which has paths up to 173 characters
long. With pre-commit's default cache (`%USERPROFILE%\.cache\pre-commit`) that fits within
Windows' 260-character limit. If you set `PRE_COMMIT_HOME` to a deep folder, the install
fails with `Filename too long`. Fix it with `git config --global core.longpaths true`.

checkov doesn't read OpenTofu's `.tofu` files (checked with 3.4.3).

## Warn, then block

`soft-fail: true` in `.checkov.yaml` prints findings, but the commit goes through. Delete
that line, and checkov blocks commits.

Because checkov scans the whole repo, a blocking checkov stops any commit that touches a
Terraform file or Dockerfile while a finding remains anywhere in the repo, even in a file
the commit doesn't change. Before you switch, either:

- **Clear the backlog:** fix or skip everything it reports (see [Tuning](#tuning)), or
- **Baseline it:** record today's findings so that only new ones block, and track the old
  ones as work to do. See below.

checkov also has a `checkov_diff` hook that scans only the staged files. We don't use it.
It still reports every old finding in a file you touch, and it can't see the rest of the
module. For example, with a security group in `sg.tf`, its CIDR in a variable in
`vars.tf` and the network interface that uses it in `ec2.tf`, scanning `sg.tf` alone
misses `CKV_AWS_24` (SSH open to the world) and falsely reports `CKV2_AWS_5` (security
group not attached). Checked with 3.4.3.

### Baseline the backlog

A baseline is a file, `.checkov.baseline`, listing each resource and the checks it fails
today. checkov stops failing on those, so commits are only blocked by new findings. The
old findings still need fixing: the baseline is a backlog, not an exception list.

1. **Record today's findings** while you're still in warn mode. Run this from your repo
   root. checkov lives inside pre-commit's cache, so this runs a separate copy with
   [uv](https://docs.astral.sh/uv/). Keep its version the same as the snippet's `rev`:

   ```sh
   uvx --python 3.14 --from checkov==3.4.3 checkov -d . --create-baseline --baseline ""
   ```

   It prints the findings and writes `.checkov.baseline`. The first run installs checkov
   again, which takes about as long as the hook's first run (see
   [What installs locally](#what-installs-locally)). `--baseline ""` ignores any baseline
   already set in `.checkov.yaml`. Without it, checkov writes an empty baseline when one
   is set (checked with 3.4.3).

2. **Track the backlog outside the repo.** Put the printed findings in your team's issue
   tracker with an owner and a date: one ticket with the list, or one per resource.

3. **Switch to block.** In `.checkov.yaml`, uncomment `baseline:` and
   `output-baseline-as-skipped:`, and delete `soft-fail: true`. Commit both files in one
   pull request that links the ticket.

From then on, only findings that aren't in the baseline fail the hook. Baselined ones
count under `Skipped checks` on every run, so the backlog stays in view. Here a commit adds
a security group open on port 3389 to a repo with 13 baselined findings:

```text
Checkov..................................................................Failed
- hook id: checkov
- duration: 9.01s
- exit code: 1

terraform scan results:

Passed checks: 0, Failed checks: 2, Skipped checks: 13

Check: CKV_AWS_25: "Ensure no security groups allow ingress from 0.0.0.0:0 to port 3389"
	FAILED for resource: aws_security_group.rdp_open
	File: \main.tf:34-44
...
```

**Working the backlog down:**

- To print everything, baselined or not, run the step 1 command without
  `--create-baseline`.
- After you fix findings, run the step 1 command again and commit the new
  `.checkov.baseline`. Its diff should only remove lines. An added line means a new
  finding is being accepted without review. Fix it, or skip it inline with a reason (see
  [Tuning](#tuning)), so the reason sits next to the code.
- Review changes to `.checkov.baseline` like code. If your Git host supports code owners,
  make your security reviewer an owner of it.
- When the backlog is done, delete the two baseline lines from `.checkov.yaml`, then
  delete `.checkov.baseline`.

**What the baseline matches on:** a resource address and a check ID, not a file or line
(checked with 3.4.3). So:

- Editing a file, or moving a Terraform resource to another file, doesn't bring its
  findings back. Renaming the resource does.
- Two resources with the same address in different folders, such as `aws_s3_bucket.logs`
  in both `envs/dev` and `envs/prod`, share one entry. If one is baselined, the same
  findings in the other are hidden too. Print everything (above) when you add a folder.
- A Dockerfile's address is its path, like `/app\Dockerfile.RUN` on Windows. Moving a
  Dockerfile brings its findings back. Windows writes the path with `\` and macOS and
  Linux with `/`, so a baselined Dockerfile in a subfolder only matches on the kind of
  OS that made the baseline. If your team commits from both, fix or skip Dockerfile
  findings inline instead of baselining them.

## Tuning

- **A check that doesn't apply to your team:** `.checkov.yaml` has commented-out
  suggestions under `skip-check:`. Uncomment them, or add your own, with a reason. These
  apply to the whole repo.
- **One Terraform resource only:** put the skip comment inside the resource block. A
  comment above the block doesn't work.

  ```hcl
  resource "aws_security_group" "bastion" {
    # checkov:skip=CKV_AWS_24: bastion host, only reachable over the VPN
    ...
  }
  ```

  The check then counts under `Skipped checks` instead of `Failed checks`.
- **One Dockerfile only:** put `# checkov:skip=CKV_DOCKER_1: reason` on its own comment
  line anywhere in the Dockerfile. It skips that check for the whole file, not just the
  next instruction. A comment at the end of an instruction line (`EXPOSE 22 # checkov:...`)
  doesn't work.
- **More frameworks** (Kubernetes, Helm ...): add them to `framework:`. The hook still only
  fires on Terraform files and Dockerfiles, so also add those files to the snippet's
  `files:`. For Kubernetes YAML, for example, add `|\.ya?ml$` to the end of the pattern.

Provider docs: <https://www.checkov.io/>
