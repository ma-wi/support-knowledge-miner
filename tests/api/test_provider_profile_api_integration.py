from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from backend.api import create_app
from backend.auth import CurrentUser
from backend.auth.service import AuthenticationError
from backend.providers import (
    ProviderCheckResult,
    ProviderConfiguration,
    ProviderError,
    ProviderSettingsInput,
)


OWNER_ID = UUID("11111111-1111-1111-1111-111111111111")
PROJECT_ID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
NOW = datetime(2026, 7, 22, tzinfo=UTC)


class FakeAuthService:
    def seed_initial_user_from_env(self) -> None:
        return None

    def authenticate_token(self, token: str) -> CurrentUser:
        if token != "valid-token":
            raise AuthenticationError("invalid or expired session")
        return CurrentUser(
            id=OWNER_ID,
            first_name="Local",
            last_name="Owner",
            email="owner@example.test",
            created_at=NOW,
            updated_at=NOW,
            session_id=uuid4(),
        )


class FakeProviderService:
    def __init__(self) -> None:
        self.configurations: dict[str, ProviderConfiguration] = {}
        self.received_api_key: str | None = None

    def list_configurations(self) -> list[ProviderConfiguration]:
        return list(self.configurations.values())

    def seed_ollama_provider_from_env(self) -> None:
        return None

    def upsert_configuration(
        self,
        payload: ProviderSettingsInput,
        *,
        actor_user_id: UUID,
    ) -> ProviderConfiguration:
        assert actor_user_id == OWNER_ID
        self.received_api_key = payload.api_key
        api_key_set = payload.provider == "openai" and not payload.remove_api_key
        configuration = ProviderConfiguration(
            provider=payload.provider,
            endpoint_url=payload.endpoint_url,
            manual_models=payload.manual_models or [],
            api_key_set=api_key_set,
            updated_at=NOW,
        )
        self.configurations[payload.provider] = configuration
        return configuration

    def check_provider(self, provider: str) -> ProviderCheckResult:
        if provider not in self.configurations:
            raise ProviderError("provider is not configured")
        return ProviderCheckResult(
            provider=provider,
            ok=True,
            models=self.configurations[provider].manual_models,
            message="provider reachable",
        )

    def pull_ollama_model(
        self, model: str, *, actor_user_id: UUID
    ) -> ProviderConfiguration:
        assert actor_user_id == OWNER_ID
        if "ollama" not in self.configurations:
            raise ProviderError("ollama provider is not configured")
        existing = self.configurations["ollama"]
        models = [*existing.manual_models]
        if model not in models:
            models.append(model)
        configuration = ProviderConfiguration(
            provider="ollama",
            endpoint_url=existing.endpoint_url,
            manual_models=models,
            api_key_set=False,
            updated_at=NOW,
        )
        self.configurations["ollama"] = configuration
        return configuration


@pytest.fixture
def fake_provider_service() -> FakeProviderService:
    return FakeProviderService()


@pytest.fixture
def client(fake_provider_service: FakeProviderService) -> TestClient:
    return TestClient(
        create_app(
            auth_service=FakeAuthService(),  # type: ignore[arg-type]
            provider_service=fake_provider_service,  # type: ignore[arg-type]
        )
    )


def auth_headers(token: str = "valid-token") -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_provider_routes_require_authentication(client: TestClient) -> None:
    assert client.get("/api/providers").status_code == 401
    assert client.put("/api/providers/openai", json={}).status_code == 401


def test_openai_provider_key_is_write_only_in_api_responses(
    client: TestClient, fake_provider_service: FakeProviderService
) -> None:
    response = client.put(
        "/api/providers/openai",
        headers=auth_headers(),
        json={
            "api_key": "sk-test-secret",
            "manual_models": ["text-embedding-3-small", "gpt-4.1-mini"],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["api_key_set"] is True
    assert payload["manual_models"] == ["text-embedding-3-small", "gpt-4.1-mini"]
    assert "sk-test-secret" not in str(payload)
    assert fake_provider_service.received_api_key == "sk-test-secret"

    listed = client.get("/api/providers", headers=auth_headers())
    assert listed.status_code == 200
    assert listed.json()[0]["api_key_set"] is True
    assert "sk-test-secret" not in str(listed.json())

    removed = client.put(
        "/api/providers/openai",
        headers=auth_headers(),
        json={"remove_api_key": True, "manual_models": ["gpt-4.1-mini"]},
    )
    assert removed.status_code == 200
    assert removed.json()["api_key_set"] is False


def test_vllm_provider_check_and_removed_project_profile_contract(
    client: TestClient,
) -> None:
    configured = client.put(
        "/api/providers/vllm",
        headers=auth_headers(),
        json={
            "endpoint_url": "http://localhost:8000",
            "manual_models": ["local-embed", "local-chat"],
        },
    )
    assert configured.status_code == 200

    check = client.post("/api/providers/vllm/check", headers=auth_headers())
    assert check.status_code == 200
    assert check.json()["models"] == ["local-embed", "local-chat"]

    created = client.post(
        f"/api/projects/{PROJECT_ID}/analysis-profiles",
        headers=auth_headers(),
        json={
            "name": "Local clustering",
            "provider": "vllm",
            "model": "local-embed",
            "thresholds": {"similarity": 0.78},
            "algorithm_settings": {"algorithm": "hdbscan"},
        },
    )
    assert created.status_code == 404

    listed = client.get(
        f"/api/projects/{PROJECT_ID}/analysis-profiles", headers=auth_headers()
    )
    assert listed.status_code == 404


def test_ollama_provider_check_and_pull_contract(client: TestClient) -> None:
    configured = client.put(
        "/api/providers/ollama",
        headers=auth_headers(),
        json={
            "endpoint_url": "http://localhost:11434",
            "manual_models": ["nomic-embed-text", "mxbai-embed-large"],
        },
    )
    assert configured.status_code == 200
    assert configured.json()["provider"] == "ollama"
    assert configured.json()["api_key_set"] is False

    check = client.post("/api/providers/ollama/check", headers=auth_headers())
    assert check.status_code == 200
    assert check.json()["models"] == ["nomic-embed-text", "mxbai-embed-large"]

    pulled = client.post(
        "/api/providers/ollama/pull",
        headers=auth_headers(),
        json={"model": "all-minilm"},
    )
    assert pulled.status_code == 200
    assert pulled.json()["manual_models"] == [
        "nomic-embed-text",
        "mxbai-embed-large",
        "all-minilm",
    ]


def test_provider_errors_are_safe(client: TestClient) -> None:
    response = client.post("/api/providers/vllm/check", headers=auth_headers())

    assert response.status_code == 400
    assert response.json()["detail"] == "provider is not configured"
