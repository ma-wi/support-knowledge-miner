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
    ProviderDeleteBlocked,
    ProviderError,
    ProviderSettingsInput,
)


OWNER_ID = UUID("11111111-1111-1111-1111-111111111111")
PROJECT_ID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
OPENAI_ID = UUID("00000000-0000-0000-0000-000000000001")
OLLAMA_ID = UUID("00000000-0000-0000-0000-000000000002")
NOW = datetime(2026, 7, 22, tzinfo=UTC)


def _unique_models(*model_lists: list[str]) -> list[str]:
    models: list[str] = []
    seen: set[str] = set()
    for model_list in model_lists:
        for model in model_list:
            if model not in seen:
                seen.add(model)
                models.append(model)
    return models


def _openai_embedding_models(models: list[str]) -> list[str]:
    return [model for model in models if model.casefold().startswith("text-embedding-")]


def _openai_llm_models(models: list[str]) -> list[str]:
    return [
        model
        for model in models
        if model.casefold() == "o4-mini"
        or model.casefold().startswith("gpt-4.1")
        or model.casefold().startswith("gpt-4o")
        or model.casefold().startswith("gpt-5")
    ]


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
        self.configurations: dict[UUID, ProviderConfiguration] = {}
        self.received_api_key: str | None = None
        self.blocked_deletes: set[UUID] = set()

    def list_configurations(self) -> list[ProviderConfiguration]:
        return list(self.configurations.values())

    def list_llm_configurations(self) -> list[ProviderConfiguration]:
        return [
            configuration
            for configuration in self.configurations.values()
            if configuration.llm_models
        ]

    def seed_ollama_provider_from_env(self) -> None:
        return None

    def create_configuration(
        self, provider: str, *, actor_user_id: UUID
    ) -> ProviderConfiguration:
        assert actor_user_id == OWNER_ID
        if provider not in {"openai", "ollama"}:
            raise ProviderError("provider must be openai or ollama")
        suffix = 1 + sum(
            1
            for configuration in self.configurations.values()
            if configuration.provider == provider
        )
        provider_id = uuid4()
        base_name = "OpenAI" if provider == "openai" else "Ollama"
        configuration = ProviderConfiguration(
            id=provider_id,
            provider=provider,
            display_name=base_name if suffix == 1 else f"{base_name} {suffix}",
            endpoint_url="http://localhost:11434/" if provider == "ollama" else None,
            available_models=[],
            manual_models=[],
            llm_models=[],
            api_key_set=False,
            updated_at=NOW,
        )
        self.configurations[provider_id] = configuration
        return configuration

    def upsert_configuration(
        self,
        payload: ProviderSettingsInput,
        *,
        actor_user_id: UUID,
    ) -> ProviderConfiguration:
        assert actor_user_id == OWNER_ID
        self.received_api_key = payload.api_key
        if payload.provider not in {"openai", "ollama"}:
            raise ProviderError("provider must be openai or ollama")
        existing = next(
            (
                configuration
                for configuration in self.configurations.values()
                if configuration.provider == payload.provider
            ),
            None,
        )
        manual_models = (
            payload.manual_models
            if payload.manual_models is not None
            else existing.manual_models
            if existing is not None
            else []
        )
        llm_models = (
            payload.llm_models
            if payload.llm_models is not None
            else existing.llm_models
            if existing is not None
            else []
        )
        if payload.provider == "openai":
            manual_models = _openai_embedding_models(manual_models)
            llm_models = _openai_llm_models(llm_models)
        available_models = _unique_models(
            payload.available_models
            if payload.available_models is not None
            else existing.available_models
            if existing is not None
            else [],
            manual_models,
            llm_models,
        )
        api_key_set = (
            existing.api_key_set
            if existing is not None
            and payload.api_key is None
            and not payload.remove_api_key
            else payload.provider == "openai" and payload.api_key is not None
        )
        provider_id = (
            existing.id
            if existing is not None
            else (OPENAI_ID if payload.provider == "openai" else OLLAMA_ID)
        )
        configuration = ProviderConfiguration(
            id=provider_id,
            provider=payload.provider,
            display_name=payload.display_name
            or (
                existing.display_name
                if existing is not None
                else "OpenAI"
                if payload.provider == "openai"
                else "Ollama"
            ),
            endpoint_url=payload.endpoint_url,
            available_models=available_models,
            manual_models=manual_models,
            llm_models=llm_models,
            api_key_set=api_key_set,
            updated_at=NOW,
        )
        self.configurations[provider_id] = configuration
        return configuration

    def update_configuration(
        self,
        provider_id: UUID,
        payload: ProviderSettingsInput,
        *,
        actor_user_id: UUID,
    ) -> ProviderConfiguration:
        assert actor_user_id == OWNER_ID
        self.received_api_key = payload.api_key
        existing = self.configurations.get(provider_id)
        if existing is None:
            raise ProviderError("provider is not configured")
        provider = payload.provider.strip() or existing.provider
        if provider != existing.provider:
            raise ProviderError("provider type cannot be changed")
        manual_models = (
            payload.manual_models
            if payload.manual_models is not None
            else existing.manual_models
        )
        llm_models = (
            payload.llm_models
            if payload.llm_models is not None
            else existing.llm_models
        )
        if provider == "openai":
            manual_models = _openai_embedding_models(manual_models)
            llm_models = _openai_llm_models(llm_models)
        available_models = _unique_models(
            payload.available_models
            if payload.available_models is not None
            else existing.available_models,
            manual_models,
            llm_models,
        )
        configuration = ProviderConfiguration(
            id=provider_id,
            provider=provider,
            display_name=payload.display_name or existing.display_name,
            endpoint_url=existing.endpoint_url
            if payload.preserve_endpoint_url
            else payload.endpoint_url,
            available_models=available_models,
            manual_models=manual_models,
            llm_models=llm_models,
            api_key_set=(
                existing.api_key_set
                if payload.api_key is None and not payload.remove_api_key
                else payload.api_key is not None
            ),
            updated_at=NOW,
        )
        self.configurations[provider_id] = configuration
        return configuration

    def delete_configuration(self, provider_id: UUID, *, actor_user_id: UUID) -> None:
        assert actor_user_id == OWNER_ID
        if provider_id in self.blocked_deletes:
            raise ProviderDeleteBlocked("provider is still used by active jobs")
        if provider_id not in self.configurations:
            raise ProviderError("provider is not configured")
        del self.configurations[provider_id]

    def _configuration_by_ref(self, provider_ref: UUID | str) -> ProviderConfiguration:
        try:
            provider_id = (
                provider_ref
                if isinstance(provider_ref, UUID)
                else UUID(str(provider_ref))
            )
        except ValueError:
            provider_id = None
        if provider_id is not None and provider_id in self.configurations:
            return self.configurations[provider_id]
        for configuration in self.configurations.values():
            if configuration.provider == str(provider_ref):
                return configuration
        raise ProviderError("provider is not configured")

    def check_provider(self, provider_ref: UUID | str) -> ProviderCheckResult:
        try:
            configuration = self._configuration_by_ref(provider_ref)
        except ProviderError:
            raise ProviderError("provider is not configured")
        return ProviderCheckResult(
            id=configuration.id,
            provider=configuration.provider,
            ok=True,
            models=configuration.available_models,
            embedding_models=configuration.manual_models,
            llm_models=configuration.llm_models,
            message="provider reachable",
        )

    def pull_ollama_model(
        self, provider_ref: UUID | str, model: str, *, actor_user_id: UUID
    ) -> ProviderConfiguration:
        assert actor_user_id == OWNER_ID
        existing = self._configuration_by_ref(provider_ref)
        if existing.provider != "ollama":
            raise ProviderError("model pull is only available for ollama")
        models = [*existing.available_models]
        if model not in models:
            models.append(model)
        configuration = ProviderConfiguration(
            id=existing.id,
            provider="ollama",
            display_name=existing.display_name,
            endpoint_url=existing.endpoint_url,
            available_models=models,
            manual_models=existing.manual_models,
            llm_models=existing.llm_models,
            api_key_set=False,
            updated_at=NOW,
        )
        self.configurations[existing.id] = configuration
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
    assert client.post("/api/providers", json={"provider": "openai"}).status_code == 401
    assert client.get("/api/llm-providers").status_code == 401
    assert client.put("/api/providers/openai", json={}).status_code == 401
    assert client.delete(f"/api/providers/{OPENAI_ID}").status_code == 401
    assert client.put("/api/llm-providers/openai", json={}).status_code == 401


def test_provider_instances_can_be_created_and_deleted(
    client: TestClient,
) -> None:
    created = client.post(
        "/api/providers",
        headers=auth_headers(),
        json={"provider": "ollama"},
    )

    assert created.status_code == 201
    payload = created.json()
    assert payload["id"]
    assert payload["provider"] == "ollama"
    assert payload["display_name"] == "Ollama"
    assert payload["available_models"] == []
    assert "supports_embedding" not in payload
    assert "supports_llm" not in payload

    removed = client.delete(
        f"/api/providers/{payload['id']}",
        headers=auth_headers(),
    )
    assert removed.status_code == 204

    listed = client.get("/api/providers", headers=auth_headers())
    assert listed.status_code == 200
    assert listed.json() == []


def test_provider_delete_is_blocked_when_active_jobs_reference_instance(
    client: TestClient,
    fake_provider_service: FakeProviderService,
) -> None:
    created = client.post(
        "/api/providers",
        headers=auth_headers(),
        json={"provider": "ollama"},
    )
    assert created.status_code == 201
    provider_id = UUID(created.json()["id"])
    fake_provider_service.blocked_deletes.add(provider_id)

    removed = client.delete(
        f"/api/providers/{provider_id}",
        headers=auth_headers(),
    )

    assert removed.status_code == 409
    assert removed.json()["code"] == "PROVIDER_DELETE_BLOCKED"
    assert provider_id in fake_provider_service.configurations


def test_openai_provider_key_is_write_only_in_api_responses(
    client: TestClient, fake_provider_service: FakeProviderService
) -> None:
    legacy = client.put(
        "/api/providers/openai",
        headers=auth_headers(),
        json={"manual_models": ["text-embedding-3-small"]},
    )
    assert legacy.status_code == 422
    assert legacy.json()["code"] == "VALIDATION_FAILED"

    created = client.post(
        "/api/providers",
        headers=auth_headers(),
        json={"provider": "openai"},
    )
    assert created.status_code == 201
    provider_id = created.json()["id"]

    response = client.put(
        f"/api/providers/{provider_id}",
        headers=auth_headers(),
        json={
            "api_key": "sk-test-secret",
            "manual_models": ["text-embedding-3-small", "gpt-4.1-mini"],
            "llm_models": ["gpt-4.1-mini"],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["api_key_set"] is True
    assert payload["available_models"] == [
        "text-embedding-3-small",
        "gpt-4.1-mini",
    ]
    assert payload["manual_models"] == ["text-embedding-3-small"]
    assert payload["llm_models"] == ["gpt-4.1-mini"]
    assert "sk-test-secret" not in str(payload)
    assert fake_provider_service.received_api_key == "sk-test-secret"

    listed = client.get("/api/providers", headers=auth_headers())
    assert listed.status_code == 200
    assert listed.json()[0]["api_key_set"] is True
    assert "sk-test-secret" not in str(listed.json())

    llm_listed = client.get("/api/llm-providers", headers=auth_headers())
    assert llm_listed.status_code == 200
    assert llm_listed.json()[0]["llm_models"] == ["gpt-4.1-mini"]

    removed = client.put(
        f"/api/providers/{provider_id}",
        headers=auth_headers(),
        json={
            "remove_api_key": True,
            "manual_models": ["text-embedding-3-small"],
            "llm_models": ["gpt-4.1-mini"],
        },
    )
    assert removed.status_code == 200
    assert removed.json()["api_key_set"] is False


def test_llm_provider_route_preserves_embedding_models(
    client: TestClient,
) -> None:
    created = client.post(
        "/api/providers",
        headers=auth_headers(),
        json={"provider": "ollama"},
    )
    assert created.status_code == 201
    provider_id = created.json()["id"]

    configured = client.put(
        f"/api/providers/{provider_id}",
        headers=auth_headers(),
        json={
            "endpoint_url": "http://localhost:11434",
            "manual_models": ["nomic-embed-text"],
        },
    )
    assert configured.status_code == 200

    legacy = client.put(
        "/api/llm-providers/ollama",
        headers=auth_headers(),
        json={
            "endpoint_url": "http://localhost:11434",
            "llm_models": ["llama3.1"],
        },
    )
    assert legacy.status_code == 422
    assert legacy.json()["code"] == "VALIDATION_FAILED"

    llm_configured = client.put(
        f"/api/providers/{provider_id}",
        headers=auth_headers(),
        json={
            "provider": "ollama",
            "endpoint_url": "http://localhost:11434",
            "llm_models": ["llama3.1"],
        },
    )

    assert llm_configured.status_code == 200
    payload = llm_configured.json()
    assert payload["manual_models"] == ["nomic-embed-text"]
    assert payload["llm_models"] == ["llama3.1"]
    assert payload["available_models"] == ["nomic-embed-text", "llama3.1"]


def test_partial_provider_update_preserves_endpoint_and_models(
    client: TestClient,
) -> None:
    created = client.post(
        "/api/providers",
        headers=auth_headers(),
        json={"provider": "ollama"},
    )
    assert created.status_code == 201
    provider_id = created.json()["id"]

    configured = client.put(
        f"/api/providers/{provider_id}",
        headers=auth_headers(),
        json={
            "provider": "ollama",
            "endpoint_url": "http://localhost:11434",
            "manual_models": ["nomic-embed-text"],
            "llm_models": ["llama3.1"],
        },
    )
    assert configured.status_code == 200

    renamed = client.put(
        f"/api/providers/{provider_id}",
        headers=auth_headers(),
        json={"display_name": "Server Ollama"},
    )

    assert renamed.status_code == 200
    payload = renamed.json()
    assert payload["display_name"] == "Server Ollama"
    assert payload["endpoint_url"] == "http://localhost:11434"
    assert payload["manual_models"] == ["nomic-embed-text"]
    assert payload["llm_models"] == ["llama3.1"]
    assert payload["available_models"] == ["nomic-embed-text", "llama3.1"]


def test_vllm_provider_is_rejected_and_removed_project_profile_contract(
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
    assert configured.status_code == 422

    check = client.post("/api/providers/vllm/check", headers=auth_headers())
    assert check.status_code == 422
    assert check.json()["code"] == "VALIDATION_FAILED"

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
    created = client.post(
        "/api/providers",
        headers=auth_headers(),
        json={"provider": "ollama"},
    )
    assert created.status_code == 201
    provider_id = created.json()["id"]

    configured = client.put(
        f"/api/providers/{provider_id}",
        headers=auth_headers(),
        json={
            "endpoint_url": "http://localhost:11434",
            "manual_models": ["nomic-embed-text", "mxbai-embed-large"],
        },
    )
    assert configured.status_code == 200
    assert configured.json()["provider"] == "ollama"
    assert configured.json()["api_key_set"] is False

    check = client.post(f"/api/providers/{provider_id}/check", headers=auth_headers())
    assert check.status_code == 200
    assert check.json()["models"] == ["nomic-embed-text", "mxbai-embed-large"]
    assert check.json()["embedding_models"] == ["nomic-embed-text", "mxbai-embed-large"]

    pulled = client.post(
        f"/api/providers/{provider_id}/ollama/pull",
        headers=auth_headers(),
        json={"model": "all-minilm"},
    )
    assert pulled.status_code == 200
    assert pulled.json()["available_models"] == [
        "nomic-embed-text",
        "mxbai-embed-large",
        "all-minilm",
    ]
    assert pulled.json()["manual_models"] == [
        "nomic-embed-text",
        "mxbai-embed-large",
    ]

    legacy_pull = client.post(
        "/api/providers/ollama/pull",
        headers=auth_headers(),
        json={"model": "second"},
    )
    assert legacy_pull.status_code == 422
    assert legacy_pull.json()["code"] == "VALIDATION_FAILED"


def test_provider_errors_are_safe(client: TestClient) -> None:
    response = client.post("/api/providers/vllm/check", headers=auth_headers())

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_FAILED"
    assert "vllm" not in str(response.json()).lower()
