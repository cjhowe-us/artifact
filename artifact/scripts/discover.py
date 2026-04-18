#!/usr/bin/env python3
"""Rebuild the artifact registry at $ARTIFACT_CACHE_DIR/registry.json.

Scans every scope (override / workspace / user / each installed plugin) for:

- ``artifact-schemes/<n>/scheme.toml``  → `artifact-scheme` entries
- ``artifact-storage/<n>/storage.toml`` → `artifact-storage` entries
- ``artifact-templates/<stem>.jinja.*`` → `artifact-template` entries
  (discovered via companion ``<stem>.content.toml``)
- ``workflows/<n>/workflow.md``         → `workflow` entries (read from YAML
  frontmatter using stdlib only; top-level `workflows/` dir, not a skill)
"""

from __future__ import annotations

import datetime
import json
import os
import re
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from artifactlib import xdg  # noqa: E402


def _git_root(start: Path) -> Path | None:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=str(start),
            stderr=subprocess.DEVNULL,
        )
        return Path(out.decode().strip())
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def _scopes() -> list[tuple[str, Path]]:
    scopes: list[tuple[str, Path]] = []
    cwd = Path.cwd()

    override = cwd / ".artifact-override"
    if override.is_dir():
        scopes.append(("override", override))

    repo = _git_root(cwd)
    if repo is not None:
        workspace = repo / ".claude"
        if workspace.is_dir():
            scopes.append(("workspace", workspace))

    user = Path.home() / ".claude"
    if user.is_dir():
        scopes.append(("user", user))

    env_dirs = os.environ.get("CLAUDE_PLUGIN_DIRS", "")
    if env_dirs:
        sep = ";" if os.name == "nt" else ":"
        for raw in env_dirs.split(sep):
            d = Path(raw)
            if not d.is_dir():
                continue
            for plugin in sorted(d.iterdir()):
                if plugin.is_dir():
                    scopes.append(("plugin", plugin))

    plugin_root = HERE.parent
    scopes.append(("plugin", plugin_root))

    if not env_dirs:
        parent = plugin_root.parent
        for sibling in sorted(parent.iterdir()):
            if not sibling.is_dir() or sibling == plugin_root:
                continue
            name = sibling.name
            if name.startswith("artifact") or name.startswith("workflow"):
                scopes.append(("plugin", sibling))

    return scopes


def _read_toml(path: Path) -> dict[str, Any]:
    try:
        with path.open("rb") as f:
            return tomllib.load(f)
    except (OSError, tomllib.TOMLDecodeError):
        return {}


def _walk(scope: str, root: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []

    schemes_dir = root / "artifact-schemes"
    if schemes_dir.is_dir():
        for toml_path in sorted(schemes_dir.glob("*/scheme.toml")):
            data = _read_toml(toml_path)
            name = data.get("name")
            if not isinstance(name, str) or not name:
                continue
            entries.append(
                {
                    "entry_type": "artifact-scheme",
                    "scope": scope,
                    "path": str(toml_path),
                    "name": name,
                    "scheme": data.get("scheme") or name,
                    "kind": data.get("kind"),
                    "description": data.get("description"),
                    "contract_version": data.get("contract_version"),
                    "storages": data.get("storage") or [],
                }
            )

    storage_dir = root / "artifact-storage"
    if storage_dir.is_dir():
        for toml_path in sorted(storage_dir.glob("*/storage.toml")):
            data = _read_toml(toml_path)
            name = data.get("name")
            if not isinstance(name, str) or not name:
                continue
            entries.append(
                {
                    "entry_type": "artifact-storage",
                    "scope": scope,
                    "path": str(toml_path),
                    "name": name,
                    "description": data.get("description"),
                    "contract_version": data.get("contract_version"),
                    "backs_schemes": data.get("backs_schemes") or [],
                    "capabilities": data.get("capabilities") or {},
                }
            )

    templates_dir = root / "artifact-templates"
    if templates_dir.is_dir():
        for body_path in sorted(templates_dir.iterdir()):
            if not body_path.is_file():
                continue
            if ".jinja." not in body_path.name:
                continue
            stem = body_path.name.split(".jinja.", 1)[0]
            content_path = templates_dir / f"{stem}.content.toml"
            if not content_path.is_file():
                continue
            content = _read_toml(content_path)
            name = content.get("name") or stem
            entries.append(
                {
                    "entry_type": "artifact-template",
                    "scope": scope,
                    "path": str(body_path),
                    "content_path": str(content_path),
                    "name": name,
                    "target_scheme": content.get("target_scheme"),
                    "description": content.get("description"),
                    "contract_version": content.get("contract_version"),
                }
            )

    workflows = root / "workflows"
    if workflows.is_dir():
        for wf_file in sorted(workflows.glob("*/workflow.md")):
            fm = _read_skill_frontmatter(wf_file)
            name = fm.get("name")
            if not name:
                continue
            entries.append(
                {
                    "entry_type": "workflow",
                    "scope": scope,
                    "path": str(wf_file),
                    "name": name,
                    "description": fm.get("description"),
                }
            )

    return entries


_FM_KV = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*):\s*(.*)$")


def _read_skill_frontmatter(path: Path) -> dict[str, Any]:
    """workflow.md (and legacy SKILL.md) carry Claude-Code-style YAML frontmatter.
    Minimal YAML subset parse to avoid pulling PyYAML into the core registry path.
    """
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}
    lines = text.split("\n")
    end = None
    for i in range(1, len(lines)):
        if lines[i].rstrip() == "---":
            end = i
            break
    if end is None:
        return {}
    out: dict[str, Any] = {}
    for line in lines[1:end]:
        m = _FM_KV.match(line)
        if not m:
            continue
        key, raw = m.group(1), m.group(2).strip()
        if raw.startswith('"') and raw.endswith('"'):
            raw = raw[1:-1]
        out[key] = raw
    return out


def main() -> int:
    dirs = xdg.resolve()
    dirs.cache.mkdir(parents=True, exist_ok=True)

    all_entries: list[dict[str, Any]] = []
    for scope, root in _scopes():
        all_entries.extend(_walk(scope, root))

    warnings: list[str] = []
    schemes_by_name = {
        e["name"]: e for e in all_entries if e.get("entry_type") == "artifact-scheme"
    }
    for storage in [e for e in all_entries if e.get("entry_type") == "artifact-storage"]:
        for sn in storage.get("backs_schemes") or []:
            scheme = schemes_by_name.get(sn)
            if scheme is None:
                continue
            declared = [s.get("name") for s in scheme.get("storages") or []]
            if storage["name"] not in declared:
                warnings.append(
                    f"storage={storage['name']} claims backs_schemes={sn!r} "
                    f"but scheme={sn!r} lacks a matching [[storage]] entry"
                )

    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    registry = {"generated_at": now, "entries": all_entries, "warnings": warnings}
    out = dirs.cache / "registry.json"
    out.write_text(json.dumps(registry, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
