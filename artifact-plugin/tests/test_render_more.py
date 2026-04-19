"""Extra render coverage: filters, is_jinja, rendered_name, render_file."""

from __future__ import annotations

from pathlib import Path

from artifactlib import render


def test_slug_filter():
    assert render.render_string("{{ x | slug }}", {"x": "Hello World!"}) == "hello-world"
    assert render.render_string("{{ x | slug }}", {"x": "  foo__bar  "}) == "foo-bar"


def test_snake_filter():
    assert render.render_string("{{ x | snake }}", {"x": "SomeCamelCase"}) == "some_camel_case"
    assert render.render_string("{{ x | snake }}", {"x": "hello world-foo"}) == "hello_world_foo"


def test_kebab_filter_is_alias_for_slug():
    assert render.render_string("{{ x | kebab }}", {"x": "Hello World"}) == "hello-world"


def test_json_escape_filter():
    out = render.render_string("{{ x | json_escape }}", {"x": 'a "b" c'})
    assert out == r"a \"b\" c"


def test_render_tree_dict_keys_and_list():
    ctx = {"k": "id", "v": "42"}
    out = render.render_tree(
        {
            "{{ k }}": "{{ v }}",
            "nested": [{"name": "{{ v }}"}],
            "ints": [1, 2, 3],
        },
        ctx,
    )
    assert out == {"id": "42", "nested": [{"name": "42"}], "ints": [1, 2, 3]}


def test_render_tree_leaves_non_str_types_alone():
    out = render.render_tree({"a": 1, "b": None, "c": True}, {})
    assert out == {"a": 1, "b": None, "c": True}


def test_is_jinja_detection():
    assert render.is_jinja("design.jinja.md")
    assert render.is_jinja("path/to/x.jinja.toml")
    assert not render.is_jinja("design.md")
    assert not render.is_jinja("jinja.md")  # only two parts
    assert not render.is_jinja("x.jinja")  # terminal jinja, not middle


def test_rendered_name_strips_jinja_component():
    assert render.rendered_name("design.jinja.md") == Path("design.md")
    assert render.rendered_name("a/b/x.jinja.toml") == Path("a/b/x.toml")


def test_render_file_writes_default_output(tmp_path: Path):
    src = tmp_path / "greet.jinja.md"
    src.write_text("hello {{ name }}")
    out = render.render_file(src, {"name": "world"})
    assert out == tmp_path / "greet.md"
    assert out.read_text() == "hello world"


def test_render_file_explicit_out_path(tmp_path: Path):
    src = tmp_path / "greet.jinja.md"
    src.write_text("hi {{ n }}")
    dst = tmp_path / "sub/elsewhere.md"
    out = render.render_file(src, {"n": "there"}, out_path=dst)
    assert out == dst
    assert dst.read_text() == "hi there"
