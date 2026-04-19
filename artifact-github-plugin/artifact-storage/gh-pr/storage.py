"""gh-pr storage — `pr` artifacts via the `gh` CLI.

URI shape: ``pr|gh-pr/<owner>/<repo>/<number>``.
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


def _parse_pr_uri(uri_str: str) -> tuple[str, str, int]:
    parsed = uri_mod.try_parse(uri_str)
    if parsed is None:
        raise ValueError(f"bad uri: {uri_str}")
    parts = parsed.path.split("/")
    if len(parts) != 3:
        raise ValueError(f"pr uri must be <owner>/<repo>/<number>: {uri_str}")
    owner, repo, num = parts
    return owner, repo, int(num)


def cmd_create(*, scheme, adapter, input, uri):
    fields = input.model_dump()
    owner_repo = fields.get("id", "")
    if "/" not in owner_repo:
        raise ValueError("gh-pr create requires id='owner/repo'")
    owner, repo = owner_repo.split("/", 1)
    argv = [
        "pr",
        "create",
        "--repo",
        f"{owner}/{repo}",
        "--title",
        fields.get("title", ""),
        "--body",
        fields.get("body", ""),
        "--base",
        fields.get("base") or "main",
        "--head",
        fields.get("head") or "",
    ]
    if not fields.get("head"):
        raise ValueError("gh-pr create requires `head` (source branch)")
    out = gh.run(argv)
    url = out.strip().splitlines()[-1].strip()
    num = int(url.rsplit("/", 1)[-1])
    return {"uri": f"{scheme.name}|gh-pr/{owner}/{repo}/{num}", "created": True}


def cmd_get(*, scheme, adapter, input, uri):
    owner, repo, num = _parse_pr_uri(uri or input.uri)
    data = gh.run_json(
        [
            "pr",
            "view",
            str(num),
            "--repo",
            f"{owner}/{repo}",
            "--json",
            "title,body,state,url,number,baseRefName,headRefName",
        ]
    )
    content = {
        "title": data.get("title", ""),
        "body": data.get("body", "") or "",
        "state": (data.get("state") or "").lower(),
        "url": data.get("url", ""),
        "number": data.get("number"),
        "base": data.get("baseRefName", ""),
        "head": data.get("headRefName", ""),
    }
    validated = scheme.content_model.model_validate(content)
    return {"uri": uri, "content": validated.model_dump()}


def cmd_status(*, scheme, adapter, input, uri):
    try:
        owner, repo, num = _parse_pr_uri(uri or getattr(input, "uri", ""))
        gh.run_json(
            [
                "pr",
                "view",
                str(num),
                "--repo",
                f"{owner}/{repo}",
                "--json",
                "state",
            ]
        )
        return {"uri": uri or "", "status": "complete"}
    except Exception:
        return {"uri": uri or "", "status": "unknown"}


def cmd_list(*, scheme, adapter, input, uri):
    owner = getattr(input, "owner", None)
    repo = getattr(input, "repo", None)
    if not (owner and repo):
        return {"entries": []}
    try:
        data = gh.run_json(
            [
                "pr",
                "list",
                "--repo",
                f"{owner}/{repo}",
                "--json",
                "number,title,state,url",
            ]
        )
    except Exception:
        return {"entries": []}
    entries = []
    for p in data or []:
        entries.append(
            {
                "uri": f"{scheme.name}|gh-pr/{owner}/{repo}/{p['number']}",
                "kind": scheme.kind.value,
                "summary": {"title": p.get("title", ""), "state": p.get("state", "")},
            }
        )
    return {"entries": entries}


def cmd_delete(*, scheme, adapter, input, uri):
    raise NotImplementedError("gh-pr has no delete (close via `gh pr close`)")
