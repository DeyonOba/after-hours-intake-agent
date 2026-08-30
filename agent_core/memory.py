"""Customer memory keyed by phone number (the contact ID from missed-call capture)."""
from __future__ import annotations

from . import config

_STORE: dict | None = None


def lookup(phone: str) -> dict | None:
    global _STORE
    if _STORE is None:
        _STORE = config.load_memory_store()
    return _STORE.get(phone.strip())
