# artifact-github

GitHub schemes + storages for the `cjhowe-us/artifact` ecosystem.

## Schemes (vertex-kind)

| Scheme      | URI shape                           | Notes                         |
|-------------|-------------------------------------|-------------------------------|
| `pr`        | `pr\|gh-pr/<owner>/<repo>/<n>`       | PR; assignee = owner lock     |
| `issue`     | `issue\|gh-issue/<owner>/<repo>/<n>` | Issue; assignee = owner lock  |
| `release`   | `release\|gh-release/<owner>/<repo>/<tag>`     | Release; no lock               |
| `milestone` | `milestone\|gh-milestone/<owner>/<repo>/<n>`   | Milestone; no lock             |
| `tag`       | `tag\|gh-tag/<owner>/<repo>/<tag>`             | Git tag; no lock               |
| `branch`    | `branch\|gh-branch/<owner>/<repo>/<branch>`    | Git branch; no lock            |
| `gist`      | `gist\|gh-gist/<gist-id>`                     | Gist; creator = owner          |

## Storages

One storage per scheme: `gh-pr`, `gh-issue`, `gh-release`, `gh-milestone`, `gh-tag`, `gh-branch`, `gh-gist`. Each shells
out to `gh` via `subprocess.run` (never `shell=True`).

## Install

```bash
claude plugin install artifact-github@cjhowe-us-marketplace
```

Requires `artifact >= 2.0.0` and the `gh` CLI (`gh auth login`).

## License

Apache-2.0.
