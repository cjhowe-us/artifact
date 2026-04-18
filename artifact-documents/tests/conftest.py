"""Shared pytest fixtures."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CORE_SCRIPTS = REPO_ROOT / "artifact" / "scripts"
if str(CORE_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(CORE_SCRIPTS))


@pytest.fixture
def tmp_worktree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    subprocess.run(
        ["git", "init", "-q", str(tmp_path)],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ARTIFACT_CONFIG_DIR", str(tmp_path / ".artifact-config"))
    monkeypatch.setenv("ARTIFACT_CACHE_DIR", str(tmp_path / ".artifact-cache"))
    monkeypatch.setenv("ARTIFACT_STATE_DIR", str(tmp_path / ".artifact-state"))
    return tmp_path


@pytest.fixture
def registry(tmp_worktree: Path) -> dict:
    import discover  # type: ignore
    import json
    import os

    discover.main()
    return __import__("json").loads(
        (Path(os.environ["ARTIFACT_CACHE_DIR"]) / "registry.json").read_text()
    )
