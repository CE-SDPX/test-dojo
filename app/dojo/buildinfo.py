"""Build/version info for GET /api/version (out of test scope)."""
from __future__ import annotations

import hashlib
from pathlib import Path

from . import time_utils as tu

_STARTED_AT = tu.now_utc()


def _compute_source_hash() -> str:
    root = Path(__file__).parent
    h = hashlib.sha256()
    for p in sorted(root.rglob("*.py")):
        h.update(p.read_bytes())
    return h.hexdigest()


SOURCE_HASH = _compute_source_hash()
VERSION = (Path(__file__).parent.parent / "VERSION").read_text(encoding="utf-8").strip()


def started_at_api() -> str:
    return tu.to_api(_STARTED_AT)
