"""Preferences round-trip via user-config storage."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from artifactlib import scheme as scheme_mod

REPO = Path(__file__).resolve().parent.parent


def _load_user_config_storage():
    spec = importlib.util.spec_from_file_location(
        "_uc_storage", REPO / "artifact-storage" / "user-config" / "storage.py"
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_preferences_roundtrip(tmp_worktree: Path):
    storage = _load_user_config_storage()
    scheme = scheme_mod.load_scheme(REPO / "artifact-schemes" / "preferences" / "scheme.py")
    adapter = {"path_template": "preferences/{{ id }}.json", "serializer": "json"}

    create_in = scheme.subcommands["create"].in_model.model_validate(
        {"id": "user", "storage": {"document": {"default": "file"}}}
    )
    out = storage.cmd_create(scheme=scheme, adapter=adapter, input=create_in, uri=None)
    assert out["created"] is True
    uri = out["uri"]

    get_in = scheme.subcommands["get"].in_model.model_validate({"uri": uri})
    got = storage.cmd_get(scheme=scheme, adapter=adapter, input=get_in, uri=uri)
    assert got["content"]["storage"]["document"]["default"] == "file"
