"""Prove a request really came from Discord.

Discord signs every interaction with Ed25519, over `timestamp + body`, and shows
you a public key to check it with. Two details trip people up:

1. The body must be the exact bytes Discord sent, before any parsing.
2. The endpoint has to answer Discord's `PING` with a `PONG` *and* a valid
   signature, or the "Interactions Endpoint URL" box refuses to save.

Verification is mandatory, not hardening: without it anyone can POST fake
commands to your app.
"""
from __future__ import annotations

import time
from typing import Optional

try:  # PyNaCl is the library Discord's own Python examples use.
    from nacl.exceptions import BadSignatureError
    from nacl.signing import VerifyKey

    CRYPTO_READY = True
except Exception:  # pragma: no cover - only on an install missing the dependency
    CRYPTO_READY = False
    BadSignatureError = Exception  # type: ignore[assignment,misc]
    VerifyKey = None  # type: ignore[assignment]


def verify(
    public_key_hex: str,
    signature_hex: str,
    timestamp: str,
    body: bytes,
    *,
    tolerance: int = 300,
    now: Optional[float] = None,
) -> bool:
    """True only for a signature Discord could have produced for this body."""
    if not CRYPTO_READY:
        raise RuntimeError(
            "PyNaCl is required to verify Discord signatures. Install it with "
            "`pip install pynacl`."
        )
    if not (public_key_hex and signature_hex and timestamp):
        return False

    if tolerance and tolerance > 0:
        try:
            signed_at = int(timestamp)
        except (TypeError, ValueError):
            return False
        current = time.time() if now is None else now
        if abs(current - signed_at) > tolerance:
            return False

    try:
        key = VerifyKey(bytes.fromhex(public_key_hex))
        key.verify(timestamp.encode() + body, bytes.fromhex(signature_hex))
    except (BadSignatureError, ValueError, TypeError):
        return False
    return True
