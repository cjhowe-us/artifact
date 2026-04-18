"""os-notifications storage — emits OS notifications via platform tools.

create: emits a notification. get/list are no-ops (no persistence).
"""

from __future__ import annotations

import platform
import subprocess


def _notify(title: str, body: str) -> None:
    system = platform.system()
    if system == "Darwin":
        script = f'display notification "{body}" with title "{title}"'
        subprocess.run(["osascript", "-e", script], check=False)
    elif system == "Linux":
        subprocess.run(["notify-send", title, body], check=False)
    elif system == "Windows":
        # Use msg.exe as a minimal cross-shell option
        subprocess.run(["msg", "*", f"{title}: {body}"], check=False)


def cmd_create(*, scheme, adapter, input, uri):
    fields = input.model_dump()
    _notify(fields.get("title", "artifact"), fields.get("body", ""))
    return {"uri": f"{scheme.name}|os-notifications/-", "created": True}


def cmd_get(*, scheme, adapter, input, uri):
    return {"uri": uri or f"{scheme.name}|os-notifications/-", "content": {}}


def cmd_status(*, scheme, adapter, input, uri):
    return {"uri": uri or f"{scheme.name}|os-notifications/-", "status": "unknown"}


def cmd_list(*, scheme, adapter, input, uri):
    return {"entries": []}


def cmd_delete(*, scheme, adapter, input, uri):
    return {"uri": uri or "", "deleted": True}
