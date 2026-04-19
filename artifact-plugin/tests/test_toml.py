from pathlib import Path

from artifactlib import toml as atoml


def test_atomic_write_and_load(tmp_path: Path):
    p = tmp_path / "x.toml"
    atoml.atomic_write(p, {"a": 1, "nested": {"b": [1, 2, 3]}})
    data = atoml.load(p)
    assert data == {"a": 1, "nested": {"b": [1, 2, 3]}}


def test_dumps_preserves_order():
    out = atoml.dumps({"b": 1, "a": 2})
    assert out.index("b =") < out.index("a =")
