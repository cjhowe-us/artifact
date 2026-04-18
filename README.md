# artifact — Claude Code plugin ecosystem

Primitive plugins for working with artifacts (PRs, issues, documents, executions, templates, …)
from a Claude Code session. Three plugins ship here:

| Plugin               | Purpose |
|----------------------|---------|
| [`artifact`](./artifact)             | Core primitive: schemes, backends, templates, graph, `/artifact` skill. Zero plugin deps. |
| [`artifact-github`](./artifact-github) | GitHub-backed backends (`gh-pr`, `gh-issue`, `gh-release`, `gh-milestone`, `gh-tag`, `gh-branch`, `gh-gist`) for the `pr`, `issue`, `release`, `milestone`, `tag`, `branch`, `gist` schemes. Requires `artifact`. |
| [`artifact-documents`](./artifact-documents) | Document scheme + `document-filesystem` / `document-confluence` backends + eight markdown templates. Requires `artifact`. |

See [`artifact/DESIGN.md`](./artifact/DESIGN.md) for the architectural source of truth —
three concepts (provider = scheme type, backend = storage, artifact = instance), the typed edge
graph, URI format (`<scheme>|<backend>/<path>`), backend resolution, local state layout.

## Install

```bash
claude plugin marketplace add cjhowe-us/marketplace
claude plugin install artifact@cjhowe-us-marketplace
claude plugin install artifact-github@cjhowe-us-marketplace        # optional
claude plugin install artifact-documents@cjhowe-us-marketplace     # optional
```

## Prerequisites

- `bash`, `jq`, `git`, `python3` on `PATH`.
- `gh` authenticated (`gh auth login`) if using `artifact-github`.

## License

Apache-2.0.
