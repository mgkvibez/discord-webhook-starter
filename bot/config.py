"""Configuration, read once from the environment.

Nothing here raises when a value is missing: the app has to import (and answer
/health) even on a machine where nothing is configured yet. The endpoints that
need a value refuse to work without it, which is the point.
"""
from __future__ import annotations

import os
from dataclasses import dataclass


def _int(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    # Discord's application public key (hex). This is the one that verifies
    # signatures. Not a secret, but required.
    public_key: str = ""
    # Application (client) ID, shown on the same page as the public key.
    application_id: str = ""
    # Bot token: only needed to register commands. Interactions themselves need
    # no token, which is why an endpoint can work with no long-lived secret.
    bot_token: str = ""
    # Register commands to one guild for instant availability while testing.
    guild_id: str = ""
    # Protects /admin/*. Generate something long and random.
    admin_token: str = ""
    # Incoming webhook URL (the other kind of Discord webhook, for posting into
    # a channel without a bot user). Optional, used by /admin/notify.
    webhook_url: str = ""
    api_base: str = "https://discord.com/api/v10"
    # Reject signatures whose timestamp is further than this from now, which
    # closes the replay window. 0 disables the check.
    timestamp_tolerance: int = 300

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            public_key=os.getenv("DISCORD_PUBLIC_KEY", "").strip(),
            application_id=os.getenv("DISCORD_APPLICATION_ID", "").strip(),
            bot_token=os.getenv("DISCORD_BOT_TOKEN", "").strip(),
            guild_id=os.getenv("DISCORD_GUILD_ID", "").strip(),
            admin_token=os.getenv("ADMIN_TOKEN", "").strip(),
            webhook_url=os.getenv("DISCORD_WEBHOOK_URL", "").strip(),
            api_base=os.getenv("DISCORD_API_BASE", "https://discord.com/api/v10").strip(),
            timestamp_tolerance=_int("DISCORD_TIMESTAMP_TOLERANCE", 300),
        )

    def signature_ready(self) -> bool:
        return bool(self.public_key and self.application_id)
