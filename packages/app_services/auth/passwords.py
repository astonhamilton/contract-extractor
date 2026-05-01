from __future__ import annotations

import base64
import hashlib
import hmac
import secrets


PBKDF2_SCHEME = "pbkdf2_sha256"
PBKDF2_ITERATIONS = 600_000
PBKDF2_SALT_BYTES = 16


def hash_password(password: str) -> str:
    """Return a PBKDF2-SHA256 password hash string."""

    salt = secrets.token_bytes(PBKDF2_SALT_BYTES)
    derived_key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
    )
    return "$".join(
        [
            PBKDF2_SCHEME,
            str(PBKDF2_ITERATIONS),
            base64.b64encode(salt).decode("ascii"),
            base64.b64encode(derived_key).decode("ascii"),
        ]
    )


def verify_password(password: str, password_hash: str) -> bool:
    """Return whether a password matches one stored PBKDF2-SHA256 hash."""

    try:
        scheme, iterations_raw, salt_b64, digest_b64 = password_hash.split("$", 3)
    except ValueError:
        return False
    if scheme != PBKDF2_SCHEME:
        return False
    try:
        iterations = int(iterations_raw)
        salt = base64.b64decode(salt_b64)
        expected_digest = base64.b64decode(digest_b64)
    except Exception:  # noqa: BLE001
        return False
    candidate_digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations,
    )
    return hmac.compare_digest(candidate_digest, expected_digest)
