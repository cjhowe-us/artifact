"""Direct-call coverage for artifactlib.provider (mediator dispatch)."""

from __future__ import annotations

from pathlib import Path

import pytest
from artifactlib import provider, registry


@pytest.fixture
def _discovered(tmp_worktree: Path):
    """Run registry discovery so provider can resolve real schemes/storages."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "_discover", Path(__file__).resolve().parent.parent / "scripts" / "discover.py"
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.main()
    return tmp_worktree


def test_dispatch_vertex_create_then_get(_discovered: Path):
    # Use the `pydantic-schema` vertex scheme + `file` storage (both ship in-plugin).
    created = provider.dispatch(
        scheme_name="pydantic-schema",
        subcommand="create",
        payload={"id": "docs/probe", "class_name": "X", "body": "class X: pass\n"},
        uri_str=None,
        storage_override="file",
    )
    assert created["created"] is True
    uri = created["uri"]
    got = provider.dispatch(
        scheme_name="pydantic-schema",
        subcommand="get",
        payload={"uri": uri},
        uri_str=uri,
        storage_override=None,
    )
    assert got["content"]["body"].startswith("class X")


def test_dispatch_unknown_subcommand_raises(_discovered: Path):
    with pytest.raises(provider.MediatorError, match="no subcommand"):
        provider.dispatch(
            scheme_name="pydantic-schema",
            subcommand="nope",
            payload={},
            uri_str=None,
            storage_override=None,
        )


def test_dispatch_unresolved_storage(_discovered: Path, monkeypatch: pytest.MonkeyPatch):
    # Force registry to fail storage resolution.
    def fake_resolve(scheme_name, storage_override):
        return None

    monkeypatch.setattr(registry, "resolve_storage", fake_resolve)
    with pytest.raises(provider.MediatorError, match="cannot resolve storage"):
        provider.dispatch(
            scheme_name="pydantic-schema",
            subcommand="get",
            payload={"uri": "pydantic-schema|file/x"},
            uri_str=None,
            storage_override=None,
        )


def test_dispatch_missing_handler(_discovered: Path, monkeypatch: pytest.MonkeyPatch):
    import types

    empty = types.ModuleType("empty")
    monkeypatch.setattr(provider, "_load_storage_module", lambda name: empty)
    with pytest.raises(provider.MediatorError, match="no handler"):
        provider.dispatch(
            scheme_name="pydantic-schema",
            subcommand="get",
            payload={"uri": "pydantic-schema|file/x"},
            uri_str="pydantic-schema|file/x",
            storage_override=None,
        )


def test_load_storage_module_reports_bad_spec(monkeypatch: pytest.MonkeyPatch):
    # spec_from_file_location returns None when the path has no loader
    # (e.g. unknown extension); that's the path the MediatorError guards.
    import importlib.util

    monkeypatch.setattr(importlib.util, "spec_from_file_location", lambda *a, **k: None)
    monkeypatch.setattr(registry, "storage_script", lambda name: Path("/tmp/ghost.py"))
    with pytest.raises(provider.MediatorError, match="cannot load storage"):
        provider._load_storage_module("ghost")
