"""Round-trip a composed_of edge + a template artifact through file storage."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from artifactlib import scheme as scheme_mod
from artifactlib.edges import make_edge_scheme

REPO = Path(__file__).resolve().parent.parent


def _load_storage_module() -> object:
    spec = importlib.util.spec_from_file_location(
        "_file_storage", REPO / "artifact-storage" / "file" / "storage.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_edge_roundtrip(tmp_worktree: Path):
    storage = _load_storage_module()
    scheme = make_edge_scheme("composed_of")
    adapter = {
        "path_template": "artifact-edges/composed_of/{{ source | slug }}--{{ target | slug }}.json",
        "serializer": "json",
    }
    create_in = scheme.subcommands["create"].in_model.model_validate(
        {"source": "doc|file/a", "target": "doc|file/b"}
    )
    create_out = storage.cmd_create(scheme=scheme, adapter=adapter, input=create_in, uri=None)
    assert create_out["created"] is True
    uri = create_out["uri"]
    assert uri.startswith("composed_of|file/artifact-edges/composed_of/")

    get_in = scheme.subcommands["get"].in_model.model_validate({"uri": uri})
    get_out = storage.cmd_get(scheme=scheme, adapter=adapter, input=get_in, uri=uri)
    assert get_out["content"]["source"] == "doc|file/a"
    assert get_out["content"]["target"] == "doc|file/b"
    assert get_out["content"]["relation"] == "composed_of"


def test_list_edges_with_filter(tmp_worktree: Path):
    storage = _load_storage_module()
    scheme = make_edge_scheme("composed_of")
    adapter = {
        "path_template": "artifact-edges/composed_of/{{ source | slug }}--{{ target | slug }}.json",
        "serializer": "json",
    }
    create_in_cls = scheme.subcommands["create"].in_model
    for s, t in [("a|b/x", "c|d/y"), ("a|b/x", "c|d/z"), ("q|r/p", "c|d/y")]:
        storage.cmd_create(
            scheme=scheme,
            adapter=adapter,
            input=create_in_cls.model_validate({"source": s, "target": t}),
            uri=None,
        )

    list_in = scheme.subcommands["list"].in_model.model_validate({"source": "a|b/x"})
    out = storage.cmd_list(scheme=scheme, adapter=adapter, input=list_in, uri=None)
    sources = {e["content"]["source"] for e in out["entries"]}
    assert sources == {"a|b/x"}
    assert len(out["entries"]) == 2


def test_split_shape_roundtrip(tmp_worktree: Path):
    """document-like vertex: body + content.toml split."""
    storage = _load_storage_module()
    template_scheme = scheme_mod.load_scheme(
        REPO / "artifact-schemes" / "artifact-template" / "scheme.py"
    )
    adapter = {
        "body_field": "body",
        "body_path_template": "artifact-templates/{{ id }}.jinja.md",
        "content_path_template": "artifact-templates/{{ id }}.content.toml",
        "content_serializer": "toml",
    }
    payload = {
        "id": "test-tmpl",
        "name": "test-tmpl",
        "target_scheme": "notifications",
        "description": "smoke",
        "body": "hello {{ name }}",
        "inputs": [{"name": "name", "type": "string", "required": True}],
        "output": {
            "path_template": "notifs/{{ name | slug }}.json",
            "create_input": {"title": "{{ name }}"},
        },
    }
    create_in = template_scheme.subcommands["create"].in_model.model_validate(payload)
    out = storage.cmd_create(scheme=template_scheme, adapter=adapter, input=create_in, uri=None)
    uri = out["uri"]
    assert uri == "artifact-template|file/test-tmpl"

    # files exist
    body = tmp_worktree / "artifact-templates" / "test-tmpl.jinja.md"
    content = tmp_worktree / "artifact-templates" / "test-tmpl.content.toml"
    assert body.read_text().startswith("hello")
    assert content.exists()

    # get round-trip
    get_in = template_scheme.subcommands["get"].in_model.model_validate({"uri": uri})
    got = storage.cmd_get(scheme=template_scheme, adapter=adapter, input=get_in, uri=uri)
    assert got["content"]["name"] == "test-tmpl"
    assert got["content"]["body"].startswith("hello")
