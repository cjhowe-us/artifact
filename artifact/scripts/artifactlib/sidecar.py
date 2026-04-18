"""Sidecar JSON files that hold artifact metadata and edges.

Naming convention (relative to the primary artifact file ``<stem>``):
    <stem>.metadata.json  — rich metadata, arbitrary per-scheme fields
    <stem>.edges.json     — typed edge list: [{target, relation}, ...]
    <stem>.lock           — holder name for soft locks
    <stem>.progress.jsonl — append-only progress log
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def metadata_path(primary: Path) -> Path:
    return primary.with_suffix(primary.suffix + ".metadata.json") if primary.suffix else primary.with_name(primary.name + ".metadata.json")


def edges_path(primary: Path) -> Path:
    return primary.with_suffix(primary.suffix + ".edges.json") if primary.suffix else primary.with_name(primary.name + ".edges.json")


def lock_path(primary: Path) -> Path:
    return primary.with_suffix(primary.suffix + ".lock") if primary.suffix else primary.with_name(primary.name + ".lock")


def progress_path(primary: Path) -> Path:
    return primary.with_suffix(primary.suffix + ".progress.jsonl") if primary.suffix else primary.with_name(primary.name + ".progress.jsonl")


def read_metadata(primary: Path) -> dict[str, Any]:
    p = metadata_path(primary)
    if not p.is_file():
        return {}
    return json.loads(p.read_text())


def write_metadata(primary: Path, data: dict[str, Any]) -> Path:
    p = metadata_path(primary)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, sort_keys=False) + "\n")
    return p


def read_edges(primary: Path) -> list[dict[str, Any]]:
    p = edges_path(primary)
    if not p.is_file():
        return []
    raw = json.loads(p.read_text())
    edges = raw.get("edges", [])
    return edges if isinstance(edges, list) else []


def write_edges(primary: Path, edges: list[dict[str, Any]]) -> Path:
    p = edges_path(primary)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"edges": edges}, indent=2) + "\n")
    return p


def delete_all_sidecars(primary: Path) -> None:
    for p in (metadata_path(primary), edges_path(primary), lock_path(primary), progress_path(primary)):
        if p.exists():
            p.unlink()
