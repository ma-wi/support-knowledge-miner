from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from backend.api import create_app
from backend.auth import CurrentUser
from backend.auth.service import AuthenticationError
from backend.providers import (
    AnalysisProfile,
    AnalysisProfileInput,
    ProviderCheckResult,
    ProviderConfiguration,
    ProviderError,
    ProviderSettingsInput,
)


OWNER_ID = UUID("11111111-1111-1111-1111-111111111111")
PROJECT_ID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
PROFILE_ID = UUID("99999999-9999-9999-9999-999999999999")
NOW = datetime(2026, 7, 22, tzinfo=UTC)


class FakeAuthService:
    def seed_initial_user_from_env(self) -> None:
        return None

    def authenticate_token(self, token: str) -> CurrentUser:
        if token != "valid-token":
            raise AuthenticationError("invalid or expired session")
        return CurrentUser(
            id=OWNER_ID,
            username="owner",
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
        self.profiles: list[AnalysisProfile] = []

    def list_configurations(self) -> list[ProviderConfiguration]:
        return list(self.configurations.values())

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

    def list_profiles(self, project_id: UUID) -> list[AnalysisProfile]:
        return [
            profile for profile in self.profiles if profile.project_id == project_id
        ]

    def create_profile(
        self,
        project_id: UUID,
        payload: AnalysisProfileInput,
        *,
        actor_user_id: UUID,
    ) -> AnalysisProfile:
        assert actor_user_id == OWNER_ID
        profile = AnalysisProfile(
            id=PROFILE_ID,
            project_id=project_id,
            name=payload.name,
            provider=payload.provider,
            model=payload.model,
            is_cloud_provider=payload.provider == "openai",
            thresholds=payload.thresholds,
            algorithm_settings=payload.algorithm_settings,
            prompt_identifier=payload.prompt_identifier,
            prompt_template=payload.prompt_template,
            created_at=NOW,
            updated_at=NOW,
        )
        self.profiles.append(profile)
        return profile

    def update_profile(
        self,
        project_id: UUID,
        profile_id: UUID,
        payload: AnalysisProfileInput,
        *,
        actor_user_id: UUID,
    ) -> AnalysisProfile:
        assert actor_user_id == OWNER_ID
        for index, profile in enumerate(self.profiles):
            if profile.id == profile_id and profile.project_id == project_id:
                updated = AnalysisProfile(
                    id=profile_id,
                    project_id=project_id,
                    name=payload.name,
                    provider=payload.provider,
                    model=payload.model,
                    is_cloud_provider=payload.provider == "openai",
                    thresholds=payload.thresholds,
                    algorithm_settings=payload.algorithm_settings,
                    prompt_identifier=payload.prompt_identifier,
                    prompt_template=payload.prompt_template,
                    created_at=profile.created_at,
                    updated_at=NOW,
                )
                self.profiles[index] = updated
                return updated
        raise ProviderError("analysis profile not found")


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


def test_vllm_provider_check_and_project_profile_contract(client: TestClient) -> None:
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
            "algorithm_settings": {"clusterer": "hdbscan"},
            "prompt_identifier": "faq-v1",
        },
    )
    assert created.status_code == 201
    assert created.json()["project_id"] == str(PROJECT_ID)
    assert created.json()["is_cloud_provider"] is False
    assert created.json()["thresholds"]["similarity"] == 0.78

    listed = client.get(
        f"/api/projects/{PROJECT_ID}/analysis-profiles", headers=auth_headers()
    )
    assert listed.status_code == 200
    assert listed.json()[0]["name"] == "Local clustering"

    updated = client.patch(
        f"/api/projects/{PROJECT_ID}/analysis-profiles/{PROFILE_ID}",
        headers=auth_headers(),
        json={
            "name": "Cloud comparison",
            "provider": "openai",
            "model": "gpt-4.1-mini",
            "thresholds": {"similarity": 0.82},
            "algorithm_settings": {"clusterer": "agglomerative"},
        },
    )
    assert updated.status_code == 200
    assert updated.json()["is_cloud_provider"] is True
