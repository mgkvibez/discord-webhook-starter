"""End-to-end through the ASGI app, with real signatures and no network."""
from __future__ import annotations

import json
import time

import pytest
from fastapi.testclient import TestClient

from app import create_app
from bot.config import Settings
from tests.conftest import RecordingClient, post_signed


@pytest.fixture
def fake():
    return RecordingClient()


@pytest.fixture
def client(settings, fake):
    return TestClient(create_app(settings, fake))


def test_home_lists_the_commands(client):
    body = client.get("/").json()
    assert body["endpoint"] == "/interactions"
    assert body["commands"] == ["hello", "ping", "slow"]


def test_health_reports_ready(client):
    body = client.get("/health").json()
    assert body["ok"] is True
    assert body["signature_ready"] is True
    assert body["crypto"] is True


def test_health_reports_not_ready_without_a_key():
    askew = TestClient(create_app(Settings(), RecordingClient()))
    assert askew.get("/health").json()["signature_ready"] is False


def test_without_a_public_key_the_endpoint_refuses():
    askew = TestClient(create_app(Settings(), RecordingClient()))
    response = askew.post("/interactions", json={"type": 1})
    assert response.status_code == 503


def test_an_unsigned_request_is_rejected(client):
    response = client.post("/interactions", json={"type": 1})
    assert response.status_code == 401


def test_a_forged_signature_is_rejected(client):
    from nacl.signing import SigningKey

    stamp = str(int(time.time()))
    body = json.dumps({"type": 1}).encode()
    signature = SigningKey.generate().sign(stamp.encode() + body).signature.hex()
    response = client.post(
        "/interactions",
        content=body,
        headers={"X-Signature-Ed25519": signature, "X-Signature-Timestamp": stamp},
    )
    assert response.status_code == 401


def test_a_tampered_body_is_rejected(client, signing_key):
    response = post_signed(client, signing_key, {"type": 2}, tamper=True)
    assert response.status_code == 401


def test_a_stale_signature_is_rejected(client, signing_key):
    response = post_signed(client, signing_key, {"type": 1}, timestamp=str(int(time.time()) - 9999))
    assert response.status_code == 401


def test_ping_is_answered_with_pong(client, signing_key):
    response = post_signed(client, signing_key, {"type": 1, "id": "1"})
    assert response.status_code == 200
    assert response.json() == {"type": 1}


def test_json_that_is_not_an_object_is_rejected(client, signing_key):
    response = post_signed(client, signing_key, None, raw=b"[]")
    assert response.status_code == 400


def test_broken_json_is_rejected(client, signing_key):
    response = post_signed(client, signing_key, None, raw=b"not json")
    assert response.status_code == 400


def test_the_hello_command_returns_a_message_with_a_button(client, signing_key):
    response = post_signed(
        client,
        signing_key,
        {"type": 2, "data": {"name": "hello"}, "member": {"user": {"id": "42"}}},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["type"] == 4
    assert "<@42>" in body["data"]["content"]
    assert body["data"]["components"][0]["components"][0]["url"].startswith("https://")


def test_the_slow_command_defers_then_follows_up(client, signing_key, fake):
    response = post_signed(
        client, signing_key, {"type": 2, "data": {"name": "slow"}, "token": "tok-1"}
    )
    assert response.json()["type"] == 5
    assert len(fake.followups) == 1
    assert fake.followups[0]["token"] == "tok-1"
    assert "Done" in fake.followups[0]["payload"]["content"]


def test_admin_routes_need_a_configured_token():
    askew = TestClient(create_app(Settings(public_key="ab" * 32, application_id="1"), RecordingClient()))
    assert askew.post("/admin/register-commands").status_code == 503


def test_admin_routes_reject_a_wrong_bearer(client):
    response = client.post("/admin/register-commands", headers={"Authorization": "Bearer nope"})
    assert response.status_code == 401


def test_register_commands_reports_what_it_sent(client, fake):
    response = client.post(
        "/admin/register-commands", headers={"Authorization": "Bearer admin-secret"}
    )
    assert response.status_code == 200
    assert response.json()["registered"] == 3
    assert [command["name"] for command in fake.registered[0]["commands"]] == ["hello", "ping", "slow"]


def test_notify_requires_content(client):
    response = client.post(
        "/admin/notify", json={}, headers={"Authorization": "Bearer admin-secret"}
    )
    assert response.status_code == 400


def test_notify_posts_into_the_channel(client, fake):
    response = client.post(
        "/admin/notify",
        json={"content": "deploy finished"},
        headers={"Authorization": "Bearer admin-secret"},
    )
    assert response.status_code == 200
    assert fake.posts == [{"content": "deploy finished", "username": None}]
