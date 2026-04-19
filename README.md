# artifact — Claude Code plugin ecosystem

Primitive plugins for working with artifacts — documents, PRs, issues, templates, conversations, notifications, and any
user-authored scheme — from a Claude Code session. Artifacts form a typed knowledge graph. Three plugins ship here:

| Plugin                                       | Purpose                                                                                                                                    |
|----------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------|
| [`artifact`](./artifact-plugin)                     | Core primitive: scheme kinds (vertex/edge/metadata), Pydantic scheme loader, generic storages (`file`, `user-config`, `session-memory`, `os-notifications`), jinja templating, `/artifact` skill. |
| [`artifact-github`](./artifact-github-plugin)       | GitHub-backed storages (`gh-pr`, `gh-issue`, `gh-release`, `gh-milestone`, `gh-tag`, `gh-branch`, `gh-gist`) for the corresponding schemes. Requires `artifact`. |
| [`artifact-documents`](./artifact-documents-plugin) | `document` scheme + `document-confluence` storage + eight markdown templates. Requires `artifact`.                                         |

See [`artifact/DESIGN.md`](./artifact-plugin/DESIGN.md) for the architectural source of truth — scheme kinds, storage
adapters, URI format (`<scheme>|<storage>/<path>`), the graph-as-artifacts model, and local state layout.

## Install

```bash
claude plugin marketplace add cjhowe-us/marketplace
claude plugin install artifact@cjhowe-us-marketplace
claude plugin install artifact-github@cjhowe-us-marketplace        # optional
claude plugin install artifact-documents@cjhowe-us-marketplace     # optional
```

## Prerequisites

- Python ≥ 3.11 with `pydantic>=2`, `tomlkit>=0.13`, `jinja2>=3.1` on the path the plugin uses. Install once:
  `python3 -m pip install --user pydantic tomlkit jinja2`.
- `git` on `PATH`.
- `gh` authenticated (`gh auth login`) if using `artifact-github`.

Cross-platform: Linux, macOS, Windows.

## License

Apache-2.0.
