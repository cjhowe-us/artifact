# extension-scaffold

Scaffolds a sibling Claude Code plugin that extends the `artifact` ecosystem. The target plugin can contribute any mix
of:

- artifact schemes (under `artifact-schemes/<name>/{scheme.toml,scheme.py,README.md}`)
- artifact storages (under `artifact-storage/<name>/{storage.toml,storage.py,README.md}`)
- artifact templates (under `artifact-templates/<name>.jinja.<ext>` + `<name>.content.toml`)

## Inputs

- `name` — plugin name (kebab-case), becomes directory name.
- `path` — parent directory to create it under.
- `description` — one-line plugin description for `plugin.json` and README.
- `contributes` — one or more of `schemes`, `storages`, `templates`.
- `depends_on` — other plugins in the marketplace this one needs (`artifact`, `artifact-github`,
  `artifact-documents`,...). `artifact` is always required as the runtime.

## Output

```text
<path>/<name>/
  .claude-plugin/plugin.json
  pyproject.toml
  README.md
  artifact-schemes/              (if contributes schemes)
  artifact-storage/              (if contributes storages)
  artifact-templates/            (if contributes templates)
  tests/                         (pytest; inherits artifactlib on PYTHONPATH)
```

`pyproject.toml` declares `artifact` as a dependency. `tests/` ships `conftest.py` that adds the core plugin's
`scripts/` to `sys.path` so `from artifactlib import …` resolves.

## Scheme authoring

1. Pick a unique scheme name + kind.
2. Scaffold `artifact-schemes/<name>/scheme.toml` declaring `name`, `kind`, compatible storages in `[[storage]]` with
   per-adapter config.
3. Write `scheme.py` with Pydantic content model + subcommand in/out models + `SCHEME`.
4. Edge schemes: one-liner via `artifactlib.edges.make_edge_scheme(<relation>)`.
5. Run `pytest` — the suite auto-loads schemes found via discovery.

## Storage authoring

1. Pick a unique storage name.
2. Scaffold `artifact-storage/<name>/storage.toml` with `backs_schemes` and `[capabilities]`.
3. Implement `storage.py` with `cmd_create`, `cmd_get`, `cmd_list`, `cmd_status`, and any other subcommands the scheme
   declares as required.
4. Each handler's signature: `cmd_<sub>(*, scheme, adapter, input, uri) -> dict`.
5. Run the shared conformance suite (`artifactlib.conformance.check_subcommand_coverage`).

## Template authoring

1. Create `artifact-templates/<name>.jinja.<ext>` — jinja2 body (ext typically `md`).
2. Create `artifact-templates/<name>.content.toml` with `name`, `target_scheme`, `inputs`, `output.path_template`,
   `output.create_input`.
3. Discovery picks up the pair automatically.

## Registration

After scaffold, list the new plugin in the marketplace's `.claude-plugin/marketplace.json`. The scaffold skill prints
the exact snippet.

## Conformance

Scaffolded plugins pass the pytest suite out of the box — empty contribution sets are valid. CI should run
`pytest artifact-plugin/tests/ artifact-documents-plugin/tests/ artifact-github-plugin/tests/` across the OS matrix
`{ubuntu, macos, windows}`.
