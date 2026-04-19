"""Shared storage conformance checks.

Used by tests to verify that a storage module correctly implements the
contract for a given scheme. A storage passes conformance if:

- It exposes ``cmd_<subcommand>`` for every required subcommand of the scheme.
- Round-trip (create → get) returns equal content.
- Delete (if declared) is idempotent.
- List returns well-formed entries.
"""

from __future__ import annotations

from typing import Any

from .scheme import Scheme


def check_subcommand_coverage(scheme: Scheme, storage_module: Any) -> list[str]:
    """Return a list of missing cmd_<sub> handlers for required subcommands."""
    missing = []
    for name, sub in scheme.subcommands.items():
        if not sub.required:
            continue
        if not callable(getattr(storage_module, f"cmd_{name}", None)):
            missing.append(name)
    return missing


def round_trip_create_get(
    scheme: Scheme,
    storage_module: Any,
    adapter: dict[str, Any],
    create_input: dict[str, Any],
) -> dict[str, Any]:
    """Invoke create then get; return the get output dict."""
    create_sub = scheme.subcommands["create"]
    create_in = create_sub.in_model.model_validate(create_input)
    create_out = storage_module.cmd_create(
        scheme=scheme, adapter=adapter, input=create_in, uri=None
    )
    if hasattr(create_out, "model_dump"):
        create_out = create_out.model_dump()
    uri = create_out["uri"]

    get_sub = scheme.subcommands["get"]
    get_in = get_sub.in_model.model_validate({"uri": uri})
    get_out = storage_module.cmd_get(scheme=scheme, adapter=adapter, input=get_in, uri=uri)
    if hasattr(get_out, "model_dump"):
        get_out = get_out.model_dump()
    return get_out
