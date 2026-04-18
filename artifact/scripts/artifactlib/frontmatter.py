"""Minimal YAML frontmatter: scheme, id, metadata pointer.

An artifact file on disk looks like:

    ---
    scheme: <scheme>
    id: <stable-id>
    metadata: <relative-path-to-sidecar.json>
    ---
    <body>

Rich per-scheme fields live in the sidecar JSON. The frontmatter is a
pointer; parsing it never requires understanding scheme semantics.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TextIO

import yaml


FIELDS = ("scheme", "id", "metadata")


@dataclass(frozen=True)
class Frontmatter:
    scheme: str
    id: str
    metadata: str  # relative path to sidecar JSON, from the artifact file's directory


@dataclass(frozen=True)
class Document:
    frontmatter: Frontmatter | None
    body: str


def parse(text: str) -> Document:
    if not text.startswith("---"):
        return Document(frontmatter=None, body=text)
    lines = text.split("\n")
    if len(lines) < 2 or lines[0].rstrip() != "---":
        return Document(frontmatter=None, body=text)
    end = None
    for idx in range(1, len(lines)):
        if lines[idx].rstrip() == "---":
            end = idx
            break
    if end is None:
        return Document(frontmatter=None, body=text)
    raw = "\n".join(lines[1:end])
    data = yaml.safe_load(raw) or {}
    fm = _coerce(data)
    body = "\n".join(lines[end + 1 :])
    if body.startswith("\n"):
        body = body[1:]
    return Document(frontmatter=fm, body=body)


def _coerce(data: dict) -> Frontmatter | None:
    scheme = data.get("scheme")
    ident = data.get("id")
    metadata = data.get("metadata")
    if not (isinstance(scheme, str) and isinstance(ident, str) and isinstance(metadata, str)):
        return None
    return Frontmatter(scheme=scheme, id=ident, metadata=metadata)


def validate_strict(data: dict) -> None:
    """Raise if the dict has anything other than {scheme, id, metadata}.

    Call this at write-time to enforce the minimal-frontmatter rule. Parsing
    stays lenient so legacy artifacts remain discoverable.
    """
    missing = [f for f in FIELDS if not isinstance(data.get(f), str) or not data.get(f)]
    if missing:
        raise ValueError(f"frontmatter missing required fields: {missing}")
    extra = set(data.keys()) - set(FIELDS)
    if extra:
        raise ValueError(f"extra frontmatter fields not allowed: {sorted(extra)}")


def render(fm: Frontmatter, body: str) -> str:
    header = yaml.safe_dump(
        {"scheme": fm.scheme, "id": fm.id, "metadata": fm.metadata},
        sort_keys=False,
        default_flow_style=False,
    ).rstrip()
    return f"---\n{header}\n---\n\n{body}"


def read(path: Path) -> Document:
    return parse(path.read_text())


def write(path: Path, fm: Frontmatter, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render(fm, body))
