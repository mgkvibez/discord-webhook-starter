"""One file from a cold repo to a live slash command.

Run locally:   uvicorn app:app --reload
Then paste    https://<your public host>/interactions  into
              Developer Portal -> your app -> General Information
              -> Interactions Endpoint URL
Discord will send a PING; the PING/PONG branch below is what makes the box save.
"""
from __future__ import annotations

import hmac
import json
import logging
from typing import Optional

from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from bot import commands as command_defs
from bot import responses as R
from bot import verify as signature
from bot.client import DiscordClient, DiscordError
from bot.config import Settings
from bot.handlers import handle_interaction

log = logging.getLogger("starter")


def create_app(
    settings: Optional[Settings] = None, client: Optional[DiscordClient] = None
) -> FastAPI:
    settings = settings or Settings.from_env()
    bot = client or DiscordClient(settings)

    app = FastAPI(title="Discord Webhook Starter", version="0.1.0")
    app.state.settings = settings
    app.state.bot = bot

    def require_admin(authorization: Optional[str]) -> None:
        if not settings.admin_token:
            raise HTTPException(
                503, "ADMIN_TOKEN is not set, so admin routes are disabled. See the README."
            )
        expected = "Bearer " + settings.admin_token
        if not authorization or not hmac.compare_digest(authorization, expected):
            raise HTTPException(401, "bad or missing bearer token")

    @app.get("/")
    async def home() -> dict:
        return {
            "status": "ok",
            "endpoint": "/interactions",
            "commands": [command["name"] for command in command_defs.COMMANDS],
        }

    @app.get("/health")
    async def health() -> dict:
        return {
            "ok": True,
            "signature_ready": settings.signature_ready(),
            "crypto": signature.CRYPTO_READY,
        }

    @app.post("/interactions")
    async def interactions(
        request: Request,
        background: BackgroundTasks,
        x_signature_ed25519: Optional[str] = Header(default=None),
        x_signature_timestamp: Optional[str] = Header(default=None),
    ):
        if not settings.signature_ready():
            raise HTTPException(
                503,
                "DISCORD_PUBLIC_KEY and DISCORD_APPLICATION_ID are not both set, "
                "so no request can be verified.",
            )
        # Read the raw bytes before parsing: the signature covers these exact bytes.
        body = await request.body()
        if not signature.verify(
            settings.public_key,
            x_signature_ed25519 or "",
            x_signature_timestamp or "",
            body,
            tolerance=settings.timestamp_tolerance,
        ):
            raise HTTPException(401, "invalid request signature")

        try:
            payload = json.loads(body or b"{}")
        except ValueError:
            raise HTTPException(400, "body must be JSON")
        if not isinstance(payload, dict):
            raise HTTPException(400, "body must be a JSON object")

        if payload.get("type") == R.PONG:
            return JSONResponse(R.pong())

        reply = await handle_interaction(payload, settings)
        if reply.followup is not None:
            background.add_task(
                bot.followup,
                settings.application_id,
                str(payload.get("token") or ""),
                reply.followup,
            )
        return JSONResponse(reply.body)

    @app.post("/admin/register-commands")
    async def register_commands(authorization: Optional[str] = Header(default=None)) -> dict:
        require_admin(authorization)
        issues = command_defs.problems()
        if issues:
            raise HTTPException(400, "; ".join(issues))
        try:
            result = await bot.register_commands(command_defs.COMMANDS)
        except DiscordError as exc:
            raise HTTPException(502, str(exc))
        return {"registered": len(command_defs.COMMANDS), "discord_response": result}

    @app.post("/admin/notify")
    async def notify(payload: dict, authorization: Optional[str] = Header(default=None)) -> dict:
        """Post into a channel with an incoming webhook URL, no bot user involved."""
        require_admin(authorization)
        content = str((payload or {}).get("content") or "").strip()
        if not content:
            raise HTTPException(400, "content is required")
        if len(content) > 2000:
            raise HTTPException(400, "content must be 2000 characters or fewer")
        try:
            await bot.post_webhook({"content": content, "username": payload.get("username")})
        except DiscordError as exc:
            raise HTTPException(502, str(exc))
        return {"sent": True}

    return app


app = create_app()
