# Design

## Goal

A team runs one script, or copies a few snippets by hand, and ends up with working
pre-commit security hooks without having to think about it. That makes good security
practice accessible.

## Audiences, in order

1. **Our DevOps team.** Terraform, Docker, Jenkins (Jenkins is their CI).
2. **GitHub Actions users**, for wider adoption.
3. **Our software development team.** Languages and package managers come later, after
   asking them.

## Principles

- **Two ways in, same result.** The setup script and hand-copying from `catalog/` produce
  byte-identical files.
- **No runtime dependency on this repo.** After setup the team owns plain files. Every hook
  comes from the tool provider's repo, or is a short `repo: local` hook that runs the
  provider's own tool. No file in a team's repo is read only by our code.
- **We curate; we don't write hooks or rules.** We pick tools, pin versions, ship sensible
  config files and explain each tool.
- **Choosing is optional.** Recommended tools are ticked; pressing Enter accepts them.
- **Accessible means not annoying.** Secrets block. Everything else starts in warn mode. We
  say plainly what installs on first run and how long it takes.
- **Free and open source only.** No accounts or API keys.
- **Small.** The setup script stays under ~200 lines, uses only the Python standard library,
  and runs on Windows, macOS and Linux.

## Non-goals

- Wrappers around provider hooks, vendored rule packs, or custom SAST rules.
- State files, `update` or `doctor` commands, or anything a team's repo consumes by
  reference from this one.
- Merging into an existing `.pre-commit-config.yaml`. We print the snippets to paste instead.
- Paid tools, or tools that need an account or API key.
