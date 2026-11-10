# hadolint

**Optional for Docker. Warns (doesn't block) until you switch it.**

hadolint is a linter for Dockerfiles. It checks each instruction against Docker's best
practices and runs ShellCheck on your `RUN` commands, so you catch unpinned images and
shell mistakes before you build.

## What it catches

Dockerfile best practices (unpinned base images and packages, `sudo`, `latest` tags,
relative `WORKDIR`), plus ShellCheck findings inside `RUN` instructions.

## Set up

You need pre-commit installed and a `.pre-commit-config.yaml` in your repo. If you don't
have those yet, start with [setup](../../docs/setup.md).

1. Paste [`snippet.yaml`](snippet.yaml) under `repos:` in `.pre-commit-config.yaml`. Leave
   a blank line between it and the snippet above it.
2. Copy [`.hadolint.yaml`](.hadolint.yaml) to your repo root, where hadolint finds it
   automatically.
3. Install the hook and see what it finds today:

   ```sh
   pre-commit run hadolint --all-files
   ```

   The first run installs hadolint, which is quick. See
   [What installs locally](#what-installs-locally). In warn mode the hook prints its
   findings and still says `Passed`.

## When it fires

The hook runs on the files in a commit that pre-commit recognizes as Dockerfiles:
`Dockerfile`, `Containerfile`, `Dockerfile.<anything>` and `<anything>.Dockerfile`. It
checks only those files. It skips names like `app.dockerfile` (lowercase) and
`Dockerfile-prod` (checked with pre-commit 4.7.0).

Here's a run on an insecure Dockerfile, in warn mode:

```text
Hadolint.................................................................Passed
- hook id: hadolint
- duration: 0.54s

Dockerfile:2 DL3007 warning: Using latest is prone to errors if the image will ever update. Pin the version explicitly to a release tag
Dockerfile:4 DL3015 info: Avoid additional packages by specifying `--no-install-recommends`
Dockerfile:4 DL3009 info: Delete the apt lists (/var/lib/apt/lists) after installing something
Dockerfile:4 DL3008 warning: Pin versions in apt get install. Instead of `apt-get install <package>` use `apt-get install <package>=<version>`
Dockerfile:5 DL3004 error: Do not use sudo as it leads to unpredictable behavior. Use a tool like gosu to enforce root
```

Each line is the file and line number, the rule ID, its severity and what's wrong. The
commit goes through. In block mode (see [Warn, then block](#warn-then-block)) the same
lines print, but the hook fails and the commit stops, because one finding (`DL3004`) is
an `error`:

```text
Hadolint.................................................................Failed
- hook id: hadolint
- duration: 0.1s
- exit code: 1
```

For each finding:

1. Read the rule ID and the line number.
2. If you need more, look the ID up. `DL` rules are hadolint's own, for example
   <https://github.com/hadolint/hadolint/wiki/DL3004>. `SC` rules come from ShellCheck,
   for example <https://www.shellcheck.net/wiki/SC2164>.
3. Fix the Dockerfile, then commit again.
4. Or, if the rule doesn't apply, ignore it on one line or in `.hadolint.yaml`. See
   [Tuning](#tuning).

## What installs locally

The hook comes from `AleksaC/hadolint-py`, which packages the hadolint binary as a Python
wheel, so you need neither Docker nor a system install.

| Machine | First run | Disk |
|---|---|---|
| GitHub runners (Linux, macOS, Windows) | under 15 s | 120–210 MB |
| Older Windows laptop (2017 i5, Defender on) | under 1 min | about 180 MB |

The disk is the hadolint binary plus a Python environment. Later runs take well under a
second. To measure your own machine, run `uv run scripts/measure_install.py hadolint`
from a clone of hookshelf.

## Warn, then block

`no-fail: true` in `.hadolint.yaml` prints findings, but the commit goes through. Delete
that line to block on findings at or above `failure-threshold` (`error` as shipped). Lower
it to `warning` to block on more.

Findings below the threshold still print, but they don't stop the commit. With the
example above in block mode, fixing the `sudo` line (`DL3004`) is enough to commit. Set
`failure-threshold: warning` and `DL3007` and `DL3008` block too.

## Tuning

- **A rule that doesn't apply:** add it to `ignored:` with a reason.

  ```yaml
  ignored:
    - DL3008  # apt versions aren't pinned: we rebuild nightly from a pinned base image
  ```

- **One line:** put `# hadolint ignore=DL3008` on the line above the instruction.
  Separate several rules with commas: `# hadolint ignore=DL3008,DL3015`.
- **Approved registries only:** uncomment `trustedRegistries:` and list your registries.
  A `FROM` image from anywhere else is then reported as `DL3026`, an `error`.

Provider docs: <https://github.com/hadolint/hadolint>
