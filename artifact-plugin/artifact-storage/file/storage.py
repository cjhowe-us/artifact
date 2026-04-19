"""file storage — stores artifacts as files under the current git worktree.

Subcommand handlers (called by the mediator):

    cmd_create, cmd_get, cmd_update, cmd_delete, cmd_list,
    cmd_status, cmd_lock, cmd_release, cmd_progress

Adapter config shapes (from scheme.toml `[[storage]]`):

    # single-file shape (edges, metadata, vertices without a body)
    path_template = "artifact-edges/composed_of/{{ source|slug }}--{{ target|slug }}.json"
    serializer    = "json" | "toml"

    # body + content split (vertex schemes with a body)
    body_field            = "body"
    body_path_template    = "{{ id }}.md"
    content_path_template = "{{ id }}.content.toml"
    content_serializer    = "json" | "toml"

Path templates are jinja2 (filters: slug/snake/kebab/json_escape). Fields come
from the subcommand input model's `model_dump()`, plus `id` derived from the
URI if present.

The URI path (`<scheme>|file/<id>`) equals the rendered filesystem path with
the template's static suffix stripped.
"""

from __future__ import annotations

import contextlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

from artifactlib import render
from artifactlib import uri as uri_mod
from artifactlib.io import read_lock_owner, release_lock, try_take_lock
from artifactlib.toml import atomic_write as toml_write
from artifactlib.toml import load as toml_load
from pydantic import BaseModel

# ---------- helpers ----------------------------------------------------------


def _root() -> Path:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"], stderr=subprocess.DEVNULL
        )
        return Path(out.decode().strip())
    except (subprocess.CalledProcessError, FileNotFoundError):
        return Path.cwd()


def _render_path(template: str, fields: dict[str, Any]) -> str:
    return render.render_string(template, fields)


_CLOSING = re.compile(r"\}\}")


def _template_suffix(template: str) -> str:
    """Literal tail of the template (everything after the last ``}}``).

    For ``"{{ id }}.md"`` → ``".md"``. For a template with no jinja, returns
    the file's `Path.suffix`.
    """
    m = list(_CLOSING.finditer(template))
    if not m:
        return Path(template).suffix
    last = m[-1]
    return template[last.end() :]


def _fields_for_templating(
    input_model: BaseModel | dict[str, Any], uri_str: str | None
) -> dict[str, Any]:
    fields: dict[str, Any] = (
        dict(input_model.model_dump())
        if hasattr(input_model, "model_dump")
        else dict(input_model or {})
    )
    if uri_str:
        parsed = uri_mod.try_parse(uri_str)
        if parsed is not None:
            fields.setdefault("id", parsed.path)
    # Convenience: alias `path` → `id` when id is missing so schemes with a
    # `path` input field can use `{{ id }}` in templates without ceremony.
    if "id" not in fields and fields.get("path"):
        fields["id"] = fields["path"]
    return fields


def _adapter_shape(adapter: dict[str, Any]) -> str:
    if adapter.get("body_field") and adapter.get("body_path_template"):
        return "split"
    if adapter.get("path_template"):
        return "single"
    raise ValueError(
        "file-storage adapter must declare either path_template or body_path_template+body_field"
    )


def _strip_nones(value: Any) -> Any:
    """TOML has no null; drop None-valued keys/list entries before writing."""
    if isinstance(value, dict):
        return {k: _strip_nones(v) for k, v in value.items() if v is not None}
    if isinstance(value, list):
        return [_strip_nones(v) for v in value if v is not None]
    return value


def _serialize(data: dict[str, Any], path: Path, serializer: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if serializer == "json":
        path.write_text(json.dumps(data, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    elif serializer == "toml":
        toml_write(path, _strip_nones(data))
    else:
        raise ValueError(f"unknown serializer: {serializer}")


def _deserialize(path: Path, serializer: str) -> dict[str, Any]:
    if serializer == "json":
        return json.loads(path.read_text(encoding="utf-8"))
    if serializer == "toml":
        return toml_load(path)
    raise ValueError(f"unknown serializer: {serializer}")


def _id_from_uri(uri_str: str) -> str:
    parsed = uri_mod.try_parse(uri_str)
    if parsed is None:
        raise ValueError(f"bad uri: {uri_str}")
    return parsed.path


def _primary_path(adapter: dict[str, Any], art_id: str) -> str:
    """Return the relative path of the artifact's primary file (body for
    split shape, the single file for single shape).
    """
    shape = _adapter_shape(adapter)
    if shape == "split":
        return _render_path(adapter["body_path_template"], {"id": art_id})
    path_template = adapter["path_template"]
    return art_id + _template_suffix(path_template)


def _content_path(adapter: dict[str, Any], art_id: str) -> str | None:
    """Content-file path for split shape; None for single shape."""
    if _adapter_shape(adapter) != "split":
        return None
    content_template = adapter.get("content_path_template")
    if not content_template:
        return None
    return _render_path(content_template, {"id": art_id})


# ---------- subcommand handlers ---------------------------------------------


def cmd_create(*, scheme, adapter, input, uri):
    root = _root()
    fields = _fields_for_templating(input, uri)
    shape = _adapter_shape(adapter)

    body_field = adapter.get("body_field")
    content_dict = dict(fields)
    body_value: Any = None
    if body_field:
        body_value = content_dict.pop(body_field, None)
    for k in ("id", "path"):
        content_dict.pop(k, None)

    if shape == "split":
        body_template = adapter["body_path_template"]
        rel_body = _render_path(body_template, fields)
        body_path = root / rel_body
        body_path.parent.mkdir(parents=True, exist_ok=True)
        if body_value is None:
            body_value = ""
        if isinstance(body_value, bytes):
            body_path.write_bytes(body_value)
        else:
            body_path.write_text(body_value, encoding="utf-8")

        content_template = adapter.get("content_path_template")
        if content_template and content_dict:
            content_path = root / _render_path(content_template, fields)
            _serialize(content_dict, content_path, adapter.get("content_serializer") or "toml")

        # Split-shape URI path = input's `id` (required). Get re-renders both templates.
        art_id = fields.get("id")
        if not art_id:
            raise ValueError("file-storage split shape requires an `id` field in the create input")
    else:
        path_template = adapter["path_template"]
        rel = _render_path(path_template, fields)
        _serialize(content_dict, root / rel, adapter.get("serializer") or "json")
        # Single-shape URI path = full relative path minus static suffix.
        art_id = rel.removesuffix(_template_suffix(path_template))

    return {"uri": f"{scheme.name}|file/{art_id}", "created": True}


def cmd_get(*, scheme, adapter, input, uri):
    root = _root()
    art_id = _id_from_uri(uri) if uri else _id_from_uri(input.uri)

    shape = _adapter_shape(adapter)
    content: dict[str, Any] = {}
    if shape == "split":
        body_template = adapter["body_path_template"]
        fields = {"id": art_id}
        body_path = root / _render_path(body_template, fields)
        body_value = body_path.read_text(encoding="utf-8") if body_path.is_file() else ""

        content_template = adapter.get("content_path_template")
        if content_template:
            content_path = root / _render_path(content_template, fields)
            if content_path.is_file():
                content = _deserialize(content_path, adapter.get("content_serializer") or "toml")
        body_field = adapter.get("body_field")
        if body_field:
            content = {**content, body_field: body_value}
    else:
        path_template = adapter["path_template"]
        # Single shape: art_id is the full path minus static suffix.
        path = root / (art_id + _template_suffix(path_template))
        if path.is_file():
            content = _deserialize(path, adapter.get("serializer") or "json")

    validated = scheme.content_model.model_validate(content)
    return {"uri": uri or f"{scheme.name}|file/{art_id}", "content": validated.model_dump()}


def cmd_delete(*, scheme, adapter, input, uri):
    root = _root()
    art_id = _id_from_uri(uri) if uri else _id_from_uri(input.uri)
    body_path = root / _primary_path(adapter, art_id)
    if body_path.exists():
        body_path.unlink()
    cp = _content_path(adapter, art_id)
    if cp:
        content_path = root / cp
        if content_path.exists():
            content_path.unlink()
    return {"uri": uri or f"{scheme.name}|file/{art_id}", "deleted": True}


def cmd_status(*, scheme, adapter, input, uri):
    root = _root()
    art_id = _id_from_uri(uri) if uri else _id_from_uri(getattr(input, "uri", ""))
    path = root / _primary_path(adapter, art_id)
    return {
        "uri": uri or f"{scheme.name}|file/{art_id}",
        "status": "complete" if path.is_file() else "unknown",
    }


def cmd_list(*, scheme, adapter, input, uri):
    """Enumerate by glob on the template's literal prefix, filter post-hoc."""
    root = _root()
    shape = _adapter_shape(adapter)
    template = adapter["body_path_template"] if shape == "split" else adapter["path_template"]
    prefix_end = template.find("{{")
    prefix = template[:prefix_end] if prefix_end != -1 else template
    suffix = _template_suffix(template)

    prefix_path = root / prefix.rstrip("/")
    search_root = prefix_path if prefix_path.exists() else root

    filter_source = getattr(input, "source", None)
    filter_target = getattr(input, "target", None)

    entries: list[dict[str, Any]] = []
    if not search_root.exists():
        return {"entries": entries}

    for p in search_root.rglob("*"):
        if not p.is_file():
            continue
        if suffix and not p.name.endswith(suffix):
            continue
        try:
            rel = p.relative_to(root)
        except ValueError:
            continue

        content: dict[str, Any] = {}
        if shape == "split":
            # Split shape: we don't know the input's id from the body path
            # alone; skip listing for split shape in this baseline. Schemes
            # wanting list for split-shape artifacts should override via a
            # scheme-specific cmd_list.
            continue
        art_id = str(rel).removesuffix(suffix)
        uri_str = f"{scheme.name}|file/{art_id}"
        with contextlib.suppress(Exception):
            content = _deserialize(p, adapter.get("serializer") or "json")

        if filter_source is not None and content.get("source") != filter_source:
            continue
        if filter_target is not None and content.get("target") != filter_target:
            continue

        entries.append({"uri": uri_str, "kind": scheme.kind.value, "content": content})

    return {"entries": entries}


def _lock_path_for(root: Path, adapter: dict[str, Any], art_id: str) -> Path:
    target = root / _primary_path(adapter, art_id)
    return target.with_suffix(target.suffix + ".lock")


def cmd_lock(*, scheme, adapter, input, uri):
    root = _root()
    art_id = _id_from_uri(uri) if uri else _id_from_uri(input.uri)
    lock_path = _lock_path_for(root, adapter, art_id)
    owner = getattr(input, "owner", "") or ""
    if getattr(input, "check", False):
        cur = read_lock_owner(lock_path)
        held = bool(cur) and (cur == owner if owner else True)
        return {"held": held, "current_owner": cur}
    ok, cur = try_take_lock(lock_path, owner)
    return {"held": ok, "current_owner": cur}


def cmd_release(*, scheme, adapter, input, uri):
    root = _root()
    art_id = _id_from_uri(uri) if uri else _id_from_uri(input.uri)
    release_lock(_lock_path_for(root, adapter, art_id), getattr(input, "owner", "") or "")
    return {"released": True}


def cmd_progress(*, scheme, adapter, input, uri):
    root = _root()
    art_id = _id_from_uri(uri) if uri else _id_from_uri(input.uri)
    target = root / _primary_path(adapter, art_id)
    log = target.with_suffix(target.suffix + ".progress.jsonl")
    entry = getattr(input, "append", None)
    if entry is None:
        entries = []
        if log.is_file():
            for line in log.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    entries.append(json.loads(line))
        return {"entries": entries}
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    return {"appended": True}
