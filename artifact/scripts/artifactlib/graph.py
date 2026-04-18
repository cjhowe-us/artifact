"""Graph queries over edge-kind artifacts.

Edges are first-class artifacts. Querying the graph = listing edge artifacts
with filters on ``source``, ``target``, and ``relation``. No special index.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from . import registry
from .kinds import Kind


@dataclass(frozen=True)
class Edge:
    uri: str
    source: str
    target: str
    relation: str
    attrs: dict[str, Any]


def _edge_scheme_names() -> list[str]:
    out = []
    for entry in registry.scheme_entries():
        if entry.get("kind") == Kind.EDGE.value:
            name = entry.get("name")
            if name:
                out.append(name)
    return out


def list_edges(
    *,
    relation: str | None = None,
    source: str | None = None,
    target: str | None = None,
) -> list[Edge]:
    """Dispatch `list` across all edge schemes, filter + flatten."""
    from . import provider

    relations = [relation] if relation else _edge_scheme_names()
    collected: list[Edge] = []
    for rel in relations:
        try:
            out = provider.dispatch(
                scheme_name=rel,
                subcommand="list",
                payload={"source": source, "target": target},
                uri_str=None,
                storage_override=None,
            )
        except provider.MediatorError:
            continue
        except registry.NoStorageForScheme:
            continue
        for entry in out.get("entries", []):
            content = entry.get("content") or entry.get("summary") or {}
            uri = entry.get("uri", "")
            collected.append(
                Edge(
                    uri=uri,
                    source=content.get("source", ""),
                    target=content.get("target", ""),
                    relation=content.get("relation", rel),
                    attrs=content.get("attrs", {}),
                )
            )
    return collected


def find(*, relation: str, target: str) -> list[Edge]:
    """All edges of this relation that point at `target`."""
    return list_edges(relation=relation, target=target)


def expand(*, uri: str, relation: str | None = None, depth: int = 1) -> list[Edge]:
    """Outbound-edge walk from `uri`, up to `depth` hops. Breadth-first."""
    visited: set[str] = set()
    frontier: list[str] = [uri]
    edges: list[Edge] = []
    for _ in range(depth):
        next_frontier: list[str] = []
        for node in frontier:
            if node in visited:
                continue
            visited.add(node)
            outbound = list_edges(relation=relation, source=node)
            edges.extend(outbound)
            next_frontier.extend(e.target for e in outbound)
        frontier = next_frontier
    return edges


def as_json(edges: list[Edge]) -> str:
    return json.dumps([e.__dict__ for e in edges], indent=2)
