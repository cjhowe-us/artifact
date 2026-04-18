# file storage

Stores artifacts under the current git worktree (falling back to `$PWD` if not in a git repo). Supports any scheme whose
`[[storage]]` adapter declares one of these shapes:

**Body + content split** (vertex schemes with a body file):

```toml
[[storage]]
name                  = "file"
body_field            = "body"
body_path_template    = "{{ id }}.md"
content_path_template = "{{ id }}.content.toml"
content_serializer    = "toml"     # or "json"
```

**Single-file content** (edges, metadata, vertices without a body):

```toml
[[storage]]
name          = "file"
path_template = "artifact-edges/composed_of/{{ source | slug }}--{{ target | slug }}.json"
serializer    = "json"     # or "toml"
```

Path templates are jinja2 — filters `slug`, `snake`, `kebab`, `json_escape` are available. Fields come from the
subcommand input model via `model_dump()`.

## URI shape

`<scheme>|file/<id>` — `<id>` is the scheme's primary identifier (typically the filesystem path relative to the worktree
root, minus extensions computed from the path template).

## Capabilities

- `supports_locking = true` — soft locks via `<path>.lock`.
- `supports_listing = true` — `list` enumerates by glob.
- `supports_watching = false` — no change notifications.
