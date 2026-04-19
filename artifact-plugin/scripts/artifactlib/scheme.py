"""Scheme + Subcommand dataclasses; loader that imports scheme.py by path."""

from __future__ import annotations

import importlib.util
import sys
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel

from .kinds import Kind


@dataclass(frozen=True)
class Subcommand:
    """One subcommand's in/out pydantic models."""

    in_model: type[BaseModel]
    out_model: type[BaseModel]
    required: bool = False


@dataclass(frozen=True)
class StorageAdapter:
    """Scheme's declared config for one compatible storage.

    Comes straight from a `[[storage]]` entry in scheme.toml. `name` is the
    storage's name; the rest is passed to the storage module verbatim.
    """

    name: str
    config: dict[str, Any]


@dataclass(frozen=True)
class Scheme:
    """A scheme's complete contract."""

    kind: Kind
    name: str
    contract_version: int
    content_model: type[BaseModel]
    subcommands: dict[str, Subcommand] = field(default_factory=dict)
    edge_relations: tuple[str, ...] = ()  # for edge-kind schemes only
    storage_adapters: tuple[StorageAdapter, ...] = ()

    def adapter_for(self, storage_name: str) -> StorageAdapter | None:
        for adapter in self.storage_adapters:
            if adapter.name == storage_name:
                return adapter
        return None


# --- loader ---------------------------------------------------------------

_LOADED: dict[str, Any] = {}  # path -> module, cached


def load_scheme_module(path: Path) -> Any:
    """Import `scheme.py` at `path` via spec_from_file_location. Cached."""
    abs_path = str(path.resolve())
    if abs_path in _LOADED:
        return _LOADED[abs_path]
    module_name = f"_artifact_scheme_{uuid.uuid4().hex}"
    spec = importlib.util.spec_from_file_location(module_name, abs_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load scheme module at {abs_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    _LOADED[abs_path] = module
    return module


def load_scheme(path: Path, toml_config: dict[str, Any] | None = None) -> Scheme:
    """Load `scheme.py` at `path` and return its `SCHEME` attribute.

    If `toml_config` is provided (the parsed scheme.toml), its `[[storage]]`
    entries are merged into the returned Scheme's `storage_adapters`.
    """
    module = load_scheme_module(path)
    scheme = getattr(module, "SCHEME", None)
    if not isinstance(scheme, Scheme):
        raise ImportError(f"{path} does not export SCHEME (of type Scheme)")
    if toml_config:
        adapters = []
        for entry in toml_config.get("storage") or []:
            if not isinstance(entry, dict):
                continue
            name = entry.get("name")
            if not isinstance(name, str) or not name:
                continue
            cfg = {k: v for k, v in entry.items() if k != "name"}
            adapters.append(StorageAdapter(name=name, config=cfg))
        if adapters:
            scheme = Scheme(
                kind=scheme.kind,
                name=scheme.name,
                contract_version=scheme.contract_version,
                content_model=scheme.content_model,
                subcommands=scheme.subcommands,
                edge_relations=scheme.edge_relations,
                storage_adapters=tuple(adapters),
            )
    return scheme


# --- universal list-entry shape -------------------------------------------


class ListEntry(BaseModel):
    uri: str
    kind: Literal["vertex", "edge", "metadata"]
    summary: dict[str, Any] = {}


class ListOut(BaseModel):
    entries: list[ListEntry]
