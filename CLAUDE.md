# CLAUDE.md

Read [docs/design.md](docs/design.md) first. It sets the goal, the audiences, the principles
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
