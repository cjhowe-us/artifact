"""Scheme kinds — every scheme declares one.

Vertex  — a first-class thing (document, PR, template, …).
Edge    — a typed link between two artifacts.
Metadata — a typed annotation attached to one target artifact.
"""

from __future__ import annotations

from enum import StrEnum


class Kind(StrEnum):
    VERTEX = "vertex"
    EDGE = "edge"
    METADATA = "metadata"


ALL_KINDS: tuple[Kind, ...] = (Kind.VERTEX, Kind.EDGE, Kind.METADATA)
