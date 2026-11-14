"""Slack Events API `message` events → unified events.

Input: the `event_callback` envelope Slack POSTs to your Events API endpoint.
A real connection needs a Slack app with the `message.im` / `message.channels`
event subscriptions; see design/13-adapters.md.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone

from .base import local_hhmm, register, resolve_sender

_MENTION = re.compile(r"<@([A-Z0-9]+)>")
_LINK = re.compile(r"<(https?://[^|>]+)\|([^>]+)>")


@register
class SlackAdapter:
    source = "slack"
    event_type = "message"

    def to_event(self, raw: dict, people: dict) -> dict:
        ev = raw["event"]
        is_bot = bool(ev.get("bot_id")) or ev.get("subtype") == "bot_message"
        handle = ev.get("user") or ev.get("bot_id")
        sender = resolve_sender("slack", handle, people)

        def name_of(m):
            key = resolve_sender("slack", m.group(1), people)
            return people[key]["name"] if key in people else m.group(0)

        text = _MENTION.sub(name_of, ev.get("text", ""))
        text = _LINK.sub(r"\2 (\1)", text)

        if ev.get("channel_type") == "im":
            channel = "Slack DM"
        else:
            channel = f"Slack #{ev.get('channel_name') or ev.get('channel')}"

        ts = datetime.fromtimestamp(float(ev["ts"]), tz=timezone.utc)
        out = {
            "id": f"slack-{ev.get('channel')}-{ev['ts']}",
            "time": local_hhmm(ts),
            "type": "message",
            "source": "slack",
            "sender": sender,
            "channel": channel,
            "text": text.strip(),
            "is_bot": is_bot,
        }
        if ev.get("thread_ts") and ev.get("thread_ts") != ev["ts"]:
            out["thread"] = ev["thread_ts"]
        return out

    def fetch(self, **kwargs) -> list[dict]:
        raise NotImplementedError("needs a Slack app + OAuth; see design/13-adapters.md")
