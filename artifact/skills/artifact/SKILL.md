---
name: artifact
description: |-
  The `/artifact` entry point — read, create, update, delete, list, and traverse artifacts of any scheme (document, PR, issue, release, artifact-template, conversation, preferences, composed_of, depends_on, validates, authors, tags, …) through the uniform mediator contract. Also authors new schemes + storages + templates. Triggered by "show a document", "list my PRs", "create a design-document", "edit artifact foo.md", "graph from release v2.3", "add a Jira storage", or any artifact URI like `document|file/docs/design/auth` / `issue|gh-issue/owner/repo/42`.
---

# artifact

All artifact operations route through the same Python mediator:
`python3 <plugin>/scripts/run-provider.py <URI-or-scheme> <subcommand>`. The mediator validates input with the scheme's
Pydantic models, resolves the storage (from the URI or user preference), then dispatches to the storage's
`cmd_<subcommand>` handler.

## Core model

Three **scheme kinds** — every scheme declares one in its `scheme.toml`:

- **vertex** — a first-class thing (document, PR, issue, template, conversation, preferences).
- **edge** — a typed link between two artifacts (`composed_of`, `depends_on`, `validates`, `references`, `mentions`,
  `supersedes`, `cites`, `bundled_in`, `closes`).
- **metadata** — a typed annotation attached to one target (`authors`, `tags`, `status`, …).

Schemes are Python + Pydantic. Each scheme dir holds `scheme.toml` (config + per-storage adapters) and `scheme.py`
(Pydantic content + subcommand in/out models + `SCHEME` object).

Storages are generic: `file` (git worktree), `user-config`, `session-memory`, `os-notifications`, `document-confluence`,
`gh-pr`, `gh-issue`, `gh-release`, `gh-milestone`, `gh-tag`, `gh-branch`, `gh-gist`. Each storage implements
`cmd_<subcommand>(scheme, adapter, input, uri) -> dict`.

The graph is made of artifacts: every edge is a stand-alone artifact of an edge-kind scheme. Query via
`python3 <plugin>/scripts/graph.py {expand|find|list} …`.

## Sub-command shape

| Pattern                                      | What to do                                                                   |
|----------------------------------------------|-------------------------------------------------------------------------------|
| `show <uri>`                                 | `run-provider.py <uri> get` (payload via stdin or `--data`)                   |
| `list <scheme> [--filter …]`                 | `run-provider.py <scheme> list` (payload = filter fields)                     |
| `create <scheme> {…}`                        | `run-provider.py <scheme> create --storage <s>` (payload = CreateIn)          |
| `instantiate <template-uri> {inputs}`        | `run-provider.py <template-uri> instantiate` (payload = `{uri, inputs, target_storage}`) |
| `update <uri> --patch {…}`                   | `run-provider.py <uri> update`                                                |
| `delete <uri>`                               | `run-provider.py <uri> delete`                                                |
| `status <uri>`                               | `run-provider.py <uri> status`                                                |
| `progress <uri>`                             | `run-provider.py <uri> progress`                                              |
| `lock <uri> --owner <user>`                  | `run-provider.py <uri> lock`                                                  |
| `graph <uri> [--relation R] [--depth N]`     | `graph.py expand --uri <uri>`                                                 |
| `graph find --relation R --target <uri>`     | `graph.py find`                                                               |
| `list schemes` / `list storages`             | Read `$ARTIFACT_CACHE_DIR/registry.json`                                      |

URI format: `<scheme>|<storage>/<path>`. Examples:

- `document|file/docs/design/auth`
- `pr|gh-pr/myorg/myrepo/42`
- `composed_of|file/artifact-edges/composed_of/<source-slug>--<target-slug>`
- `preferences|user-config/user`

## Storage resolution

Scheme-addressed calls (`create`, `list` without URI) resolve in this strict order:

1. Per-call `--storage <name>` override.
2. Saved preference `storage.<scheme>.default` in `$ARTIFACT_CONFIG_DIR/preferences/storage.json`.
3. Sole-storage short-circuit (persisted as the new default).
4. Prompt the user once, persist the answer.

URI-addressed calls dispatch to the storage named in the URI directly. Never alphabetical.

## Input / output validation

Every subcommand has `in_model` and `out_model` Pydantic classes defined in the scheme's `scheme.py`. The mediator
validates stdin JSON against `in_model` before dispatch, and the storage's return against `out_model` after. On failure:

```json
{"error": "schema-mismatch", "details": [{"loc": [...], "msg": "..."}, ...]}
```

exit code `3`. Other errors (missing storage, unknown subcommand, etc.) → `{"error": "..."}` exit `2`.

## Extending with your own schemes, storages, templates

Four scopes by precedence (highest first):

| Scope       | Path                                                 | Purpose                                    |
|-------------|------------------------------------------------------|--------------------------------------------|
| `override`  | `$CWD/.artifact-override/<bucket>/<name>/`           | One-off; for this working tree only        |
| `workspace` | `$REPO/.claude/<bucket>/<name>/`                     | Project-specific; committed to repo        |
| `user`      | `~/.claude/<bucket>/<name>/`                         | Personal; across all your projects         |
| `plugin`    | `<installed-plugin>/<bucket>/<name>/`                | Shipped by a plugin; immutable via Claude Code |

`<bucket>` ∈ `artifact-schemes`, `artifact-storage`, `artifact-templates`.

To add an edge relation `composed_of`, `depends_on`, etc.: create `artifact-schemes/<relation>/scheme.py` that calls
`artifactlib.edges.make_edge_scheme("<relation>")`. Pair with `scheme.toml` declaring the `[[storage]]` path template.

To add a storage (e.g. Jira): create `artifact-storage/jira/storage.toml` + `storage.py` exposing `cmd_create`,
`cmd_get`, `cmd_list`, `cmd_status`. Declare `backs_schemes = [...]` of schemes it can back.

## References

- `references/artifact-contract.md` — scheme + storage contract, subcommand shapes, validation.
- `references/discovery.md` — registry layout, scope precedence, troubleshooting missing entries.
- `references/extension-scaffold.md` — step-by-step new-scheme / new-storage guide.
- `references/creation.md` — template authoring (`.jinja.*` body + `.content.toml`).
- `references/composition.md` — graph edges as artifacts.

## Related skills

- `/workflow` — run and author workflows that produce artifacts.
