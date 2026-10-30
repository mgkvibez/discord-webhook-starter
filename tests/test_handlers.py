"""One test per branch of the handler, because each branch is one user-visible path."""
from __future__ import annotations

import asyncio

from bot.handlers import handle_interaction


def run(payload, settings):
    return asyncio.run(handle_interaction(payload, settings))


def test_hello_mentions_the_user_and_offers_a_button(settings):
    reply = run({"type": 2, "data": {"name": "hello"}, "member": {"user": {"id": "9"}}}, settings)
    assert reply.body["type"] == 4
    assert reply.body["data"]["content"].startswith("Hi <@9>!")
    assert reply.body["data"]["components"][0]["components"][0]["type"] == 2
    assert reply.body.get("flags") != 64


def test_hello_works_for_a_dm_where_member_is_absent(settings):
    reply = run({"type": 2, "data": {"name": "hello"}, "user": {"id": "9"}}, settings)
    assert "<@9>" in reply.body["data"]["content"]


def test_ping_says_pong(settings):
    reply = run({"type": 2, "data": {"name": "ping"}}, settings)
    assert reply.body["type"] == 4
    assert "Pong" in reply.body["data"]["content"]


def test_slow_defers_and_carries_a_followup(settings):
    reply = run({"type": 2, "data": {"name": "slow"}, "token": "t"}, settings)
    assert reply.body["type"] == 5
    assert reply.followup is not None
    assert "three seconds" in reply.followup["content"]


def test_an_unwired_command_is_answered_privately(settings):
    reply = run({"type": 2, "data": {"name": "unwired"}}, settings)
    assert reply.body["type"] == 4
    assert reply.body["data"]["flags"] == 64
    assert "handlers.py" in reply.body["data"]["content"]


def test_a_button_click_is_answered(settings):
    reply = run({"type": 3, "data": {"custom_id": "hello:again"}}, settings)
    assert reply.body["data"]["flags"] == 64
    assert "type 3" in reply.body["data"]["content"]


def test_an_unknown_component_is_answered(settings):
    reply = run({"type": 3, "data": {"custom_id": "nope"}}, settings)
    assert "Unknown component" in reply.body["data"]["content"]


def test_an_unknown_interaction_type_does_not_crash(settings):
    reply = run({"type": 99}, settings)
    assert reply.body["type"] == 4
    assert reply.body["data"]["flags"] == 64


def test_command_names_are_matched_case_insensitively(settings):
    reply = run({"type": 2, "data": {"name": "PING"}}, settings)
    assert "Pong" in reply.body["data"]["content"]
