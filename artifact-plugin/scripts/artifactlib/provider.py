"""Generic scheme mediator.

Validates subcommand inputs/outputs via the scheme's Pydantic models, resolves
storage, loads the storage module, and dispatches. One code path for every
scheme.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import uuid
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from . import registry, toml, uri
from .scheme import Scheme, load_scheme
from .validate import SCHEMA_MISMATCH_EXIT, emit_schema_mismatch


class MediatorError(RuntimeError):
    pass


def _load_storage_module(storage_name: str) -> Any:
    script = registry.storage_script(storage_name)
    module_name = f"_artifact_storage_{uuid.uuid4().hex}"
    spec = importlib.util.spec_from_file_location(module_name, str(script.resolve()))
    if spec is None or spec.loader is None:
        raise MediatorError(f"cannot load storage module at {script}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _load_scheme_for(scheme_name: str) -> Scheme:
    script = registry.scheme_script(scheme_name)
    toml_path = script.parent / "scheme.toml"
    toml_data = toml.load(toml_path) if toml_path.is_file() else {}
    return load_scheme(script, toml_data)


def dispatch(
    *,
    scheme_name: str,
    subcommand: str,
    payload: dict[str, Any],
    uri_str: str | None,
    storage_override: str | None,
) -> dict[str, Any]:
    """Run `subcommand` for `scheme_name` with `payload`. Returns output dict.

    Raises MediatorError for non-validation failures. Pydantic validation
    failures are caught by the caller (CLI entry) and converted to schema-mismatch.
    """
    scheme = _load_scheme_for(scheme_name)
    sub = scheme.subcommands.get(subcommand)
    if sub is None:
        raise MediatorError(f"scheme={scheme_name} has no subcommand={subcommand}")

    validated = sub.in_model.model_validate(payload)

    # Special cross-scheme subcommand: artifact-template.instantiate.
    if scheme_name == "artifact-template" and subcommand == "instantiate":
        result = _instantiate(scheme, validated, uri_str, storage_override)
        return sub.out_model.model_validate(result).model_dump()

    storage_name = (
        uri.backend_of(uri_str)
        if uri_str
        else registry.resolve_storage(scheme_name, storage_override)
    )
    if not storage_name:
        raise MediatorError(f"cannot resolve storage for scheme={scheme_name}")

    adapter_cfg = registry.scheme_adapter_config(scheme_name, storage_name)
    storage_module = _load_storage_module(storage_name)

    handler = getattr(storage_module, f"cmd_{subcommand}", None)
    if handler is None:
        raise MediatorError(f"storage={storage_name} has no handler cmd_{subcommand}")

    result = handler(
        scheme=scheme,
        adapter=adapter_cfg,
        input=validated,
        uri=uri_str,
    )
    if not isinstance(result, dict):
        result = result.model_dump() if hasattr(result, "model_dump") else dict(result)
    return sub.out_model.model_validate(result).model_dump()


def _load_shipped_template(uri_str: str) -> dict[str, Any] | None:
    """Load an artifact-template discovered by registry (shipped by a plugin).

    Returns the template as a dict (matching ArtifactTemplate content shape)
    or None if no registry entry matches. Shipped templates live in plugin
    directories (outside the user's worktree); `file` storage's `get` would
    miss them.
    """
    import tomllib

    try:
        art_id = uri.parse(uri_str).path
    except ValueError:
        return None
    try:
        reg = registry.load_registry()
    except registry.RegistryMissing:
        return None
    for entry in reg.get("entries", []):
        if entry.get("entry_type") != "artifact-template":
            continue
        if entry.get("name") != art_id:
            continue
        body_path = Path(entry["path"])
        content_path = Path(entry.get("content_path") or "")
        body = body_path.read_text(encoding="utf-8") if body_path.is_file() else ""
        content: dict[str, Any] = {}
        if content_path.is_file():
            with content_path.open("rb") as f:
                content = tomllib.load(f)
        return {**content, "body": body}
    return None


def _instantiate(
    template_scheme: Any,
    validated_input: Any,
    uri_str: str | None,
    storage_override: str | None,
) -> dict[str, Any]:
    """Orchestrate template instantiation across schemes."""
    from pydantic import create_model

    from . import render

    template_uri = getattr(validated_input, "uri", None) or uri_str
    if not template_uri:
        raise MediatorError("instantiate requires --uri for the template")

    # 1. Load template content. Try the shipped-template registry first
    #    (plugins ship templates outside the user's worktree), then fall back
    #    to the regular `get` path for user-authored templates.
    template = _load_shipped_template(template_uri)
    if template is None:
        template_get = dispatch(
            scheme_name="artifact-template",
            subcommand="get",
            payload={"uri": template_uri},
            uri_str=template_uri,
            storage_override=None,
        )
        template = template_get["content"]

    # 2. Validate user inputs against declared template.inputs.
    user_inputs = validated_input.inputs if hasattr(validated_input, "inputs") else {}
    input_fields: dict[str, Any] = {}
    for spec in template.get("inputs", []):
        name = spec["name"]
        py_type = str  # all inputs treated as str for now
        required = spec.get("required", False)
        default = spec.get("default", ... if required else "")
        input_fields[name] = (py_type, default)
    InputsModel = create_model("TemplateUserInputs", **input_fields)
    validated_inputs = InputsModel.model_validate(user_inputs).model_dump()

    # 3. Render body.
    rendered_body = render.render_string(template.get("body", ""), validated_inputs)

    # 4. Render produced id (path_template).
    output = template.get("output", {})
    produced_id = render.render_string(output.get("path_template", ""), validated_inputs)

    # 5. Render create_input (recursive string render).
    create_input = render.render_tree(output.get("create_input", {}), validated_inputs)

    # 6. Build target-scheme create payload and dispatch.
    target_scheme = template["target_scheme"]
    target_payload: dict[str, Any] = {"id": produced_id, **create_input}
    # If target has a body_field, attach rendered body.
    target_scheme_obj = _load_scheme_for(target_scheme)
    create_sub = target_scheme_obj.subcommands.get("create")
    if create_sub is not None:
        create_model_cls = create_sub.in_model
        if "body" in create_model_cls.model_fields:
            target_payload["body"] = rendered_body

    target_storage = getattr(validated_input, "target_storage", None) or storage_override

    produced_out = dispatch(
        scheme_name=target_scheme,
        subcommand="create",
        payload=target_payload,
        uri_str=None,
        storage_override=target_storage,
    )
    produced_uri = produced_out["uri"]

    # 7. Create composed_of edge from produced → template.
    edge_uris: list[str] = []
    edge_out = dispatch(
        scheme_name="composed_of",
        subcommand="create",
        payload={"source": produced_uri, "target": template_uri},
        uri_str=None,
        storage_override="file",
    )
    edge_uris.append(edge_out["uri"])

    return {"produced_uri": produced_uri, "edges": edge_uris}


def main_cli(argv: list[str]) -> int:
    """Stdin JSON in (payload); stdout JSON out.

    argv shape: [scheme, subcommand] [--uri <u>] [--storage <s>]
    """
    if len(argv) < 2:
        sys.stderr.write('{"error":"scheme and subcommand required"}\n')
        return 2

    scheme_name = argv[0]
    subcommand = argv[1]
    rest = argv[2:]

    uri_str: str | None = None
    storage_override: str | None = None
    i = 0
    while i < len(rest):
        tok = rest[i]
        if tok == "--uri":
            uri_str = rest[i + 1]
            i += 2
        elif tok == "--storage":
            storage_override = rest[i + 1]
            i += 2
        else:
            i += 1

    raw = sys.stdin.read()
    payload = json.loads(raw) if raw.strip() else {}

    try:
        out = dispatch(
            scheme_name=scheme_name,
            subcommand=subcommand,
            payload=payload,
            uri_str=uri_str,
            storage_override=storage_override,
        )
    except ValidationError as exc:
        emit_schema_mismatch(exc)
        return SCHEMA_MISMATCH_EXIT
    except (
        MediatorError,
        registry.NoStorageForScheme,
        registry.AmbiguousStorage,
        registry.RegistryMissing,
    ) as exc:
        sys.stdout.write(json.dumps({"error": str(exc)}) + "\n")
        return 2

    sys.stdout.write(json.dumps(out) + "\n")
    return 0
