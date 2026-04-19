from pathlib import Path

from artifactlib import scheme as scheme_mod
from artifactlib.kinds import Kind

REPO = Path(__file__).resolve().parent.parent
SCHEMES = REPO / "artifact-schemes"


def test_load_artifact_template_scheme():
    s = scheme_mod.load_scheme(SCHEMES / "artifact-template" / "scheme.py")
    assert s.name == "artifact-template"
    assert s.kind is Kind.VERTEX
    assert "create" in s.subcommands
    assert "instantiate" in s.subcommands


def test_load_edge_scheme():
    s = scheme_mod.load_scheme(SCHEMES / "composed_of" / "scheme.py")
    assert s.name == "composed_of"
    assert s.kind is Kind.EDGE


def test_load_with_toml_config_populates_adapters():
    import tomllib

    toml_path = SCHEMES / "composed_of" / "scheme.toml"
    data = tomllib.loads(toml_path.read_text())
    s = scheme_mod.load_scheme(SCHEMES / "composed_of" / "scheme.py", data)
    assert any(a.name == "file" for a in s.storage_adapters)
    assert s.adapter_for("file") is not None
    adapter = s.adapter_for("file")
    assert adapter is not None
    assert adapter.config.get("path_template")


def test_load_scheme_rejects_missing_SCHEME(tmp_path):
    p = tmp_path / "scheme.py"
    p.write_text("# no SCHEME here\n")
    try:
        scheme_mod.load_scheme(p)
    except ImportError as exc:
        assert "SCHEME" in str(exc)
        return
    raise AssertionError("expected ImportError")
