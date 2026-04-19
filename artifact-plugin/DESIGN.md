# artifact plugin — design document

Source of truth for the artifact primitive's architecture. Append-only changelog at the bottom records material design
decisions. Edits that change these choices must add a dated entry here.

## Problem

Workflow- and knowledge-oriented plugins need a single, uniform primitive for every read or write: local files, markdown
docs, GitHub PRs and issues, Jira tickets, Confluence pages, persisted AI conversations, workflow executions, template
definitions. Each external system is wildly different, but plugin authors should not care. They should declare "this
thing is an artifact of type X" and the engine should route it to the right storage.

On top of that, agents need a **knowledge graph** they can traverse to pull in relevant context: which design doc
produced this implementation plan, which tests depend on which schema, which PR closes which issue. The graph is made of
artifacts — edges and metadata are themselves artifacts — so traversal is the same mechanism used for creating and
reading.

## Non-goals

- A workflow engine. That lives in the separate `workflow` plugin, which depends on this one.
- A caching layer, CRDT, or file server. The artifact plugin *points to* external state; it does not duplicate it.
- Automatic invalidation or change detection. The graph is queryable; re-validation is a caller concern.

## Goals

- **One universal type: the artifact.** No sidecars. No frontmatter. Vertices, edges, and metadata are all artifacts in
  their own right.
- **Three scheme kinds: vertex, edge, metadata.** Every scheme declares one kind. The kind determines the artifact's
  role in the graph; the scheme's Pydantic model defines its content.
- **Schemes are Python + Pydantic.** Every scheme ships a `scheme.py` next to a `scheme.toml`. Pydantic models validate
  every subcommand's inputs and outputs at the mediator boundary.
- **Storages are generic.** `file`, `session-memory`, `user-config`, `os-notifications`, `gh-pr`, `gh-issue`, … Each
  storage reads/writes bytes in its own substrate. The scheme decides, per compatible storage, how its artifacts are
  encoded (path template, serializer).
- **The graph is the artifacts.** `composed_of`, `depends_on`, `validates`, `references`, `mentions`, `supersedes`,
  `cites`, `bundled_in`, `closes` are each their own edge-kind scheme. Querying the graph is just `list`-ing edge
  artifacts with filters.
- **Zero bash.** Python 3.11+, pydantic 2, tomlkit, jinja2. `git` required. `gh` required only for `artifact-github`.
  Cross-platform (Linux / macOS / Windows).

## The three kinds

Every scheme sets its `kind` in `scheme.toml` to one of:

- **vertex** — a first-class thing: a document, a PR, an issue, a template, a conversation, a notification, a preference
  bundle. Carries arbitrary Pydantic content.
- **edge** — a typed link between two artifacts. Content shape:
  `{source: URI, target: URI, relation: str, attrs: dict[str, Any]}`. Each relation is its own scheme (`composed_of`,
  `depends_on`, …), all of `kind = "edge"`. They all share an identical content shape via the
  `artifactlib.edges.make_edge_scheme(relation)` factory.
- **metadata** — a typed annotation attached to exactly one target artifact. Content shape:
  `{target: URI, …scheme- specific fields}`. Used when a small structured blob accompanies a vertex without needing a
  full artifact.

The canonical enum lives in `artifactlib.kinds.Kind`.

## Scheme — Python + Pydantic

```text
artifact-schemes/<scheme>/
  scheme.toml   # kind, description, contract_version, [[storage]] adapters
  scheme.py     # pydantic content model + SCHEME object
  README.md
```

### `scheme.toml`

```toml
name             = "document"
scheme           = "document"
kind             = "vertex"
description      = "Markdown document with structured content."
contract_version = 1

# One [[storage]] entry per compatible storage backend. Each entry declares
# how this scheme's artifacts are encoded in that storage. Keys beyond `name`
# are passed to the storage module verbatim as the "adapter" config dict.
[[storage]]
name                  = "file"
body_field            = "body"
body_path_template    = "{id}.md"
content_path_template = "{id}.content.toml"
content_serializer    = "toml"
```

### `scheme.py`

```python
from pydantic import BaseModel
from artifactlib.scheme import Scheme, Subcommand
from artifactlib.kinds import Kind


class DocumentContent(BaseModel):
    title: str
    authors: list[str]
    status: str
    body: str


class CreateIn(BaseModel):
    path: str
    content: DocumentContent


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
        # get / update / list / delete / status analogously
    },
)
```

### Scheme module loader

`artifactlib.scheme.load_scheme(path: Path) -> Scheme`:

- Uses `importlib.util.spec_from_file_location("artifact_scheme_<hash>", path)`.
- Returns the module's `SCHEME` attribute.
- No package install required; no `__init__.py` chain; no sys.path mutation.

## Storage — generic read/write adapters

```text
artifact-storage/<name>/
  storage.toml   # capabilities + compatible schemes
  storage.py     # read/write impl
  README.md
```

### `storage.toml`

```toml
name        = "file"
description = "Stores artifacts as files in the git worktree."

# Informational. Authoritative mapping is each scheme's [[storage]] entry.
backs_schemes = ["composed_of", "depends_on", "validates", "document", "artifact-template", "authors", "pydantic-schema"]

[capabilities]
supports_locking = true
supports_listing = true
supports_watching = false
```

### `storage.py` contract

```python
def write_content(path: str, content: dict | bytes, *, serializer: str) -> None: ...
def write_body(path: str, body: str | bytes) -> None: ...
def read_content(path: str, *, serializer: str) -> dict: ...
def read_body(path: str) -> bytes: ...
def list_matching(pattern: str) -> list[str]: ...
def delete(path: str) -> None: ...
def lock(path: str, owner: str) -> bool: ...
def release(path: str, owner: str) -> None: ...
def status(path: str) -> str: ...
def progress_append(path: str, entry: dict) -> None: ...
def progress_read(path: str) -> list[dict]: ...
```

Schemes never call storages directly. The mediator loads the storage module and invokes its functions with the scheme's
declared adapter config.

### Remote storages

`gh-pr`, `gh-issue`, etc. implement the same interface but resolve identifiers from the URI and ignore path templates.
Each remote storage declares which schemes it backs (typically one-to-one).

## Artifact = instance of (scheme, storage)

Every artifact is addressed by URI:

```text
<scheme>|<storage>/<path>
```

Examples:

- `document|file/docs/design/auth` — a local document at `docs/design/auth.md` + `docs/design/auth.content.toml`.
- `composed_of|file/docs--design--auth--template--design-document` — an edge artifact JSON at
  `artifact-edges/composed_of/docs--design--auth--template--design-document.json`.
- `pr|gh-pr/myorg/myrepo#42` — a GitHub PR.
- `authors|file/docs--design--auth` — metadata attaching an author list to a document.

## Mediator — `artifactlib.provider`

One dispatcher for every scheme:

1. Registry finds the `scheme.py` absolute path for the given scheme.
2. `load_scheme(path)` imports and returns the `SCHEME` object.
3. Parse stdin JSON → `subcommand.in_model.model_validate(...)`. `ValidationError` →
   `{"error":"schema-mismatch", "details":[…]}` exit 3.
4. Resolve the storage from the URI or saved preference (see backend resolution).
5. Load the storage module via `spec_from_file_location`.
6. Call the storage's read/write functions using the scheme's `[[storage]]` adapter config.
7. Build subcommand output. `subcommand.out_model.model_validate(...)` → stdout.

### `instantiate` (for `artifact-template`)

Owned by the mediator, not the storage. Orchestrates across schemes:

1. `get` the template artifact.
2. Build an ad-hoc pydantic model from `template.inputs` → validate user inputs.
3. Jinja-render `template.body` and every string in `output.create_input` + `output.path_template` against inputs.
4. Dispatch to the target scheme's `create` via `run-provider.py`.
5. Create a `composed_of` edge artifact → template.
6. If the target scheme declares a validating pydantic-schema, create a `depends_on` edge → that schema's artifact.

## Jinja convention

`artifactlib/render.py`:

- `is_jinja(path)` — True if `.jinja.` appears in the filename.
- `rendered_name(path)` — strips `.jinja` from the name. `design.jinja.md` → `design.md`.
- `render_file(template_path, inputs, out_path=None)` — jinja2 render; defaults to `rendered_name(...)`.
- `render_tree(value, inputs)` — recursive string rendering inside nested dict/list.

Environment: `StrictUndefined`; filters `slug`/`snake`/`kebab`/`json_escape`; no autoescape.

The `.jinja.` marker is solely a convention of the `artifact-template` scheme's file-storage adapter. Other schemes opt
in via their own `scheme.toml`.

## Backend resolution

URI-addressed operations dispatch directly to the named storage in the URI.

Scheme-addressed operations (`create`, `list`) resolve storage in this order:

1. Per-call `--storage <name>` override.
2. Saved user preference. `storage.<scheme>.default` in `$ARTIFACT_CONFIG_DIR/preferences/storage.json`.
3. Sole-storage short-circuit. If exactly one storage backs the scheme, use it and persist as the user's preference.
4. Prompt. The `/artifact` skill asks once, then persists.

No alphabetical tiebreak. No silent random selection.

## Local state

Platform-specific paths resolved by `artifactlib.xdg`:

### Preferences (config dir)

- Linux: `${XDG_CONFIG_HOME:-$HOME/.config}/artifact/preferences/`
- macOS: `~/Library/Application Support/artifact/preferences/`
- Windows: `%APPDATA%\artifact\preferences\`

### Graph / discovery cache (cache dir)

- Linux: `${XDG_CACHE_HOME:-$HOME/.cache}/artifact/`
- macOS: `~/Library/Caches/artifact/`
- Windows: `%LOCALAPPDATA%\artifact\cache\`

Rebuilt every session; never authoritative — the plugin files are.

### Ephemeral state (state dir)

Flocks and per-machine runtime state (e.g. the orchestrator lock owned by the `workflow` plugin):

- Linux: `${XDG_STATE_HOME:-$HOME/.local/state}/artifact/`
- macOS: `~/Library/Application Support/artifact/state/`
- Windows: `%LOCALAPPDATA%\artifact\state\`

## The graph

Every edge is an artifact of an edge-kind scheme. `graph.py` is a thin wrapper over `list` filtered by relation and
endpoint URIs. There are no separate graph files.

```bash
artifact graph expand --uri <U> [--relation R] [--depth N]
artifact graph find   --relation R --target <U>
```

Both commands list edge artifacts. No watchers, no auto-invalidation. When a schema artifact's content changes, the
caller decides what needs re-validation and walks the graph via `find --relation validates --target <scheme-URI>` to
enumerate dependents.

## Reserved suffixes (file storage)

File storage computes, at registry-load time, the set of path-template suffixes across all active
`[[storage]] name = "file"` entries. On `create`, file storage rejects any explicit path ending in one of those suffixes
unless the caller's scheme owns that suffix. Prevents user-created files masquerading as scheme artifacts.

## Dependencies

Python 3.11+. Pure-Python runtime deps:

- `pydantic >= 2` (schema validation)
- `tomlkit >= 0.13` (round-trippable TOML read/write)
- `jinja2 >= 3.1` (template rendering)

Dev deps: `pytest >= 8`, `pytest-xdist`.

External CLIs:

- `git` required.
- `gh` required only if `artifact-github` is used.

## Windows support

- Scripts invoked as `python3 <path>` (from `hooks.json` and all inter-script calls). No shebang-only invocations.
- All paths use `pathlib.Path`.
- `subprocess.run([...])` lists, never `shell=True`.
- Atomic writes via `Path.replace` (same-volume rename).
- Locks via `os.open(..., O_CREAT | O_EXCL)`.

CI matrix: `{ubuntu, macos, windows}`.

## Key invariants

1. **One type: artifact.** No sidecar conventions outside scheme `[[storage]]` declarations.
2. **Three kinds: vertex, edge, metadata.** Every scheme declares one.
3. **Schemes are Python + Pydantic.** Validation at mediator boundary.
4. **Storages are generic.** Scheme declares the encoding; storage implements the I/O.
5. **Graph is artifacts.** Edges and metadata are first-class; querying the graph is querying artifacts.
6. **URI format is `<scheme>|<storage>/<path>`.**
7. **Backend resolution never silently picks.** URI > override > preference > sole-storage > prompt.
8. **No in-repo runtime state.** All artifact state lives in storages. Machine-local files hold only cache, preferences,
   and ephemeral state.
9. **Plugin files are immutable to agents.** Changes come via override scope (workspace/user) or external PR.
10. **External mutations are first-class.** The next `get` returns updated state; the cache invalidates via
    `updated_at`.
11. **Python 3.11+, zero bash, cross-platform.**

## Dogfooding

Every dependent plugin is a reference plugin for this one. If any cross-plugin link needs a special case, the contract
is wrong — fix the contract, not the consumer.

- `workflow` depends on `artifact` and consumes its full surface.
- `artifact-github` and `artifact-documents` each ship schemes plus storages, following the contracts here.
- Future external consumers (Jira, Slack, Notion, …) plug in as storages against existing schemes.

## Design changelog

Append-only.

| Date       | Decision |
|------------|----------|
| 2026-04-18 | Extracted artifact primitive from the `workflow` plugin. Artifact owns provider + backend + artifact concepts, templates (as artifacts of scheme `artifact-template`), directories (as artifacts of scheme `directory`), and the typed-edge graph. Zero plugin dependencies. |
| 2026-04-18 | Provider/backend split. Provider defines an artifact *type* (scheme) via `schema.json`; backends store state in external systems and declare `backs_schemes` conformance. External consumers plug in as backends, not as new schemes. |
| 2026-04-18 | Templates are artifacts of scheme `artifact-template`. Single-file shape with YAML frontmatter (no directory bundles, no `instantiate.sh`). Composition via `composes:` (child templates) and `references:` (existing artifact URIs). |
| 2026-04-18 | Directories are artifacts of scheme `directory`. Directory templates are multi-file via tree specs in `composes`. |
| 2026-04-18 | Typed-edge graph is first-class. `composed_of` is the universal composition relation; other relations (`depends_on`, `closes`, `bundled_in`, `mentions`, `cites`, `supersedes`) are named in each scheme's schema. `scripts/graph.sh` exposes `expand / path / dot` for cross-provider traversal. |
| 2026-04-18 | Backend resolution is URI → override → saved preference → sole-backend short-circuit → prompt. No alphabetical fallback. |
| 2026-04-18 | Local state paths via `scripts/xdg.sh`: preferences in the user's config dir; graph cache + discovery registry in the user's cache dir; ephemeral state (flocks) in the state dir. Windows-compatible. |
| 2026-04-18 | Repository layout: `cjhowe-us/artifact-plugin` hosts this plugin plus `artifact-github` and `artifact-documents`. `cjhowe-us/workflow` keeps the workflow plugin. `cjhowe-us/marketplace` hosts only `marketplace.json` pointing at the plugin repos. |
| 2026-04-18 | **Full rewrite.** Three scheme kinds (vertex/edge/metadata). Schemes are Python + Pydantic modules, loaded via `spec_from_file_location` from `scheme.py` next to `scheme.toml`. Storages are generic read/write adapters (`storage.toml` + `storage.py`). `file` is a storage, not a scheme. `directory` scheme removed — filesystem hierarchy is structural only. No sidecars: vertex content, edges, and metadata are each first-class artifacts of their own schemes. Edges are artifacts of edge-kind schemes (`composed_of`, `depends_on`, `validates`, `references`, `mentions`, `supersedes`, `cites`, `bundled_in`, `closes`), stored as `.json` files in file storage via a shared factory. Template body files use `.jinja.*` naming for jinja2 detection. Renamed directories: `artifact-providers/` → `artifact-schemes/`, `artifact-backends/` → `artifact-storage/`. Manifests renamed: `manifest.json` + `schema.json` → `scheme.toml`; backend `manifest.json` → `storage.toml`. Dep floor: Python ≥ 3.11, `pydantic>=2`, `tomlkit>=0.13`, `jinja2>=3.1`. Bash and `jq` removed. Cross-platform (Linux + macOS + Windows). Knowledge-graph propagation is explicit + queryable via edge-artifact `list`; no auto-invalidation. |
