"""session-memory storage — ephemeral per-process artifacts.

Kept simple: in-process dict keyed by URI. Survives only the current process.
Useful for transient `conversation` artifacts and tests.
"""

from __future__ import annotations

from typing import Any

from artifactlib import uri as uri_mod


_STORE: dict[str, dict[str, Any]] = {}


def _id_from_uri(uri_str: str) -> str:
    parsed = uri_mod.try_parse(uri_str)
    return parsed.path if parsed else uri_str


def cmd_create(*, scheme, adapter, input, uri):
    fields = input.model_dump()
    art_id = fields.get("id") or fields.get("path") or fields.get("name")
    if not art_id:
        raise ValueError("session-memory: create requires id/path/name")
    content = {k: v for k, v in fields.items() if k not in {"id", "path"}}
    scheme.content_model.model_validate(content)
    key = f"{scheme.name}|session-memory/{art_id}"
    _STORE[key] = content
    return {"uri": key, "created": True}


def cmd_get(*, scheme, adapter, input, uri):
    art_id = _id_from_uri(uri) if uri else getattr(input, "uri", "")
    key = f"{scheme.name}|session-memory/{_id_from_uri(art_id) if not isinstance(art_id, str) else art_id}"
    content = _STORE.get(key, {})
    validated = scheme.content_model.model_validate(content)
    return {"uri": uri or key, "content": validated.model_dump()}


def cmd_delete(*, scheme, adapter, input, uri):
    key = uri or f"{scheme.name}|session-memory/{input.uri}"
    _STORE.pop(key, None)
    return {"uri": key, "deleted": True}


def cmd_status(*, scheme, adapter, input, uri):
    key = uri or f"{scheme.name}|session-memory/{getattr(input, 'uri', '')}"
    return {"uri": key, "status": "complete" if key in _STORE else "unknown"}


def cmd_list(*, scheme, adapter, input, uri):
    entries = [
        {"uri": k, "kind": scheme.kind.value}
        for k in _STORE
        if k.startswith(f"{scheme.name}|session-memory/")
    ]
    return {"entries": entries}
