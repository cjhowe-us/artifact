from pathlib import Path

import pytest

from artifactlib import render


def test_render_string_with_slug_filter():
    assert render.render_string("{{ x | slug }}", {"x": "Hello World!"}) == "hello-world"


def test_render_tree_dict_and_list():
    out = render.render_tree(
        {"title": "{{ t }}", "tags": ["{{ t }}-a", "b"]},
        {"t": "v"},
    )
    assert out == {"title": "v", "tags": ["v-a", "b"]}


def test_strict_undefined_raises():
    with pytest.raises(Exception):
        render.render_string("{{ missing }}", {})


def test_is_jinja_true():
    assert render.is_jinja("design.jinja.md")
    assert render.is_jinja("artifact-templates/x.jinja.json")


def test_is_jinja_false():
    assert not render.is_jinja("design.md")
    assert not render.is_jinja("jinja.md")  # jinja must appear between dots


def test_rendered_name_strips_jinja():
    assert render.rendered_name("design.jinja.md") == Path("design.md")
    assert (
        render.rendered_name("artifact-templates/x.jinja.toml")
        == Path("artifact-templates/x.toml")
    )


def test_render_file(tmp_path: Path):
    src = tmp_path / "greeting.jinja.md"
    src.write_text("hello {{ name }}\n")
    dst = render.render_file(src, {"name": "world"})
    assert dst == tmp_path / "greeting.md"
    assert dst.read_text() == "hello world\n"
