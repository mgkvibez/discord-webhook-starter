"""Discord rejects invalid command definitions with terse errors, so check locally."""
from __future__ import annotations

from bot import commands


def test_the_shipped_commands_are_valid():
    assert commands.problems() == []


def test_a_bad_name_is_caught(monkeypatch):
    monkeypatch.setattr(
        commands, "COMMANDS", [{"name": "Not Valid!", "description": "x", "type": 1}]
    )
    assert any("must match" in problem for problem in commands.problems())


def test_a_duplicate_name_is_caught(monkeypatch):
    monkeypatch.setattr(
        commands,
        "COMMANDS",
        [
            {"name": "hello", "description": "one", "type": 1},
            {"name": "hello", "description": "two", "type": 1},
        ],
    )
    assert any("twice" in problem for problem in commands.problems())


def test_a_long_description_is_caught(monkeypatch):
    monkeypatch.setattr(
        commands, "COMMANDS", [{"name": "hello", "description": "x" * 101, "type": 1}]
    )
    assert any("1-100" in problem for problem in commands.problems())
