"""Shared pytest fixtures."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))


@pytest.fixture
def tmp_worktree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Initialize a git worktree + chdir into it + isolated XDG dirs."""
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
    """Build a registry scoped to this test's plugin dir (this repo)."""
    import discover  # type: ignore

    discover.main()
    import json

    cache = Path(os.environ["ARTIFACT_CACHE_DIR"])
    return json.loads((cache / "registry.json").read_text())
