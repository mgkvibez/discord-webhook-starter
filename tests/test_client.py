"""The HTTP client, against a mock transport. No Discord account involved."""
from __future__ import annotations

import asyncio

import httpx
import pytest

from bot.client import DiscordClient, DiscordError


def call(coro):
    return asyncio.run(coro)


def make(handler, settings, **kwargs):
    return DiscordClient(settings, transport=httpx.MockTransport(handler), **kwargs)


def test_registering_globally_uses_the_application_route(settings):
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers.get("Authorization")
        return httpx.Response(200, json=[{"id": "1"}])

    client = make(handler, settings)
    call(client.register_commands([{"name": "hello"}]))
    assert seen["url"].endswith("/applications/111111111111111111/commands")
    assert seen["auth"] == "Bot bot-token"


def test_registering_to_a_guild_is_the_instant_path(settings):
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        return httpx.Response(200, json=[])

    client = make(handler, settings)
    call(client.register_commands([{"name": "hello"}], guild_id="555"))
    assert "/guilds/555/commands" in seen["url"]


def test_a_followup_uses_the_interaction_token_and_no_bot_token(settings):
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers.get("Authorization")
        seen["body"] = request.content.decode()
        return httpx.Response(200, json={"id": "2"})

    client = make(handler, settings)
    call(client.followup("111", "tok", {"content": "late", "username": None}))
    assert seen["url"].endswith("/webhooks/111/tok")
    assert seen["auth"] is None
    assert '"username"' not in seen["body"]


def test_posting_to_an_incoming_webhook_works_without_a_bot_token(settings):
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        return httpx.Response(204)

    client = make(handler, settings)
    call(client.post_webhook({"content": "hi"}))
    assert seen["url"] == settings.webhook_url


def test_an_error_status_becomes_a_discord_error(settings):
    client = make(lambda request: httpx.Response(401, text="401: Unauthorized"), settings)
    with pytest.raises(DiscordError) as caught:
        call(client.register_commands([]))
    assert "401" in str(caught.value)


def test_a_network_failure_becomes_a_discord_error(settings):
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no route", request=request)

    client = make(handler, settings)
    with pytest.raises(DiscordError) as caught:
        call(client.register_commands([]))
    assert "could not reach Discord" in str(caught.value)


def test_registering_without_a_bot_token_is_refused_early(settings):
    from dataclasses import replace

    tokenless = replace(settings, bot_token="")
    client = make(lambda request: httpx.Response(200, json=[]), tokenless)
    with pytest.raises(DiscordError) as caught:
        call(client.register_commands([]))
    assert "DISCORD_BOT_TOKEN" in str(caught.value)


def test_posting_without_a_webhook_url_is_refused_early(settings):
    from dataclasses import replace

    client = make(lambda request: httpx.Response(204), replace(settings, webhook_url=""))
    with pytest.raises(DiscordError) as caught:
        call(client.post_webhook({"content": "hi"}))
    assert "DISCORD_WEBHOOK_URL" in str(caught.value)
