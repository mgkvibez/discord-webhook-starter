"""What your bot actually does. Everything else is plumbing.

Add a command by adding a branch in ``_command`` and an entry in commands.py.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from . import responses as R
from .config import Settings

APPLICATION_COMMAND = 2
MESSAGE_COMPONENT = 3


@dataclass
class Reply:
    """A response body, plus an optional message to send after replying.

    ``followup`` is how you beat the three-second deadline: answer immediately
    with a deferred acknowledgement, then do the slow work and send the result.
    """

    body: Dict[str, Any]
    followup: Optional[Dict[str, Any]] = None


async def handle_interaction(payload: Dict[str, Any], settings: Settings) -> Reply:
    kind = payload.get("type")
    if kind == APPLICATION_COMMAND:
        return _command(payload)
    if kind == MESSAGE_COMPONENT:
        return _component(payload)
    return Reply(
        R.message(
            "I don't handle interaction type `{}` yet. "
            "The switch is in bot/handlers.py.".format(kind),
            ephemeral=True,
        )
    )


def _user_id(payload: Dict[str, Any]) -> str:
    member = payload.get("member") or {}
    user = member.get("user") or payload.get("user") or {}
    return str(user.get("id") or "")


def _command(payload: Dict[str, Any]) -> Reply:
    data = payload.get("data") or {}
    name = str(data.get("name") or "").lower()
    user_id = _user_id(payload)
    mention = "Hi <@{}>!".format(user_id) if user_id else "Hi!"

    if name == "hello":
        return Reply(
            R.message(
                "{} I'm a bot that answers over plain HTTP: no gateway connection, "
                "no `while True`, and it sleeps between requests.".format(mention),
                components=[R.text_input_button("How this works", "https://discord.com/developers/docs/interactions/overview")],
            )
        )
    if name == "ping":
        return Reply(R.message("Pong. The endpoint is awake, and the signature checked out."))
    if name == "slow":
        return Reply(
            R.deferred(),
            followup={
                "content": "Done. That took longer than three seconds, and you never saw "
                "\"This interaction failed\" because the bot acknowledged first."
            },
        )
    return Reply(
        R.message(
            "`/{}` is registered but has no handler yet. "
            "Add a branch in bot/handlers.py.".format(name or "unknown"),
            ephemeral=True,
        )
    )


def _component(payload: Dict[str, Any]) -> Reply:
    data = payload.get("data") or {}
    custom_id = str(data.get("custom_id") or "")
    if custom_id == "hello:again":
        return Reply(
            R.message(
                "You clicked a button. That arrives as interaction type 3, and you answer it "
                "exactly like a command.",
                ephemeral=True,
            )
        )
    return Reply(R.message("Unknown component `{}`.".format(custom_id or "none"), ephemeral=True))
