"""Talking back to Discord: register commands, answer late, post to a channel.

Two different things live here on purpose, because beginners conflate them:

* ``register_commands`` and ``followup`` use the application API with the bot
  token or the interaction token. This is the bot.
* ``post_webhook`` uses an *incoming webhook URL*, which posts into a channel
  with no bot user involved at all. Useful for build notifications.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import httpx

from .config import Settings


class DiscordError(RuntimeError):
    """Discord returned an error, or could not be reached."""


def _detail(response: httpx.Response) -> str:
    try:
        text = response.text
    except Exception:  # pragma: no cover
        return "no body"
    return text[:300] if text else "no body"


class DiscordClient:
    def __init__(
        self,
        settings: Settings,
        transport: Optional[httpx.AsyncBaseTransport] = None,
        timeout: float = 10.0,
    ) -> None:
        self.settings = settings
        self._transport = transport
        self._timeout = timeout
        # Useful in tests and for a quick "what did I send" check.
        self.calls: List[Dict[str, Any]] = []

    async def _request(
        self, method: str, path: str, *, payload: Any = None, auth: bool = True
    ) -> Any:
        url = self.settings.api_base.rstrip("/") + path
        headers: Dict[str, str] = {}
        if auth:
            if not self.settings.bot_token:
                raise DiscordError("DISCORD_BOT_TOKEN is not set, so this call cannot be made")
            headers["Authorization"] = "Bot " + self.settings.bot_token
        async with httpx.AsyncClient(transport=self._transport, timeout=self._timeout) as client:
            try:
                response = await client.request(method, url, json=payload, headers=headers)
            except httpx.HTTPError as exc:
                raise DiscordError("could not reach Discord: {}".format(exc)) from exc
        self.calls.append({"method": method, "url": url, "status": response.status_code})
        if response.status_code >= 400:
            raise DiscordError(
                "Discord returned {}: {}".format(response.status_code, _detail(response))
            )
        try:
            return response.json()
        except ValueError:
            return {}

    async def register_commands(self, commands: List[Dict[str, Any]], guild_id: str = "") -> Any:
        """Upload the slash-command definitions.

        Global commands can take an hour to appear; a guild id makes them instant,
        which is why DISCORD_GUILD_ID exists for development.
        """
        guild = guild_id or self.settings.guild_id
        base = "/applications/{}".format(self.settings.application_id)
        path = "{}/guilds/{}/commands".format(base, guild) if guild else base + "/commands"
        return await self._request("PUT", path, payload=commands)

    async def followup(
        self, application_id: str, interaction_token: str, payload: Dict[str, Any]
    ) -> Any:
        """Finish a deferred interaction. The token is the auth, so no bot token."""
        clean = {key: value for key, value in payload.items() if value is not None}
        path = "/webhooks/{}/{}".format(application_id, interaction_token)
        return await self._request("POST", path, payload=clean, auth=False)

    async def post_webhook(self, payload: Dict[str, Any], webhook_url: str = "") -> Any:
        """Post into a channel through an incoming webhook URL."""
        url = webhook_url or self.settings.webhook_url
        if not url:
            raise DiscordError("DISCORD_WEBHOOK_URL is not set")
        clean = {key: value for key, value in payload.items() if value is not None}
        async with httpx.AsyncClient(transport=self._transport, timeout=self._timeout) as client:
            try:
                response = await client.post(url, json=clean)
            except httpx.HTTPError as exc:
                raise DiscordError("could not reach the webhook: {}".format(exc)) from exc
        self.calls.append({"method": "POST", "url": url, "status": response.status_code})
        if response.status_code >= 400:
            raise DiscordError(
                "the webhook returned {}: {}".format(
                    response.status_code, _detail(response)
                )
            )
        try:
            return response.json()
        except ValueError:
            return {}
