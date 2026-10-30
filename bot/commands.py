"""The slash commands this starter ships with.

Registering commands is a one-time upload of these definitions to Discord. Keep
the same list here as in the handlers so the two cannot drift.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List

NAME_PATTERN = re.compile(r"^[-_\w]{1,32}$")

COMMANDS: List[Dict[str, Any]] = [
    {
        "name": "hello",
        "description": "Say hello and show a button you can click",
        "type": 1,
    },
    {
        "name": "ping",
        "description": "Check whether the bot is awake",
        "type": 1,
    },
    {
        "name": "slow",
        "description": "Show the three-second rule with a deferred reply",
        "type": 1,
    },
]


def problems() -> List[str]:
    """Reasons this commands list would be rejected by Discord, if any.

    Discord is strict and its error messages are terse, so checking locally saves
    a round trip.
    """
    found: List[str] = []
    seen = set()
    for command in COMMANDS:
        name = command.get("name", "")
        description = command.get("description", "")
        if not NAME_PATTERN.match(name):
            found.append("command name {!r} must match {}".format(name, NAME_PATTERN.pattern))
        if name in seen:
            found.append("command name {!r} is declared twice".format(name))
        seen.add(name)
        if not 1 <= len(description) <= 100:
            found.append("command {!r} description must be 1-100 characters".format(name))
    return found


if __name__ == "__main__":  # a handy way to check before you deploy
    issues = problems()
    print("\n".join(issues) if issues else "commands look valid")
