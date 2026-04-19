"""Per-OS artifact state directories. Mirrors scripts/xdg.sh."""

from __future__ import annotations

import os
import platform
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Dirs:
    config: Path
    cache: Path
    state: Path


def resolve() -> Dirs:
    system = platform.system()
    home = Path.home()

    if system == "Darwin":
        config = Path(os.environ.get("ARTIFACT_CONFIG_DIR") or home / "Library/Application Support/artifact")
        cache = Path(os.environ.get("ARTIFACT_CACHE_DIR") or home / "Library/Caches/artifact")
        state = Path(os.environ.get("ARTIFACT_STATE_DIR") or home / "Library/Application Support/artifact/state")
    elif system == "Windows":
        appdata = Path(os.environ.get("APPDATA") or home / "AppData/Roaming")
        localappdata = Path(os.environ.get("LOCALAPPDATA") or home / "AppData/Local")
        config = Path(os.environ.get("ARTIFACT_CONFIG_DIR") or appdata / "artifact")
        cache = Path(os.environ.get("ARTIFACT_CACHE_DIR") or localappdata / "artifact/cache")
        state = Path(os.environ.get("ARTIFACT_STATE_DIR") or localappdata / "artifact/state")
    else:
        xdg_config = Path(os.environ.get("XDG_CONFIG_HOME") or home / ".config")
        xdg_cache = Path(os.environ.get("XDG_CACHE_HOME") or home / ".cache")
        xdg_state = Path(os.environ.get("XDG_STATE_HOME") or home / ".local/state")
        config = Path(os.environ.get("ARTIFACT_CONFIG_DIR") or xdg_config / "artifact")
        cache = Path(os.environ.get("ARTIFACT_CACHE_DIR") or xdg_cache / "artifact")
        state = Path(os.environ.get("ARTIFACT_STATE_DIR") or xdg_state / "artifact")

    return Dirs(config=config, cache=cache, state=state)
