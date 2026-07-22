"""Provider secret encryption helpers."""

from __future__ import annotations

import os

from cryptography.fernet import Fernet, InvalidToken

PROVIDER_ENCRYPTION_KEY_ENV = "SKM_PROVIDER_ENCRYPTION_KEY"
ENCRYPTED_VALUE_PREFIX = "fernet:"


class ProviderSecretError(ValueError):
    """Raised when provider secret encryption cannot be performed safely."""


def generate_provider_secret_key() -> str:
    """Return a new local provider credential encryption key."""

    return Fernet.generate_key().decode("ascii")


def encrypt_provider_secret(plaintext: str) -> str:
    key = _provider_secret_key()
    token = Fernet(key).encrypt(plaintext.encode("utf-8")).decode("ascii")
    return f"{ENCRYPTED_VALUE_PREFIX}{token}"


def decrypt_provider_secret(envelope: str) -> str:
    if not envelope.startswith(ENCRYPTED_VALUE_PREFIX):
        raise ProviderSecretError("provider credential is not encrypted")
    key = _provider_secret_key()
    token = envelope.removeprefix(ENCRYPTED_VALUE_PREFIX).encode("ascii")
    try:
        return Fernet(key).decrypt(token).decode("utf-8")
    except InvalidToken as exc:
        raise ProviderSecretError("provider credential cannot be decrypted") from exc


def _provider_secret_key() -> bytes:
    configured = os.environ.get(PROVIDER_ENCRYPTION_KEY_ENV)
    if configured is None or not configured.strip():
        raise ProviderSecretError(
            f"{PROVIDER_ENCRYPTION_KEY_ENV} must be set before storing "
            "provider credentials"
        )
    key = configured.strip().encode("ascii")
    try:
        Fernet(key)
    except (ValueError, TypeError) as exc:
        raise ProviderSecretError(
            f"{PROVIDER_ENCRYPTION_KEY_ENV} must be a valid Fernet key"
        ) from exc
    return key
