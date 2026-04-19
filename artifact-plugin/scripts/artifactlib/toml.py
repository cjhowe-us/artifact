"""TOML load/dump via tomlkit (round-trip preserving) + atomic write.

Reading uses stdlib `tomllib` when round-trip preservation isn't needed (faster).
Writing goes through tomlkit so comments + key order survive.
"""

from __future__ import annotations

import os
import tempfile
import tomllib
from pathlib import Path
from typing import Any

import tomlkit


def load(path: Path) -> dict[str, Any]:
    """Fast read via stdlib tomllib. Use `load_doc` when you need to round-trip."""
    with path.open("rb") as f:
        return tomllib.load(f)


def loads(text: str) -> dict[str, Any]:
    return tomllib.loads(text)


def load_doc(path: Path) -> tomlkit.TOMLDocument:
    """Round-trippable parse via tomlkit. Preserves comments + order."""
    return tomlkit.parse(path.read_text(encoding="utf-8"))


def dumps(data: dict[str, Any] | tomlkit.TOMLDocument) -> str:
    if isinstance(data, tomlkit.TOMLDocument):
        return tomlkit.dumps(data)
    doc = tomlkit.document()
    for k, v in data.items():
        doc[k] = v
    return tomlkit.dumps(doc)


def atomic_write(path: Path, data: dict[str, Any] | tomlkit.TOMLDocument) -> None:
    text = dumps(data)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".tmp-", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass
        raise
