"""Gmail API message resources → unified events.

Input: the JSON from `users.messages.get(format="full")`. The real connection
(OAuth, "Fetch new mail") is server/google.py, design/17; push via Pub/Sub is not built.
"""
from __future__ import annotations

import base64
import html
import re
from datetime import datetime, timezone

from .base import local_hhmm, register, resolve_sender

_QUOTE_START = re.compile(r"^\s*On .+wrote:\s*$", re.M)
_TAG = re.compile(r"<[^>]+>")


def _decode(data: str) -> str:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4)).decode("utf-8", "replace")


def _find_part(payload: dict, mime: str) -> str | None:
    if payload.get("mimeType") == mime and payload.get("body", {}).get("data"):
        return _decode(payload["body"]["data"])
    for part in payload.get("parts", []) or []:
        found = _find_part(part, mime)
        if found:
            return found
    return None


@register
class GmailAdapter:
    source = "gmail"
    event_type = "message"

    def to_event(self, raw: dict, people: dict) -> dict:
        payload = raw["payload"]
        headers = {h["name"].lower(): h["value"] for h in payload.get("headers", [])}

        body = _find_part(payload, "text/plain")
        if body is None:
            html_body = _find_part(payload, "text/html") or ""
            body = html.unescape(_TAG.sub(" ", html_body))
        m = _QUOTE_START.search(body)
        if m:
            body = body[: m.start()]
        body = re.sub(r"[ \t]+", " ", body).strip()

        subject = headers.get("subject", "").strip()
        sent = datetime.fromtimestamp(int(raw["internalDate"]) / 1000, tz=timezone.utc)
        return {
            "id": f"gmail-{raw['id']}",
            "time": local_hhmm(sent),
            "type": "message",
            "source": "email",
            "sender": resolve_sender("email", headers.get("from", ""), people),
            "channel": "Email",
            "subject": subject,
            "text": f"{subject}\n\n{body}".strip() if subject else body,
            "thread": raw.get("threadId"),
            # A fact for the state (bulk/marketing mail), not a routing decision.
            "bulk_mail": "list-unsubscribe" in headers,
        }

    def fetch(self, **kwargs) -> list[dict]:
        raise NotImplementedError("needs Google OAuth + Gmail push; see design/13-adapters.md")
