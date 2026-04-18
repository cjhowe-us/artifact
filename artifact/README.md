# artifact

Core artifact primitive for the `cjhowe-us/artifact` ecosystem. Ships:

- **Scheme kinds** — `vertex`, `edge`, `metadata`. Every scheme declares one.
- **Core schemes** — `artifact-template`, `pydantic-schema`, `preferences`, `conversation`, `notifications`. Plus nine
  edge-kind schemes (`composed_of`, `depends_on`, `validates`, `references`, `mentions`, `supersedes`, `cites`,
  `bundled_in`, `closes`) via a shared factory. Plus metadata-kind schemes (`authors`, `tags`, `status`).
- **Core storages** — `file` (git worktree), `user-config`, `session-memory`, `os-notifications`.
- **Generic mediator** — validates every subcommand's inputs and outputs via pydantic, dispatches to storages.
- **Jinja templating** — `.jinja.*` file naming convention drives rendering via `artifactlib.render`.
- **Graph** — every edge is an artifact; `graph.py` is a thin wrapper over `list` with relation + endpoint filters.
- **`/artifact` skill** — user entry point.

Zero runtime deps besides Python 3.11+, `pydantic>=2`, `tomlkit>=0.13`, `jinja2>=3.1`. Cross-platform.

Source of truth: [`DESIGN.md`](./DESIGN.md).

## Install

```bash
claude plugin marketplace add cjhowe-us/marketplace
claude plugin install artifact@cjhowe-us-marketplace
```

Other ecosystem plugins (`artifact-github`, `artifact-documents`, `workflow`) depend on this one.

## Layout

```text
artifact/
  DESIGN.md
  scripts/
    artifactlib/           # shared Python package — kinds, scheme loader, storages, graph, mediator
    run-provider.py        # dispatch CLI
    graph.py               # graph CLI
  hooks/
    sessionstart-discover.py
    hooks.json
  artifact-schemes/        # one dir per scheme: scheme.toml + scheme.py + README.md
  artifact-storage/        # one dir per storage: storage.toml + storage.py + README.md
  tests/                   # pytest
```

## URI format

```text
<scheme>|<storage>/<path>
```

Examples:

- `document|file/docs/design/auth` — a document vertex stored as `docs/design/auth.md` + `.content.toml`.
- `composed_of|file/<source-slug>--<target-slug>` — an edge artifact JSON.
- `preferences|user-config/user` — the user's preferences bundle.

## Prerequisites

Python 3.11+ with `pydantic>=2`, `tomlkit>=0.13`, `jinja2>=3.1`. `git` on `PATH`.

## License

Apache-2.0.
