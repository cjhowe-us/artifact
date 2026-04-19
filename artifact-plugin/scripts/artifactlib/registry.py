"""Discovery registry + storage resolver.

The registry is rebuilt by `discover.py` at session start. It records:

- ``artifact-scheme`` entries (one per ``artifact-schemes/<n>/scheme.toml``)
- ``artifact-storage`` entries (one per ``artifact-storage/<n>/storage.toml``)
- ``artifact-template`` entries (one per body file in ``artifact-templates/``)

Resolution order for scheme-addressed ops:

1. Per-call ``--storage`` override.
2. Saved preference in ``$ARTIFACT_CONFIG_DIR/preferences/storage.json``.
3. Sole-storage short-circuit; persisted.
4. Error (``AmbiguousStorage``) or missing (``NoStorageForScheme``).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from . import xdg


class RegistryMissing(RuntimeError):
    pass


class NoStorageForScheme(RuntimeError):
    pass


class AmbiguousStorage(RuntimeError):
    def __init__(self, scheme: str, candidates: list[str]) -> None:
        self.scheme = scheme
        self.candidates = candidates
        super().__init__(
            f"multiple storages for scheme={scheme} ({', '.join(candidates)}). "
            f"Pass --storage <name>, or save a default via preferences."
        )


def registry_path() -> Path:
    return xdg.resolve().cache / "registry.json"


def preferences_path() -> Path:
    return xdg.resolve().config / "preferences" / "storage.json"


def load_registry() -> dict[str, Any]:
    p = registry_path()
    if not p.is_file():
        raise RegistryMissing(f"registry not found: {p}")
    return json.loads(p.read_text())


def scheme_entries(registry: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    registry = registry or load_registry()
    return [e for e in registry.get("entries", []) if e.get("entry_type") == "artifact-scheme"]


def storage_entries(registry: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    registry = registry or load_registry()
    return [e for e in registry.get("entries", []) if e.get("entry_type") == "artifact-storage"]


def find_scheme(scheme_name: str, registry: dict[str, Any] | None = None) -> dict[str, Any] | None:
    for entry in scheme_entries(registry):
        if entry.get("name") == scheme_name:
            return entry
    return None


def find_storage(storage_name: str, registry: dict[str, Any] | None = None) -> dict[str, Any] | None:
    for entry in storage_entries(registry):
        if entry.get("name") == storage_name:
            return entry
    return None


def storages_for_scheme(scheme_name: str, registry: dict[str, Any] | None = None) -> list[str]:
    """Return storage names that back `scheme_name`.

    Authoritative source is each scheme's `[[storage]]` entries (recorded in
    the scheme registry entry's `storages` field). We also cross-check with
    each storage's `backs_schemes` list, warning via registry `warnings` if
    there's a mismatch (done by discover.py, not here).
    """
    entry = find_scheme(scheme_name, registry)
    if entry is None:
        return []
    return [s.get("name") for s in (entry.get("storages") or []) if s.get("name")]


def _read_pref(scheme: str) -> str | None:
    p = preferences_path()
    if not p.is_file():
        return None
    try:
        data = json.loads(p.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    val = data.get(scheme, {}).get("default")
    return val if isinstance(val, str) and val else None


def _write_pref(scheme: str, storage: str) -> None:
    p = preferences_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    current: dict[str, Any] = {}
    if p.is_file():
        try:
            current = json.loads(p.read_text())
        except (OSError, json.JSONDecodeError):
            current = {}
    current.setdefault(scheme, {})["default"] = storage
    p.write_text(json.dumps(current, indent=2) + "\n")


def resolve_storage(scheme: str, override: str | None = None) -> str:
    if override:
        return override
    pref = _read_pref(scheme)
    if pref:
        return pref
    candidates = storages_for_scheme(scheme)
    if len(candidates) == 1:
        only = candidates[0]
        _write_pref(scheme, only)
        return only
    if not candidates:
        raise NoStorageForScheme(f"no storage installed for scheme={scheme}")
    raise AmbiguousStorage(scheme, candidates)


def storage_script(storage_name: str) -> Path:
    """Return the absolute path to a storage's `storage.py`."""
    entry = find_storage(storage_name)
    if entry is None:
        raise RuntimeError(f"storage not found in registry: {storage_name}")
    toml_path = Path(entry["path"])
    script = toml_path.parent / "storage.py"
    if not script.is_file():
        raise RuntimeError(f"storage missing storage.py: {script}")
    return script


def scheme_script(scheme_name: str) -> Path:
    """Return the absolute path to a scheme's `scheme.py`."""
    entry = find_scheme(scheme_name)
    if entry is None:
        raise RuntimeError(f"scheme not found in registry: {scheme_name}")
    toml_path = Path(entry["path"])
    script = toml_path.parent / "scheme.py"
    if not script.is_file():
        raise RuntimeError(f"scheme missing scheme.py: {script}")
    return script


def scheme_adapter_config(scheme_name: str, storage_name: str) -> dict[str, Any]:
    """Return the `[[storage]]` entry in scheme.toml for `storage_name`."""
    entry = find_scheme(scheme_name)
    if entry is None:
        raise RuntimeError(f"scheme not found in registry: {scheme_name}")
    for s in entry.get("storages") or []:
        if s.get("name") == storage_name:
            return {k: v for k, v in s.items() if k != "name"}
    raise RuntimeError(f"scheme={scheme_name} has no [[storage]] entry for {storage_name}")


def plugin_scripts_path_for(entry_path: Path) -> Path | None:
    """Return the `<plugin>/scripts` directory that owns a registry entry path.

    Used by run-provider.py to set PYTHONPATH so subprocess scheme/storage
    scripts can `from artifactlib import …`.
    """
    p = entry_path.resolve()
    for parent in p.parents:
        scripts = parent / "scripts"
        if scripts.is_dir() and (scripts / "artifactlib").is_dir():
            return scripts
    return None
