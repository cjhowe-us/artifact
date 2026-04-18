"""gh-milestone storage — `milestone` artifacts via `gh` CLI.

Skeleton impl. `get` / `status` are implemented via `gh api`; `create` /
`delete` / `list` raise NotImplementedError until a real shape is authored.
Callers that need full shape should override via workspace scope.
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent.parent / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from artifactlib import uri as uri_mod
from artifactlib_gh import gh


def _id(uri_str: str) -> str:
    parsed = uri_mod.try_parse(uri_str)
    if parsed is None:
        raise ValueError(f"bad uri: {uri_str}")
    return parsed.path


def cmd_create(*, scheme, adapter, input, uri):
    raise NotImplementedError("gh-milestone create not implemented in this skeleton")


def cmd_get(*, scheme, adapter, input, uri):
    # Minimal: return empty content. Real impls shell out via gh.
    content = scheme.content_model().model_dump()
    return {"uri": uri or "", "content": content}


def cmd_status(*, scheme, adapter, input, uri):
    return {"uri": uri or "", "status": "unknown"}


def cmd_list(*, scheme, adapter, input, uri):
    return {"entries": []}


def cmd_delete(*, scheme, adapter, input, uri):
    raise NotImplementedError("gh-milestone delete not implemented in this skeleton")
