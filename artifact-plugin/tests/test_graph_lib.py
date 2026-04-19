"""Unit tests for artifactlib.graph — list_edges, find, expand, as_json."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from artifactlib import graph


class _FakeProvider:
    def __init__(self, by_relation: dict[str, list[dict]]):
        self._by_rel = by_relation

    def dispatch(self, *, scheme_name, subcommand, payload, uri_str, storage_override):
        entries = [
            e
            for e in self._by_rel.get(scheme_name, [])
            if (payload.get("source") in (None, e["content"]["source"]))
            and (payload.get("target") in (None, e["content"]["target"]))
        ]
        return {"entries": entries}


def _install_fake_provider(monkeypatch: pytest.MonkeyPatch, by_relation: dict[str, list[dict]]):
    from artifactlib import provider as provider_mod

    fake = _FakeProvider(by_relation)
    monkeypatch.setattr(provider_mod, "dispatch", fake.dispatch)
    monkeypatch.setattr(graph, "_edge_scheme_names", lambda: list(by_relation.keys()))


def _edge(rel: str, s: str, t: str, **attrs):
    return {
        "uri": f"{rel}|file/{s}--{t}",
        "content": {"source": s, "target": t, "relation": rel, "attrs": attrs},
    }


def test_list_edges_flattens_across_relations(monkeypatch: pytest.MonkeyPatch):
    _install_fake_provider(
        monkeypatch,
        {
            "composed_of": [_edge("composed_of", "a", "b"), _edge("composed_of", "a", "c")],
            "depends_on": [_edge("depends_on", "a", "d")],
        },
    )
    edges = graph.list_edges()
    relations = {e.relation for e in edges}
    assert relations == {"composed_of", "depends_on"}
    assert len(edges) == 3


def test_list_edges_single_relation_filter(monkeypatch: pytest.MonkeyPatch):
    _install_fake_provider(
        monkeypatch,
        {
            "composed_of": [_edge("composed_of", "a", "b")],
            "depends_on": [_edge("depends_on", "a", "d")],
        },
    )
    edges = graph.list_edges(relation="composed_of")
    assert [e.target for e in edges] == ["b"]


def test_find_by_target(monkeypatch: pytest.MonkeyPatch):
    _install_fake_provider(
        monkeypatch,
        {"composed_of": [_edge("composed_of", "a", "z"), _edge("composed_of", "b", "z")]},
    )
    edges = graph.find(relation="composed_of", target="z")
    assert {e.source for e in edges} == {"a", "b"}


def test_expand_bfs_depth(monkeypatch: pytest.MonkeyPatch):
    _install_fake_provider(
        monkeypatch,
        {
            "composed_of": [
                _edge("composed_of", "root", "x"),
                _edge("composed_of", "root", "y"),
                _edge("composed_of", "x", "x1"),
                _edge("composed_of", "y", "y1"),
            ]
        },
    )
    depth1 = graph.expand(uri="root", depth=1)
    assert {e.target for e in depth1} == {"x", "y"}
    depth2 = graph.expand(uri="root", depth=2)
    assert {e.target for e in depth2} == {"x", "y", "x1", "y1"}


def test_expand_skips_already_visited(monkeypatch: pytest.MonkeyPatch):
    # Cycle: a → b → a
    _install_fake_provider(
        monkeypatch,
        {"composed_of": [_edge("composed_of", "a", "b"), _edge("composed_of", "b", "a")]},
    )
    edges = graph.expand(uri="a", depth=5)
    # 2 edges emitted, no infinite loop.
    assert len(edges) == 2


def test_list_edges_swallows_mediator_errors(monkeypatch: pytest.MonkeyPatch):
    from artifactlib import provider as provider_mod

    monkeypatch.setattr(graph, "_edge_scheme_names", lambda: ["broken"])

    def boom(**kw):
        raise provider_mod.MediatorError("x")

    monkeypatch.setattr(provider_mod, "dispatch", boom)
    assert graph.list_edges() == []


def test_list_edges_swallows_no_storage(monkeypatch: pytest.MonkeyPatch):
    from artifactlib import provider as provider_mod
    from artifactlib import registry

    monkeypatch.setattr(graph, "_edge_scheme_names", lambda: ["broken"])

    def boom(**kw):
        raise registry.NoStorageForScheme("broken")

    monkeypatch.setattr(provider_mod, "dispatch", boom)
    assert graph.list_edges() == []


def test_as_json_serializes_edges():
    edges = [graph.Edge(uri="u", source="a", target="b", relation="r", attrs={"k": 1})]
    payload = json.loads(graph.as_json(edges))
    assert payload == [
        {"uri": "u", "source": "a", "target": "b", "relation": "r", "attrs": {"k": 1}}
    ]


def test_edge_scheme_names_pulls_from_registry(tmp_worktree: Path, monkeypatch: pytest.MonkeyPatch):
    from artifactlib import registry

    monkeypatch.setattr(
        registry,
        "scheme_entries",
        lambda: [
            {"name": "composed_of", "kind": "edge"},
            {"name": "status", "kind": "metadata"},
            {"kind": "edge"},  # no name → skipped
        ],
    )
    assert graph._edge_scheme_names() == ["composed_of"]
