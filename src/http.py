"""Tiny HTTP helper with a shared session, timeout, and JSON convenience."""
from __future__ import annotations

import requests

_HEADERS = {
    "User-Agent": "java-jobs-telegram-bot/1.0 (+https://github.com)",
    "Accept": "application/json",
}

_session = requests.Session()
_session.headers.update(_HEADERS)

TIMEOUT = 20


def get_json(url: str, params: dict | None = None) -> dict | list:
    """GET a URL and return parsed JSON. Raises on HTTP or decode errors."""
    resp = _session.get(url, params=params, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()
