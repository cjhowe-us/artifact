# artifact-template

Vertex scheme. Templates that produce an artifact of some target scheme.

Templates carry a jinja2 body (file with `.jinja.<ext>` naming), declared inputs (pydantic-validated), and an output
mapping that drives `instantiate`.

## URI

`artifact-template|file/<id>`

## Subcommands

- `create` — write the template pair.
- `get` — read the template.
- `instantiate` — validate inputs, jinja-render body and `output.create_input`, dispatch to target scheme's `create`,
  record `composed_of` and `depends_on` edges.
- `status`, `delete`, `list`.

See [`scheme.py`](./scheme.py) for pydantic models.
