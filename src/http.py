"""Tiny HTTP helper with a shared session, timeout, and JSON convenience."""
from __future__ import annotations

import html
import json
import re
from xml.etree import ElementTree as ET

import requests

# Escape bare ampersands and undefined HTML entities (e.g. &nbsp;) that would
# otherwise make a strict XML parser reject an RSS feed.
_BAD_ENTITY = re.compile(r"&(?!(?:amp|lt|gt|quot|apos|#\d+|#x[0-9a-fA-F]+);)")

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


def get_text(url: str, params: dict | None = None,
             headers: dict | None = None) -> str:
    """GET a URL and return its body as UTF-8 text (used for RSS/XML feeds)."""
    resp = _session.get(url, params=params, headers=headers, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.content.decode("utf-8", errors="replace")


def get_rss_items(url: str) -> list[dict]:
    """Fetch an RSS feed and return each <item> as a {tag: text} dict.

    Tolerates undefined HTML entities that would break strict XML parsing.
    """
    xml = _BAD_ENTITY.sub("&amp;", get_text(url))
    root = ET.fromstring(xml)
    items = []
    for item in root.findall(".//item"):
        row = {}
        for child in item:
            tag = child.tag.split("}")[-1]  # strip namespace
            if child.text:
                row[tag] = html.unescape(child.text)
        items.append(row)
    return items
