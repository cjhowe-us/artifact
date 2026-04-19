# artifact-contract

Contract for **schemes** (the type of an artifact) and **storages** (where the artifact lives). Schemes are Python +
Pydantic. Storages are Python modules exposing a small I/O surface. The mediator in `artifactlib.provider` sits between
them, validating every subcommand's input and output against the scheme's Pydantic models.

## Directory layout

```text
<plugin>/artifact-schemes/<scheme-name>/
  scheme.toml   # name, kind, description, contract_version, [[storage]] adapters
  scheme.py     # pydantic models + SCHEME object
  README.md     # optional

<plugin>/artifact-storage/<storage-name>/
  storage.toml  # name, description, backs_schemes, capabilities
  storage.py    # cmd_<subcommand> handlers
  README.md     # optional
```

## Invocation

All calls go through:

```text
python3 <plugin>/scripts/run-provider.py <URI-or-scheme> <subcommand> [--storage <name>] [--uri <u>] [--data <path|->]
```

- First arg is a URI (`<scheme>|<storage>/<path>`) or a bare scheme name.
- Payload is JSON on stdin (default) or from `--data <path>`.
- Output is one JSON document on stdout.
- Exit codes:
  - `0` success
  - `2` dispatch error (missing storage, unknown subcommand, …) → `{"error": "..."}`
  - `3` schema mismatch (pydantic validation failed) → `{"error": "schema-mismatch", "details": [...]}`

## Scheme shape

`scheme.toml`:

```toml
name             = "document"
scheme           = "document"
kind             = "vertex"           # vertex | edge | metadata
description      = "…"
contract_version = 1

[[storage]]
name                  = "file"
body_field            = "body"
body_path_template    = "{{ id }}.md"
content_path_template = "{{ id }}.content.toml"
content_serializer    = "toml"

[[storage]]
name = "document-confluence"          # remote storage — no path templates
```

`scheme.py`:

```python
from pydantic import BaseModel
from artifactlib.kinds import Kind
from artifactlib.scheme import Scheme, Subcommand


class DocumentContent(BaseModel):
    title: str = ""
    authors: list[str] = []
    status: str = "draft"
    body: str = ""


class CreateIn(BaseModel):
    id: str
    title: str = ""
    authors: list[str] = []
    status: str = "draft"
    body: str = ""


class CreateOut(BaseModel):
    uri: str
    created: bool


SCHEME = Scheme(
    kind=Kind.VERTEX,
    name="document",
    contract_version=1,
    content_model=DocumentContent,
    subcommands={
        "create": Subcommand(in_model=CreateIn, out_model=CreateOut, required=True),
        # get / update / delete / status / list similarly
    },
    edge_relations=("composed_of", "depends_on", "mentions", "supersedes"),
)
```

Loaded via `importlib.util.spec_from_file_location` — no package install required.

### Edge schemes (factory)

```python
# artifact-schemes/composed_of/scheme.py
from artifactlib.edges import make_edge_scheme
SCHEME = make_edge_scheme("composed_of")
```

Content shape for every edge: `{source: URI, target: URI, relation: str, attrs: dict}`.

## Storage shape

`storage.toml`:

```toml
name          = "file"
description   = "Stores artifacts under the git worktree."
backs_schemes = ["document", "composed_of", …]     # informational
contract_version = 1

[capabilities]
supports_locking = true
supports_listing = true
```

`storage.py` exposes one handler per subcommand:

```python
def cmd_create(*, scheme, adapter, input, uri):
    # scheme:  Scheme object
    # adapter: the scheme's [[storage]] entry for this storage (dict)
    # input:   validated Pydantic BaseModel (subcommand's in_model)
    # uri:     the URI if one was passed; None on scheme-addressed calls
    return {"uri": "...", "created": True}
```

Analogous: `cmd_get`, `cmd_update`, `cmd_delete`, `cmd_list`, `cmd_status`, `cmd_lock`, `cmd_release`, `cmd_progress`.

## Subcommand output shapes

Each scheme's `Subcommand.out_model` defines the expected output. Universal patterns:

| Subcommand | Returns                                                      |
|------------|--------------------------------------------------------------|
| `create`   | `{uri, created: true}`                                       |
| `get`      | `{uri, content: <scheme.content_model>}`                     |
| `update`   | `{uri, updated: true}`                                       |
| `delete`   | `{uri, deleted: true}`                                       |
| `status`   | `{uri, status: "complete"|"unknown"|"running"|...}`          |
| `list`     | `{entries: [{uri, kind, summary?}, ...]}`                    |
| `lock`     | `{held: bool, current_owner: str}`                           |
| `release`  | `{released: bool}`                                           |
| `progress` | `{entries: [...]}` on read; `{appended: true}` on append     |

## `artifact-template.instantiate` (cross-scheme)

Owned by the mediator, not by a storage. Flow:

1. Load the template (registry-first for shipped templates, else storage `get`).
2. Build an ad-hoc Pydantic model from `template.inputs`; validate user inputs.
3. Jinja-render `template.body` and every string in `template.output.create_input`.
4. Render `template.output.path_template` → produced artifact's `id`.
5. Dispatch `<target_scheme> create` with `{id, body, ...rendered-create-input}`.
6. Create a `composed_of` edge artifact from produced → template.
7. Return `{produced_uri, edges: [edge_uri, ...]}`.

## Invariants schemes + storages must uphold

1. **Stable URIs.** Once `create` returns a URI, it stays valid for the artifact's lifetime.
2. **Idempotent writes.** `update`, `release`, `delete` must be safe to retry.
3. **No silent mutation.** `get` always reflects the current state; no stale cache.
4. **External-mutation reconciliation.** If the storage changes outside the plugin (e.g. the file is edited directly, or
   the GitHub PR is edited on the web), the next `get` reflects it.
5. **Schema-mismatch first.** Any malformed input or output is rejected with `schema-mismatch`, not silently coerced.
6. **Cross-platform.** Paths use `pathlib`; subprocesses use list argv (never `shell=True`). Locks use
   `os.open(O_CREAT | O_EXCL)`.

## Authoring a new scheme or storage

1. Pick a unique name.
2. Scaffold at `<plugin-root>/artifact-schemes/<name>/` or `artifact-storage/<name>/`.
3. Write `scheme.toml` / `scheme.py` (or `storage.toml` / `storage.py`).
4. Run `pytest` — the conformance suite (`artifactlib/conformance.py`) validates coverage of required subcommands.
5. Ship the plugin; auto-discovered at session start by `hooks/sessionstart-discover.py`.

## Versioning

Breaking changes bump `contract_version` in `scheme.toml` / `storage.toml`. Discovery refuses schemes/storages whose
major doesn't match core. Minor bumps are additive subcommands marked `required = false`.
