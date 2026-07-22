"""Password hashing helpers using Argon2id."""

from __future__ import annotations

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError

_PASSWORD_HASHER = PasswordHasher()


def hash_password(password: str) -> str:
    """Hash a plaintext password with Argon2id."""

    if not password:
        raise ValueError("password must not be empty")
    return _PASSWORD_HASHER.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a plaintext password against a stored hash."""

    try:
        return _PASSWORD_HASHER.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError):
        return False
