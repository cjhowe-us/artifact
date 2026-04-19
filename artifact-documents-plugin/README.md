# artifact-documents

Document scheme + storages + templates for the `cjhowe-us/artifact-plugin` ecosystem.

## Schemes

| Scheme     | Kind   | Notes                                                                              |
|------------|--------|------------------------------------------------------------------------------------|
| `document` | vertex | Markdown body + structured content (title, authors, status). Validated by pydantic. |

## Storages

| Storage               | Backs              | Notes                                           |
|-----------------------|--------------------|-------------------------------------------------|
| `document-confluence` | `document`         | Confluence Cloud REST v2. Env: `CONFLUENCE_BASE_URL`, `CONFLUENCE_USER`, `CONFLUENCE_TOKEN`. |

`document` can also be stored in core's `file` storage — that's the default for local authoring.

## Templates

Eight fill-in templates live under `artifact-templates/`. Each is a pair of files:

- `<name>.jinja.md` — body (jinja2).
- `<name>.content.toml` — template metadata (name, inputs, output path template, produced artifact content shape).

| Template name         | Produces                             |
|-----------------------|--------------------------------------|
| `design-document`     | Subsystem / feature design            |
| `implementation-plan` | Task breakdown for a planned change   |
| `review-note`         | Review findings + verdict             |
| `release-note`        | User-facing release summary           |
| `test-plan`           | Strategy + cases + oracles            |
| `requirement`         | Goal + acceptance criteria            |
| `user-story`          | As-a / I-want-to / So-that            |
| `triage-note`         | Observed / hypothesis / next-check    |

Customize: copy a pair to workspace scope (`$REPO/.claude/artifact-templates/`) or user scope to shadow the shipped
version. Shipped files are never edited in place.

## Install

```bash
claude plugin install artifact-documents@cjhowe-us-marketplace
```

Requires `artifact >= 2.0.0`.

## License

Apache-2.0.
