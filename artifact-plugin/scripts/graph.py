#!/usr/bin/env python3
"""Graph CLI — thin wrapper over artifactlib.graph.

Subcommands:
    graph.py expand --uri <U> [--relation R] [--depth N]
    graph.py find   --relation R --target <U>
    graph.py list   [--relation R] [--source U] [--target U]
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from artifactlib import graph as G  # noqa: E402


def main(argv: list[str]) -> int:
    if not argv:
        sys.stderr.write("usage: graph.py {expand|find|list} [options]\n")
        return 2
    sub = argv[0]
    rest = argv[1:]

    opts = {}
    i = 0
    while i < len(rest):
        tok = rest[i]
        if tok in ("--uri", "--relation", "--target", "--source", "--depth"):
            opts[tok.lstrip("-")] = rest[i + 1]
            i += 2
        else:
            i += 1

    if sub == "expand":
        edges = G.expand(
            uri=opts["uri"],
            relation=opts.get("relation"),
            depth=int(opts.get("depth") or 1),
        )
    elif sub == "find":
        edges = G.find(relation=opts["relation"], target=opts["target"])
    elif sub == "list":
        edges = G.list_edges(
            relation=opts.get("relation"),
            source=opts.get("source"),
            target=opts.get("target"),
        )
    else:
        sys.stderr.write(f"unknown subcommand: {sub}\n")
        return 2

    sys.stdout.write(G.as_json(edges) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
