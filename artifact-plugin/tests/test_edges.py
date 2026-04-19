from artifactlib import edges, kinds


def test_make_edge_scheme_shape():
    s = edges.make_edge_scheme("composed_of")
    assert s.kind is kinds.Kind.EDGE
    assert s.name == "composed_of"
    assert set(s.subcommands) >= {"create", "get", "list", "status"}


def test_content_model_defaults_relation():
    s = edges.make_edge_scheme("depends_on")
    inst = s.content_model(source="a|b/c", target="d|e/f")
    assert inst.relation == "depends_on"
    assert inst.attrs == {}


def test_create_in_allows_attrs():
    s = edges.make_edge_scheme("validates")
    sub = s.subcommands["create"]
    instance = sub.in_model.model_validate(
        {"source": "x|y/z", "target": "a|b/c", "attrs": {"weight": 3}}
    )
    assert instance.attrs == {"weight": 3}
