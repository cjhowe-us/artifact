"""Shared fixtures for artifact-github."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent.parent
CORE_SCRIPTS = REPO / "artifact-plugin" / "scripts"
GH_SCRIPTS = REPO / "artifact-github-plugin" / "scripts"
for p in (CORE_SCRIPTS, GH_SCRIPTS):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))


@pytest.fixture
def tmp_worktree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True, stdout=subprocess.DEVNULL)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ARTIFACT_CONFIG_DIR", str(tmp_path / ".artifact-config"))
    monkeypatch.setenv("ARTIFACT_CACHE_DIR", str(tmp_path / ".artifact-cache"))
    return tmp_path
