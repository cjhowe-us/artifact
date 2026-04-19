"""IO helpers: atomic writes, git-root discovery, soft locks."""

from __future__ import annotations

import contextlib
import os
import subprocess
import tempfile
from pathlib import Path


def git_root(start: Path | None = None) -> Path:
    cwd = str(start) if start else None
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"],
            stderr=subprocess.DEVNULL,
            cwd=cwd,
        )
        return Path(out.decode().strip())
    except (subprocess.CalledProcessError, FileNotFoundError):
        return Path.cwd() if start is None else start


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".tmp-", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w") as f:
            f.write(text)
        os.replace(tmp, path)
    except BaseException:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(tmp)
        raise


def read_lock_owner(lock_file: Path) -> str:
    if not lock_file.is_file():
        return ""
    try:
        return lock_file.read_text().strip()
    except OSError:
        return ""


def try_take_lock(lock_file: Path, owner: str) -> tuple[bool, str]:
    """Take a lock. Returns (acquired, current_owner).

    - Returns (True, owner) if lock newly acquired or already held by owner.
    - Returns (False, existing) if held by someone else.
    """
    existing = read_lock_owner(lock_file)
    if existing and existing != owner:
        return False, existing
    lock_file.parent.mkdir(parents=True, exist_ok=True)
    lock_file.write_text(owner)
    return True, owner


def release_lock(lock_file: Path, owner: str) -> None:
    existing = read_lock_owner(lock_file)
    if not existing or existing == owner:
        with contextlib.suppress(FileNotFoundError):
            lock_file.unlink()
