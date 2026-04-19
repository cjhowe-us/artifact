"""Jinja2 helpers.

A template file is any file whose name contains ``.jinja.`` — e.g.
``design.jinja.md``, ``config.jinja.json``, ``entry.jinja.py``. The
``.jinja`` component is stripped to form the rendered filename
(``design.md``, ``config.json``, ``entry.py``).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import jinja2

_SLUG_NONWORD = re.compile(r"[^a-zA-Z0-9]+")


# ---------- filters ----------------------------------------------------------


def _slug(value: Any) -> str:
    s = str(value).strip().lower()
    s = _SLUG_NONWORD.sub("-", s)
    return s.strip("-")


def _snake(value: Any) -> str:
    s = str(value).strip()
    s = re.sub(r"[\s-]+", "_", s)
    s = re.sub(r"(?<!^)(?=[A-Z])", "_", s)
    return s.lower()


def _kebab(value: Any) -> str:
    return _slug(value)


def _json_escape(value: Any) -> str:
    import json

    return json.dumps(value)[1:-1]  # strip surrounding quotes


def env() -> jinja2.Environment:
    e = jinja2.Environment(
        keep_trailing_newline=True,
        undefined=jinja2.StrictUndefined,
        autoescape=False,
    )
    filters: dict[str, Any] = {
        "slug": _slug,
        "snake": _snake,
        "kebab": _kebab,
        "json_escape": _json_escape,
    }
    for name, fn in filters.items():
        e.filters[name] = fn
        e.globals[name] = fn
    return e


# ---------- rendering --------------------------------------------------------


def render_string(template: str, context: dict[str, Any]) -> str:
    return env().from_string(template).render(**context)


def render_tree(value: Any, context: dict[str, Any]) -> Any:
    """Recursively render every string leaf in dict/list. Dict keys rendered too."""
    if isinstance(value, str):
        return render_string(value, context)
    if isinstance(value, dict):
        return {
            render_string(k, context) if isinstance(k, str) else k: render_tree(v, context)
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [render_tree(v, context) for v in value]
    return value


# ---------- .jinja. filename convention -------------------------------------


def is_jinja(path: str | Path) -> bool:
    """True if the filename contains ``.jinja.`` before its terminal extension."""
    name = Path(path).name
    # Must have at least two dots; the ``.jinja.`` marker precedes the target ext.
    parts = name.split(".")
    return len(parts) >= 3 and "jinja" in parts[1:-1]


def rendered_name(path: str | Path) -> Path:
    """Return the path with the ``.jinja`` component removed from its name.

    ``design.jinja.md`` → ``design.md``.
    ``artifact-templates/x.jinja.toml`` → ``artifact-templates/x.toml``.
    """
    p = Path(path)
    parts = p.name.split(".")
    kept = [seg for seg in parts if seg != "jinja"]
    return p.with_name(".".join(kept))


def render_file(
    template_path: str | Path,
    context: dict[str, Any],
    out_path: str | Path | None = None,
) -> Path:
    """Render a template file with jinja2; write to out_path (default: rendered_name)."""
    src = Path(template_path)
    dst = Path(out_path) if out_path is not None else rendered_name(src)
    dst.parent.mkdir(parents=True, exist_ok=True)
    body = src.read_text(encoding="utf-8")
    rendered = render_string(body, context)
    dst.write_text(rendered, encoding="utf-8")
    return dst
