"""Tiny HTTP helper with a shared session, timeout, and JSON convenience."""
from __future__ import annotations

import json

import requests

_HEADERS = {
    "User-Agent": "java-jobs-telegram-bot/1.0 (+https://github.com)",
    "Accept": "application/json",
}

_session = requests.Session()
_session.headers.update(_HEADERS)

TIMEOUT = 20


def get_json(url: str, params: dict | None = None,
             headers: dict | None = None) -> dict | list:
    """GET a URL and return parsed JSON. Raises on HTTP or decode errors.

    Per-request headers are merged over the session defaults (used for APIs
    like RapidAPI that require auth headers).
    """
    resp = _session.get(url, params=params, headers=headers, timeout=TIMEOUT)
    resp.raise_for_status()
    # Decode from raw bytes as UTF-8 rather than trusting requests' charset
    # guessing, which mangles accented text (e.g. "Sênior" → "SÃªnior") when a
    # source omits or misdeclares its charset.
    return json.loads(resp.content)
