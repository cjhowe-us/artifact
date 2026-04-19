from artifactlib import uri


def test_parse_roundtrip():
    u = uri.parse("document|file/docs/design/auth")
    assert u.scheme == "document"
    assert u.backend == "file"
    assert u.path == "docs/design/auth"
    assert str(u) == "document|file/docs/design/auth"


def test_try_parse_returns_none_on_bad_input():
    assert uri.try_parse("no-pipe-here") is None
    assert uri.try_parse("a|b") is None
    assert uri.try_parse("") is None


def test_accessors():
    assert uri.scheme_of("document|file/x") == "document"
    assert uri.backend_of("document|file/x") == "file"
    assert uri.scheme_of("garbage") is None
