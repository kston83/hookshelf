# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

hookshelf: curated, pinned pre-commit security hooks that teams copy into their repos and
own. Read [docs/design.md](docs/design.md) first. It sets the goal, the audiences, the principles
and the non-goals for everything in this repo.

Before adding anything, check: does a team's repo still work if this repo disappears? If
a provider hook seems to need a wrapper, stop and ask.

## Working rules

- Pin every `rev` and action to a version you checked with `git ls-remote --tags`. Never
  guess a version or SHA.
- Prefer a provider's remote hook with a pinned `rev` over a `repo: local` hook.
- Test with real `pre-commit` runs on `tests/fixtures/`, not only unit tests.
- Never commit anything secret-looking. Fixtures use `<FAKE_...>` markers, which
  `tests/conftest.py` fills in at run time.
- Keep each PR reviewable in about 15 minutes.
- Use uv with Python 3.14 for this repo's tooling: `uv sync`, then `uv run pytest`. Add
  dev dependencies to `pyproject.toml` pinned with `==`, and commit `uv.lock`.

## Commands

```sh
uv sync                                            # uv itself is pinned (required-version in pyproject.toml)
uv run pytest                                      # everything
uv run pytest "tests/test_terraform_docker.py::test_insecure_fixture_warns_then_blocks[docker-expected1]"
uv run pytest --collect-only -q                    # list test IDs
uv run pytest tests/test_base_fixtures.py -k history   # -k also matches module names
REQUIRE_GITLEAKS=1 uv run pytest tests/test_gitleaks_rules.py   # fail instead of skip without gitleaks on PATH
uv run scripts/measure_install.py checkov          # first-install time/disk for one catalog tool
```

The fixture tests run real pre-commit, which downloads each hook into its cache on first run,
so the first run is slow and needs network access. `test_gitleaks_rules.py` needs a
`gitleaks` binary at the version pinned in `catalog/gitleaks/snippet.yaml` (CI reads the
`rev:` from there and `go install`s it).

## How it fits together

- `catalog/<tool>/` holds three kinds of file. `snippet.yaml` is one `repos:` entry, indented
  so it pastes under `repos:`. A README covers what the tool catches, what installs on first
  run (with measured first-run time and disk), and how to go from warn to block. Every other
  file is a config that goes to the team's repo root. Tests copy every file except
  `snippet.yaml` and `README.md` to the repo root, so only put files there that a team should
  copy.
- `catalog/stacks.yaml` maps stacks (`base`, `terraform`, `docker`) to recommended and
  optional tools, by folder name. `base` applies to every repo.
- `tests/conftest.py` reproduces the hand-copy path. `assemble()` builds the config as
  `repos:\n` plus the snippets joined by blank lines. `make_repo()` builds a throwaway git
  repo with that config, the tools' config files and a fixture, with the `<FAKE_...>`
  markers filled in. `run_pre_commit()` parses pre-commit's per-hook status lines, and
  `expect()` checks the exact set of hooks and their verdicts. Tests refer to hooks by the
  `name` pre-commit prints, not their `id`. If you add, rename or re-stage a hook, update
  the expected hook sets in the tests, or `expect()` fails.
- Policy: secrets block. Everything else starts in warn mode, and each tool's warn switch is
  a single line: `soft-fail: true` in `.checkov.yaml`, `no-fail: true` in `.hadolint.yaml`,
  and `args: [--force]` in the tflint snippet. `block_mode()` in
  `tests/test_terraform_docker.py` deletes those exact strings, so keep them byte-for-byte.
  It also reads the suggested skips from the commented `#   - CKV_...` lines in
  `.checkov.yaml`. The baseline test uncomments `# baseline:` and
  `# output-baseline-as-skipped:` there, so keep those byte-for-byte too.
- gitleaks has a second hook, `gitleaks-history`, in the `manual` stage. CI runs it with
  `pre-commit run --all-files --hook-stage manual`.
- checkov also has a `manual`-stage hook, `checkov-baseline`, which writes
  `.checkov.baseline`. That same CI command runs it as well. The baseline test runs the one
  `pre-commit run ` line under the checkov README's `### Baseline the backlog` heading.
- `scripts/measure_install.py` is a standalone uv script with PEP 723 inline dependencies.
  It installs each tool into its own temporary pre-commit cache. `.github/workflows/measure.yml`
  runs it on GitHub's runners, and its numbers go into each tool's README.
- The setup script in `docs/design.md` doesn't exist yet. When it's written, it must
  produce byte-identical files to `assemble()` plus the copied configs. It must use only
  the standard library, stay under ~200 lines, and run on Windows, macOS and Linux.
- Line endings are LF (`.gitattributes`). When you write files in tests, pass `newline="\n"`
  so Windows runs match CI.
