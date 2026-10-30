"""Shared fixtures. A real Ed25519 keypair means signatures are actually tested."""
from __future__ import annotations

import json
import time

import pytest
from nacl.signing import SigningKey

from bot.config import Settings


@pytest.fixture
def signing_key() -> SigningKey:
    return SigningKey.generate()


@pytest.fixture
def public_hex(signing_key: SigningKey) -> str:
    return signing_key.verify_key.encode().hex()


@pytest.fixture
def settings(public_hex: str) -> Settings:
    return Settings(
        public_key=public_hex,
        application_id="111111111111111111",
        bot_token="bot-token",
        admin_token="admin-secret",
        webhook_url="https://discord.com/api/webhooks/1/abc",
    )


class RecordingClient:
    """Stands in for Discord. Records what the app tried to send."""

    def __init__(self) -> None:
        self.registered = []
        self.followups = []
        self.posts = []

    async def register_commands(self, commands, guild_id=""):
        self.registered.append({"commands": commands, "guild_id": guild_id})
        return {"ok": True}

    async def followup(self, application_id, interaction_token, payload):
        self.followups.append(
            {"application_id": application_id, "token": interaction_token, "payload": payload}
        )
        return {"ok": True}

    async def post_webhook(self, payload, webhook_url=""):
        self.posts.append(payload)
        return {"ok": True}


def sign(signing_key: SigningKey, timestamp: str, body: bytes) -> str:
    return signing_key.sign(timestamp.encode() + body).signature.hex()


def post_signed(client, signing_key, payload, *, timestamp=None, tamper=False, raw=None):
    stamp = timestamp or str(int(time.time()))
    body = raw if raw is not None else json.dumps(payload).encode()
    signature = sign(signing_key, stamp, body)
    if tamper:
        body = json.dumps({**payload, "type": 99}).encode()
    return client.post(
        "/interactions",
        content=body,
        headers={
            "X-Signature-Ed25519": signature,
            "X-Signature-Timestamp": stamp,
            "Content-Type": "application/json",
        },
    )
