"""URI parsing for artifact addresses: <scheme>|<backend>/<path>."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Uri:
    scheme: str
    backend: str
    path: str

    def __str__(self) -> str:
        return f"{self.scheme}|{self.backend}/{self.path}"


def parse(raw: str) -> Uri:
    if "|" not in raw:
        raise ValueError(f"bad uri: {raw} (expected <scheme>|<backend>/<path>)")
    scheme, rest = raw.split("|", 1)
    if "/" not in rest:
        raise ValueError(f"bad uri: {raw} (missing /<path>)")
    backend, path = rest.split("/", 1)
    if not scheme or not backend:
        raise ValueError(f"bad uri: {raw}")
    return Uri(scheme=scheme, backend=backend, path=path)


def try_parse(raw: str) -> Uri | None:
    try:
        return parse(raw)
    except ValueError:
        return None


def scheme_of(raw: str) -> str | None:
    u = try_parse(raw)
    return u.scheme if u else None


def backend_of(raw: str) -> str | None:
    u = try_parse(raw)
    return u.backend if u else None
