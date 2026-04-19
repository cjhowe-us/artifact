"""Extra artifactlib.toml coverage: load_doc, dumps, atomic_write, error cleanup."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from artifactlib import toml as toml_mod


def test_load_reads_toml_file(tmp_path: Path):
    p = tmp_path / "a.toml"
    p.write_text('name = "x"\nversion = 1\n')
    assert toml_mod.load(p) == {"name": "x", "version": 1}


def test_loads_parses_string():
    assert toml_mod.loads("x = 1\n") == {"x": 1}


def test_load_doc_preserves_comments_on_roundtrip(tmp_path: Path):
    src = '# top comment\nname = "x"\n'
    p = tmp_path / "a.toml"
    p.write_text(src)
    doc = toml_mod.load_doc(p)
    assert toml_mod.dumps(doc) == src


def test_dumps_from_plain_dict():
    assert toml_mod.dumps({"a": 1}).strip() == "a = 1"


def test_atomic_write_creates_parents_and_file(tmp_path: Path):
    target = tmp_path / "nested/deep/out.toml"
    toml_mod.atomic_write(target, {"k": "v"})
    assert target.read_text().strip() == 'k = "v"'


def test_atomic_write_cleans_tmp_on_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    def boom(*args, **kwargs):
        raise RuntimeError("replace failed")

    monkeypatch.setattr(os, "replace", boom)
    target = tmp_path / "x.toml"
    with pytest.raises(RuntimeError, match="replace failed"):
        toml_mod.atomic_write(target, {"k": "v"})
    assert not list(tmp_path.glob(".tmp-*"))
