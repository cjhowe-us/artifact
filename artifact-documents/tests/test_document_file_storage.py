"""document scheme round-trip through the file storage."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from artifactlib import scheme as scheme_mod


REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def _load_file_storage():
    spec = importlib.util.spec_from_file_location(
        "_file_storage", REPO_ROOT / "artifact" / "artifact-storage" / "file" / "storage.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_document_create_and_get(tmp_worktree: Path):
    storage = _load_file_storage()
    doc_scheme = scheme_mod.load_scheme(
        REPO_ROOT / "artifact-documents" / "artifact-schemes" / "document" / "scheme.py"
    )
    adapter = {
        "body_field": "body",
        "body_path_template": "{{ id }}.md",
        "content_path_template": "{{ id }}.content.toml",
        "content_serializer": "toml",
    }
    payload = {
        "id": "docs/design/auth",
        "title": "Auth rework",
        "authors": ["christian"],
        "status": "draft",
        "body": "## Auth rework\n\nDesign body here.\n",
    }
    create_in = doc_scheme.subcommands["create"].in_model.model_validate(payload)
    out = storage.cmd_create(scheme=doc_scheme, adapter=adapter, input=create_in, uri=None)
    assert out["created"] is True
    assert out["uri"] == "document|file/docs/design/auth"

    md = tmp_worktree / "docs" / "design" / "auth.md"
    ct = tmp_worktree / "docs" / "design" / "auth.content.toml"
    assert md.read_text().startswith("## Auth rework")
    assert "Auth rework" in ct.read_text()

    get_in = doc_scheme.subcommands["get"].in_model.model_validate({"uri": out["uri"]})
    got = storage.cmd_get(scheme=doc_scheme, adapter=adapter, input=get_in, uri=out["uri"])
    assert got["content"]["title"] == "Auth rework"
    assert got["content"]["authors"] == ["christian"]
    assert got["content"]["body"].startswith("## Auth rework")
