# user-config storage

Stores user-scoped configuration under `$ARTIFACT_CONFIG_DIR` (resolved per platform by `artifactlib.xdg`). Backs the
`preferences` scheme.

URI shape: `preferences|user-config/<id>` (e.g. `preferences|user-config/user`).
