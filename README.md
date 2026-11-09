# hookshelf

Curated, pinned pre-commit security hooks that you copy into your repo and own.

> Work in progress. See [docs/design.md](docs/design.md) for the goal and principles.

## What's here so far

- `catalog/<tool>/snippet.yaml`: a `repos:` entry to paste under `repos:` in your
  `.pre-commit-config.yaml`.
- `catalog/<tool>/<config>`: the tool's config file, if it needs one. Copy it to your repo root.
- `catalog/<tool>/README.md`: what the tool catches, what installs locally, and how to tune it.
- `catalog/stacks.yaml`: which tools each stack recommends.

Every hook comes from the tool provider's own repo. Once copied, nothing in your repo
depends on this one.

## License

Apache-2.0
