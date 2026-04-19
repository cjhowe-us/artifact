"""Tests for artifactlib.conformance helpers."""

from __future__ import annotations

import importlib.util
import types
from pathlib import Path

from artifactlib import conformance
from artifactlib.edges import make_edge_scheme

REPO_ROOT = Path(__file__).resolve().parent.parent

_EDGE_ADAPTER = {
    "path_template": "artifact-edges/composed_of/{{ source | slug }}--{{ target | slug }}.json",
    "serializer": "json",
}


def _load_file_storage():
    spec = importlib.util.spec_from_file_location(
        "_file_storage", REPO_ROOT / "artifact-storage" / "file" / "storage.py"
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_check_subcommand_coverage_all_present():
    scheme = make_edge_scheme("composed_of")
    file_storage = _load_file_storage()
    assert conformance.check_subcommand_coverage(scheme, file_storage) == []


def test_check_subcommand_coverage_missing_flagged():
    scheme = make_edge_scheme("composed_of")
    empty = types.ModuleType("empty")
    missing = conformance.check_subcommand_coverage(scheme, empty)
    assert "create" in missing
    assert "get" in missing


def test_round_trip_create_get(tmp_worktree: Path):
    scheme = make_edge_scheme("composed_of")
    file_storage = _load_file_storage()

    out = conformance.round_trip_create_get(
        scheme=scheme,
        storage_module=file_storage,
        adapter=_EDGE_ADAPTER,
        create_input={"source": "doc|file/a", "target": "doc|file/b"},
    )
    assert out["content"]["source"] == "doc|file/a"
    assert out["content"]["target"] == "doc|file/b"
    assert out["content"]["relation"] == "composed_of"


def test_round_trip_handles_pydantic_model_return(tmp_worktree: Path):
    """round_trip must coerce pydantic-model returns to dicts."""
    scheme = make_edge_scheme("composed_of")
    file_storage = _load_file_storage()

    def wrapped_create(**kw):
        return scheme.subcommands["create"].out_model.model_validate(file_storage.cmd_create(**kw))

    def wrapped_get(**kw):
        return scheme.subcommands["get"].out_model.model_validate(file_storage.cmd_get(**kw))

    fake_storage = types.SimpleNamespace(cmd_create=wrapped_create, cmd_get=wrapped_get)
    out = conformance.round_trip_create_get(
        scheme=scheme,
        storage_module=fake_storage,
        adapter=_EDGE_ADAPTER,
        create_input={"source": "doc|file/c", "target": "doc|file/d"},
    )
    assert out["content"]["source"] == "doc|file/c"
