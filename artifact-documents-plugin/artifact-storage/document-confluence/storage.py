"""document-confluence storage — `document` artifacts as Confluence Cloud pages.

Needs CONFLUENCE_BASE_URL, CONFLUENCE_USER, CONFLUENCE_TOKEN in environment.
URIs: ``document|document-confluence/<space>/<page-id>``.

Minimal reference impl via stdlib urllib + json. Callers that want rich
behaviour can wrap around this.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from base64 import b64encode

from artifactlib import uri as uri_mod


def _creds() -> tuple[str, str, str]:
    base = os.environ.get("CONFLUENCE_BASE_URL", "").rstrip("/")
    user = os.environ.get("CONFLUENCE_USER", "")
    token = os.environ.get("CONFLUENCE_TOKEN", "")
    if not (base and user and token):
        raise RuntimeError(
            "document-confluence requires CONFLUENCE_BASE_URL, CONFLUENCE_USER, CONFLUENCE_TOKEN"
        )
    return base, user, token


def _auth_header(user: str, token: str) -> str:
    raw = f"{user}:{token}".encode()
    return "Basic " + b64encode(raw).decode("ascii")


def _request(method: str, url: str, body: dict | None = None) -> dict:
    base, user, token = _creds()
    headers = {
        "Authorization": _auth_header(user, token),
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            txt = resp.read().decode("utf-8")
            return json.loads(txt) if txt else {}
    except urllib.error.HTTPError as exc:
        raise RuntimeError(
            f"confluence {method} {url} → {exc.code}: {exc.read().decode()}"
        ) from exc


def _parse_id(uri_str: str) -> tuple[str, str]:
    """Return (space_key, page_id)."""
    parsed = uri_mod.try_parse(uri_str)
    if parsed is None:
        raise ValueError(f"bad uri: {uri_str}")
    parts = parsed.path.split("/", 1)
    if len(parts) != 2:
        raise ValueError(f"document-confluence uri needs <space>/<page-id>: {uri_str}")
    return parts[0], parts[1]


def cmd_create(*, scheme, adapter, input, uri):
    fields = input.model_dump()
    base, _, _ = _creds()
    space_key = fields.get("space") or fields.get("id", "").split("/", 1)[0]
    if not space_key:
        raise ValueError("document-confluence create requires `space` or id=<space>/...")
    body = {
        "spaceId": space_key,
        "status": "current",
        "title": fields.get("title") or "",
        "body": {"representation": "storage", "value": fields.get("body") or ""},
    }
    result = _request("POST", f"{base}/api/v2/pages", body)
    page_id = result.get("id", "")
    return {
        "uri": f"{scheme.name}|document-confluence/{space_key}/{page_id}",
        "created": True,
    }


def cmd_get(*, scheme, adapter, input, uri):
    space, page_id = _parse_id(uri)
    base, _, _ = _creds()
    page = _request("GET", f"{base}/api/v2/pages/{page_id}?body-format=storage")
    content = {
        "title": page.get("title", ""),
        "authors": [],
        "status": page.get("status", "current"),
        "body": page.get("body", {}).get("storage", {}).get("value", ""),
    }
    validated = scheme.content_model.model_validate(content)
    return {"uri": uri, "content": validated.model_dump()}


def cmd_update(*, scheme, adapter, input, uri):
    space, page_id = _parse_id(uri or input.uri)
    base, _, _ = _creds()
    patch = input.patch if hasattr(input, "patch") else {}
    body = {
        "id": page_id,
        "status": "current",
        "title": patch.get("title", ""),
        "body": {"representation": "storage", "value": patch.get("body", "")},
        "version": {"number": int(patch.get("version", 1))},
    }
    _request("PUT", f"{base}/api/v2/pages/{page_id}", body)
    return {"uri": uri or f"{scheme.name}|document-confluence/{space}/{page_id}", "updated": True}


def cmd_delete(*, scheme, adapter, input, uri):
    _, page_id = _parse_id(uri or input.uri)
    base, _, _ = _creds()
    _request("DELETE", f"{base}/api/v2/pages/{page_id}")
    return {"uri": uri or "", "deleted": True}


def cmd_status(*, scheme, adapter, input, uri):
    try:
        _, page_id = _parse_id(uri or getattr(input, "uri", ""))
        base, _, _ = _creds()
        _request("GET", f"{base}/api/v2/pages/{page_id}")
        return {"uri": uri or "", "status": "complete"}
    except Exception:
        return {"uri": uri or "", "status": "unknown"}


def cmd_list(*, scheme, adapter, input, uri):
    # Confluence paging not implemented here; returns empty.
    return {"entries": []}
