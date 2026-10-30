"""The five response shapes worth knowing, and nothing else.

Discord interaction callbacks are a number and a body. These helpers name the
numbers so the handlers read like English.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

PONG = 1
CHANNEL_MESSAGE = 4
DEFERRED_CHANNEL_MESSAGE = 5
EPHEMERAL = 64  # "only you can see this"


def pong() -> Dict[str, Any]:
    """Answer to Discord's PING. This is what makes the endpoint URL save."""
    return {"type": PONG}


def message(
    content: str,
    *,
    components: Optional[List[Dict[str, Any]]] = None,
    embeds: Optional[List[Dict[str, Any]]] = None,
    ephemeral: bool = False,
) -> Dict[str, Any]:
    data: Dict[str, Any] = {"content": content[:2000]}
    if embeds:
        data["embeds"] = embeds
    if components:
        data["components"] = components
    body: Dict[str, Any] = {"type": CHANNEL_MESSAGE, "data": data}
    if ephemeral:
        body["data"]["flags"] = EPHEMERAL
    return body


def deferred(*, ephemeral: bool = False) -> Dict[str, Any]:
    """Acknowledge now, answer later.

    Discord gives you three seconds. Past that the user sees "This interaction
    failed" and the interaction is dead. Type 5 buys you fifteen minutes, and
    you finish the job by POSTing a follow-up message.
    """
    body: Dict[str, Any] = {"type": DEFERRED_CHANNEL_MESSAGE}
    if ephemeral:
        body["data"] = {"flags": EPHEMERAL}
    return body


def text_input_button(label: str, url: str) -> Dict[str, Any]:
    """A link button. Buttons in a `components` row are how you add UI."""
    return {
        "type": 1,
        "components": [{"type": 2, "style": 5, "label": label[:80], "url": url}],
    }
