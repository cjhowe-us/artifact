"""Tests for artifactlib.xdg per-OS dir resolution."""

from __future__ import annotations

import platform
from pathlib import Path

import pytest
from artifactlib import xdg


@pytest.fixture
def clean_env(monkeypatch: pytest.MonkeyPatch):
    for var in (
        "ARTIFACT_CONFIG_DIR",
        "ARTIFACT_CACHE_DIR",
        "ARTIFACT_STATE_DIR",
        "XDG_CONFIG_HOME",
        "XDG_CACHE_HOME",
        "XDG_STATE_HOME",
        "APPDATA",
        "LOCALAPPDATA",
    ):
        monkeypatch.delenv(var, raising=False)
    return monkeypatch


def test_resolve_honors_artifact_overrides(clean_env, tmp_path: Path):
    clean_env.setenv("ARTIFACT_CONFIG_DIR", str(tmp_path / "cfg"))
    clean_env.setenv("ARTIFACT_CACHE_DIR", str(tmp_path / "cch"))
    clean_env.setenv("ARTIFACT_STATE_DIR", str(tmp_path / "st"))
    dirs = xdg.resolve()
    assert dirs.config == tmp_path / "cfg"
    assert dirs.cache == tmp_path / "cch"
    assert dirs.state == tmp_path / "st"


def test_resolve_darwin_defaults(clean_env, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(platform, "system", lambda: "Darwin")
    dirs = xdg.resolve()
    home = Path.home()
    assert dirs.config == home / "Library/Application Support/artifact"
    assert dirs.cache == home / "Library/Caches/artifact"
    assert dirs.state == home / "Library/Application Support/artifact/state"


def test_resolve_windows_defaults(clean_env, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.setattr(platform, "system", lambda: "Windows")
    clean_env.setenv("APPDATA", str(tmp_path / "Roaming"))
    clean_env.setenv("LOCALAPPDATA", str(tmp_path / "Local"))
    dirs = xdg.resolve()
    assert dirs.config == tmp_path / "Roaming" / "artifact"
    assert dirs.cache == tmp_path / "Local" / "artifact/cache"
    assert dirs.state == tmp_path / "Local" / "artifact/state"


def test_resolve_windows_falls_back_when_env_unset(clean_env, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(platform, "system", lambda: "Windows")
    dirs = xdg.resolve()
    home = Path.home()
    assert dirs.config == home / "AppData/Roaming" / "artifact"


def test_resolve_linux_defaults(clean_env, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(platform, "system", lambda: "Linux")
    dirs = xdg.resolve()
    home = Path.home()
    assert dirs.config == home / ".config/artifact"
    assert dirs.cache == home / ".cache/artifact"
    assert dirs.state == home / ".local/state/artifact"


def test_resolve_linux_honors_xdg_vars(clean_env, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.setattr(platform, "system", lambda: "Linux")
    clean_env.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))
    clean_env.setenv("XDG_CACHE_HOME", str(tmp_path / "cch"))
    clean_env.setenv("XDG_STATE_HOME", str(tmp_path / "st"))
    dirs = xdg.resolve()
    assert dirs.config == tmp_path / "cfg/artifact"
    assert dirs.cache == tmp_path / "cch/artifact"
    assert dirs.state == tmp_path / "st/artifact"
