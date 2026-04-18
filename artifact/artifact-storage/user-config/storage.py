"""user-config storage — stores preferences under $ARTIFACT_CONFIG_DIR."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from artifactlib import render, xdg
from artifactlib import uri as uri_mod


def _root() -> Path:
    return xdg.resolve().config


def _path_for(adapter: dict[str, Any], fields: dict[str, Any]) -> Path:
    tmpl = adapter.get("path_template") or "{{ id }}.json"
    return _root() / render.render_string(tmpl, fields)


def _id_from_uri(uri_str: str) -> str:
    parsed = uri_mod.try_parse(uri_str)
    return parsed.path if parsed else uri_str


def cmd_create(*, scheme, adapter, input, uri):
    fields = input.model_dump()
    if "id" not in fields:
        fields["id"] = fields.get("path") or fields.get("name") or "user"
    path = _path_for(adapter, fields)
    path.parent.mkdir(parents=True, exist_ok=True)
    content = {k: v for k, v in fields.items() if k not in {"id", "path"}}
    serializer = adapter.get("serializer") or "json"
    if serializer == "json":
        path.write_text(json.dumps(content, indent=2) + "\n", encoding="utf-8")
    else:
        from artifactlib.toml import atomic_write

        atomic_write(path, content)
    return {"uri": f"{scheme.name}|user-config/{fields['id']}", "created": True}


def cmd_get(*, scheme, adapter, input, uri):
    art_id = _id_from_uri(uri) if uri else getattr(input, "uri", "")
    if not isinstance(art_id, str):
        art_id = _id_from_uri(art_id)
    path = _path_for(adapter, {"id": art_id})
    if not path.is_file():
        content = {}
    else:
        serializer = adapter.get("serializer") or "json"
        if serializer == "json":
            content = json.loads(path.read_text(encoding="utf-8"))
        else:
            from artifactlib.toml import load

            content = load(path)
    validated = scheme.content_model.model_validate(content)
    return {"uri": uri or f"{scheme.name}|user-config/{art_id}", "content": validated.model_dump()}


def cmd_delete(*, scheme, adapter, input, uri):
    art_id = _id_from_uri(uri) if uri else input.uri
    if not isinstance(art_id, str):
        art_id = _id_from_uri(art_id)
    path = _path_for(adapter, {"id": art_id})
    if path.exists():
        path.unlink()
    return {"uri": uri or f"{scheme.name}|user-config/{art_id}", "deleted": True}


def cmd_status(*, scheme, adapter, input, uri):
    art_id = _id_from_uri(uri) if uri else getattr(input, "uri", "")
    if not isinstance(art_id, str):
        art_id = _id_from_uri(art_id)
    path = _path_for(adapter, {"id": art_id})
    return {
        "uri": uri or f"{scheme.name}|user-config/{art_id}",
        "status": "complete" if path.is_file() else "unknown",
    }


def cmd_list(*, scheme, adapter, input, uri):
    root = _root()
    entries = []
    if root.is_dir():
        for p in sorted(root.rglob("*")):
            if not p.is_file():
                continue
            rel = p.relative_to(root)
            art_id = str(rel).split(".", 1)[0]
            entries.append({"uri": f"{scheme.name}|user-config/{art_id}", "kind": scheme.kind.value})
    return {"entries": entries}
