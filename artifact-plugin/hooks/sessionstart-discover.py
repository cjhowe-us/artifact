#!/usr/bin/env python3
"""SessionStart hook — rebuilds the artifact registry.

Invoked by Claude Code as:

    python3 ${CLAUDE_PLUGIN_ROOT}/hooks/sessionstart-discover.py

Probes runtime deps; on missing deps, prints a one-line install hint to stderr
and exits 0 (non-fatal).
"""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    try:
        import jinja2  # noqa: F401
        import pydantic  # noqa: F401
        import tomlkit  # noqa: F401
    except ImportError:
        sys.stderr.write(
            "artifact: install deps → python3 -m pip install 'pydantic>=2' tomlkit jinja2\n"
        )
        return 0

    here = Path(__file__).resolve().parent
    scripts = here.parent / "scripts"
    sys.path.insert(0, str(scripts))

    from discover import main as discover_main

    return discover_main()


if __name__ == "__main__":
    sys.exit(main())
