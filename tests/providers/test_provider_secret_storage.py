from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest

import backend.providers.service as provider_service_module
from backend.providers import ProviderError, ProviderService, ProviderSettingsInput
from backend.providers.secrets import (
    decrypt_provider_secret,
    generate_provider_secret_key,
)


ACTOR_ID = UUID("11111111-1111-1111-1111-111111111111")
NOW = datetime(2026, 7, 22, tzinfo=UTC)


class FakeResult:
    def __init__(self, row: dict[str, object] | None = None) -> None:
        self._row = row

    def fetchone(self) -> dict[str, object] | None:
        return self._row


class FakeTransaction:
    def __enter__(self) -> FakeTransaction:
        return self

    def __exit__(self, *_: object) -> None:
        return None


class ProviderConfigurationConnection:
    def __init__(self) -> None:
        self.stored_secret: str | None = None
        self.audit_metadata: object | None = None

    def __enter__(self) -> ProviderConfigurationConnection:
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def transaction(self) -> FakeTransaction:
        return FakeTransaction()

    def execute(
        self, query: str, params: tuple[object, ...] | None = None
    ) -> FakeResult:
        normalized = " ".join(query.split())
        if normalized.startswith("INSERT INTO provider_configurations"):
            assert params is not None
            assert isinstance(params[2], str)
            self.stored_secret = params[2]  # api_key_secret insert value
            return FakeResult(
                {
                    "provider": params[0],
                    "endpoint_url": params[1],
                    "manual_models": ["gpt-4.1-mini"],
                    "api_key_secret": self.stored_secret,
                    "updated_at": NOW,
                }
            )
        if normalized.startswith("INSERT INTO audit_events"):
            assert params is not None
            self.audit_metadata = params[5]
            return FakeResult()
        raise AssertionError(f"unexpected query: {normalized}")


class FailingConnection:
    def __enter__(self) -> FailingConnection:
        raise AssertionError("database must not be opened without an encryption key")

    def __exit__(self, *_: object) -> None:
        return None


def test_openai_api_key_is_encrypted_before_database_storage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_connection = ProviderConfigurationConnection()
    plaintext = "sk-review-regression-secret"
    monkeypatch.setenv("SKM_PROVIDER_ENCRYPTION_KEY", generate_provider_secret_key())
    monkeypatch.setattr(
        provider_service_module,
        "open_database_connection",
        lambda _: fake_connection,
    )

    configuration = ProviderService().upsert_configuration(
        ProviderSettingsInput(
            provider="openai",
            api_key=plaintext,
            manual_models=["gpt-4.1-mini"],
        ),
        actor_user_id=ACTOR_ID,
    )

    assert configuration.api_key_set is True
    assert fake_connection.stored_secret is not None
    assert fake_connection.stored_secret != plaintext
    assert fake_connection.stored_secret.startswith("fernet:")
    assert decrypt_provider_secret(fake_connection.stored_secret) == plaintext


def test_openai_api_key_storage_requires_configured_encryption_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SKM_PROVIDER_ENCRYPTION_KEY", raising=False)
    monkeypatch.setattr(
        provider_service_module,
        "open_database_connection",
        lambda _: FailingConnection(),
    )

    with pytest.raises(ProviderError, match="SKM_PROVIDER_ENCRYPTION_KEY"):
        ProviderService().upsert_configuration(
            ProviderSettingsInput(
                provider="openai",
                api_key="sk-review-regression-secret",
                manual_models=["gpt-4.1-mini"],
            ),
            actor_user_id=ACTOR_ID,
        )
