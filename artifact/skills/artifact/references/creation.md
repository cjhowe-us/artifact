# creation

How to author a new template, scheme, or storage. Templates are the common case; schemes and storages are rarer and
follow the same scope rules.

## Template authoring

A template is a pair of files in the same `artifact-templates/` directory:

```text
<name>.jinja.md                   # jinja2 body — rendered into the produced artifact
<name>.content.toml               # template metadata (inputs, output mapping)
```

The `.content.toml`:

```toml
name             = "design-document"
target_scheme    = "document"
description      = "Fill-in markdown design doc."
contract_version = 1

[[inputs]]
name = "title"
type = "string"
required = true

[[inputs]]
name = "author"
type = "string"
required = true

[output]
path_template = "docs/design/{{ title | slug }}"

[output.create_input]
title   = "{{ title }}"
authors = ["{{ author }}"]
status  = "draft"
```

Instantiate via the mediator:

```bash
echo '{"uri":"artifact-template|file/design-document","inputs":{"title":"Auth rework","author":"christian"},"target_storage":"file"}' | \
  python3 <plugin>/scripts/run-provider.py 'artifact-template|file/design-document' instantiate
```

Produces `docs/design/auth-rework.md` + `docs/design/auth-rework.content.toml` + a `composed_of` edge artifact linking
the document to its template.

## Scope resolution

Writes go to one of three writable scopes (plugin scope is never a write target):

| Scope     | Target path                                                                 |
|-----------|-----------------------------------------------------------------------------|
| override  | `$CWD/.artifact-override/artifact-templates/<name>.{jinja.md,content.toml}` |
| workspace | `$REPO/.claude/artifact-templates/<name>.{jinja.md,content.toml}`           |
| user      | `$HOME/.claude/artifact-templates/<name>.{jinja.md,content.toml}`           |

Higher-precedence scopes shadow lower ones with the same name (override > workspace > user > plugin).

## Write refusal under plugin roots

All writes go through a guard that rejects any target under an installed plugin's root. Plugin files are immutable to
agents; change them by opening a PR to the plugin repo.

## Validation

Before write, the authoring flow runs:

1. `toml.load` on `<name>.content.toml` — must parse.
2. Pydantic validation of the content against the `artifact-template` scheme's content model (inputs list, output
   mapping, etc.).
3. Jinja2 `env().parse()` on the body — must compile.

Failures surface as blockers; the meta-workflow can prompt for corrections.

## Scheme / storage authoring

See `extension-scaffold.md`. Both live at the plugin root (not inside `skills/`) and are discovered by
`scripts/discover.py`:

```text
artifact-schemes/<name>/{scheme.toml, scheme.py, README.md}
artifact-storage/<name>/{storage.toml, storage.py, README.md}
```

Scheme authors write Pydantic models for each subcommand; storage authors write `cmd_<subcommand>` functions.
