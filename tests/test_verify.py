"""Signature checking is the whole security model, so it gets its own tests."""
from __future__ import annotations

import time

from bot.verify import verify


def test_a_real_signature_passes(public_hex, signing_key):
    body = b'{"type":1}'
    stamp = str(int(time.time()))
    signature = signing_key.sign(stamp.encode() + body).signature.hex()
    assert verify(public_hex, signature, stamp, body) is True


def test_a_changed_body_fails(public_hex, signing_key):
    stamp = str(int(time.time()))
    signature = signing_key.sign(stamp.encode() + b'{"type":1}').signature.hex()
    assert verify(public_hex, signature, stamp, b'{"type":2}') is False


def test_another_key_cannot_sign_for_us(public_hex):
    from nacl.signing import SigningKey

    stranger = SigningKey.generate()
    body = b'{"type":1}'
    stamp = str(int(time.time()))
    signature = stranger.sign(stamp.encode() + body).signature.hex()
    assert verify(public_hex, signature, stamp, body) is False


def test_malformed_hex_is_rejected_not_crashed(public_hex):
    assert verify(public_hex, "zzzz", "123", b"{}") is False
    assert verify("not-hex", "ab" * 64, "123", b"{}") is False


def test_missing_headers_are_rejected(public_hex):
    assert verify(public_hex, "", "123", b"{}") is False
    assert verify(public_hex, "ab" * 64, "", b"{}") is False
    assert verify("", "ab" * 64, "123", b"{}") is False


def test_a_stale_signature_is_rejected(public_hex, signing_key):
    stamp = str(int(time.time()) - 10_000)
    body = b'{"type":1}'
    signature = signing_key.sign(stamp.encode() + body).signature.hex()
    assert verify(public_hex, signature, stamp, body, tolerance=300) is False


def test_tolerance_zero_disables_the_freshness_check(public_hex, signing_key):
    stamp = str(int(time.time()) - 10_000)
    body = b'{"type":1}'
    signature = signing_key.sign(stamp.encode() + body).signature.hex()
    assert verify(public_hex, signature, stamp, body, tolerance=0) is True


def test_a_non_numeric_timestamp_is_rejected(public_hex, signing_key):
    stamp = "not-a-number"
    body = b"{}"
    signature = signing_key.sign(stamp.encode() + body).signature.hex()
    assert verify(public_hex, signature, stamp, body) is False
