from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from backend.api import create_app
from backend.auth import CurrentUser
from backend.auth.service import AuthenticationError
from backend.clusters import Cluster, ClusterError, ClusterManualUpdate, ClusterSource

OWNER_ID = UUID("11111111-1111-1111-1111-111111111111")
PROJECT_ID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
RUN_ID = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
DATASET_ID = UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
CLUSTER_ID = UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")
PAIR_ID = UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee")
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


class FakeClusterService:
    def __init__(self) -> None:
        self.generated_by: UUID | None = None
        self.updated_by: UUID | None = None
        self.cluster = self._cluster()

    def generate_for_run(
        self, project_id: UUID, run_id: UUID, *, actor_user_id: UUID
    ) -> list[Cluster]:
        assert project_id == PROJECT_ID
        assert run_id == RUN_ID
        self.generated_by = actor_user_id
        return [self.cluster]

    def list_clusters(self, project_id: UUID, run_id: UUID) -> list[Cluster]:
        assert project_id == PROJECT_ID
        assert run_id == RUN_ID
        return [self.cluster]

    def update_cluster(
        self,
        project_id: UUID,
        cluster_id: UUID,
        payload: ClusterManualUpdate,
        *,
        actor_user_id: UUID,
    ) -> Cluster:
        assert project_id == PROJECT_ID
        assert cluster_id == CLUSTER_ID
        self.updated_by = actor_user_id
        self.cluster = self._cluster(
            manual_title=payload.manual_title,
            manual_category=payload.manual_category,
            manual_status=payload.manual_status,
        )
        return self.cluster

    def list_sources(self, project_id: UUID, cluster_id: UUID) -> list[ClusterSource]:
        assert project_id == PROJECT_ID
        assert cluster_id == CLUSTER_ID
        return [
            ClusterSource(
                cluster_id=CLUSTER_ID,
                message_pair_id=PAIR_ID,
                ticket_id="T-1",
                message_group_id="G-1",
                message="How do I reset it?",
                answer="Use the reset link.",
                membership_score=0.91,
                is_outlier=False,
                assignment_type="automatic",
            )
        ]

    def _cluster(
        self,
        *,
        manual_title: str | None = None,
        manual_category: str | None = None,
        manual_status: str | None = None,
    ) -> Cluster:
        return Cluster(
            id=CLUSTER_ID,
            project_id=PROJECT_ID,
            analysis_run_id=RUN_ID,
            dataset_version_id=DATASET_ID,
            auto_title="Cluster H",
            manual_title=manual_title,
            effective_title=manual_title or "Cluster H",
            auto_category="hdbscan",
            manual_category=manual_category,
            effective_category=manual_category or "hdbscan",
            auto_status="unreviewed",
            manual_status=manual_status,
            effective_status=manual_status or "unreviewed",
            score=0.91,
            is_outlier=False,
            algorithm="hdbscan",
            member_count=2,
            metadata={"label": 0, "non_quadratic": True},
            created_at=NOW,
            updated_at=NOW,
        )


def auth_headers(token: str = "valid-token") -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_cluster_routes_require_authentication() -> None:
    client = TestClient(
        create_app(
            auth_service=FakeAuthService(),  # type: ignore[arg-type]
            cluster_service=FakeClusterService(),  # type: ignore[arg-type]
        )
    )

    assert (
        client.get(
            f"/api/projects/{PROJECT_ID}/analysis-runs/{RUN_ID}/clusters"
        ).status_code
        == 401
    )
    assert (
        client.post(
            f"/api/projects/{PROJECT_ID}/analysis-runs/{RUN_ID}/clusters/generate"
        ).status_code
        == 401
    )


def test_cluster_api_generates_updates_and_exposes_source_traceability() -> None:
    fake_service = FakeClusterService()
    client = TestClient(
        create_app(
            auth_service=FakeAuthService(),  # type: ignore[arg-type]
            cluster_service=fake_service,  # type: ignore[arg-type]
        )
    )

    generated = client.post(
        f"/api/projects/{PROJECT_ID}/analysis-runs/{RUN_ID}/clusters/generate",
        headers=auth_headers(),
    )
    assert generated.status_code == 200
    assert generated.json()[0]["auto_title"] == "Cluster H"
    assert generated.json()[0]["effective_title"] == "Cluster H"
    assert generated.json()[0]["metadata"]["non_quadratic"] is True
    assert fake_service.generated_by == OWNER_ID

    updated = client.patch(
        f"/api/projects/{PROJECT_ID}/clusters/{CLUSTER_ID}",
        headers=auth_headers(),
        json={
            "manual_title": "Reset workflow",
            "manual_category": "Account",
            "manual_status": "reviewed",
        },
    )
    assert updated.status_code == 200
    assert updated.json()["auto_title"] == "Cluster H"
    assert updated.json()["manual_title"] == "Reset workflow"
    assert updated.json()["effective_title"] == "Reset workflow"
    assert updated.json()["effective_status"] == "reviewed"
    assert fake_service.updated_by == OWNER_ID

    sources = client.get(
        f"/api/projects/{PROJECT_ID}/clusters/{CLUSTER_ID}/sources",
        headers=auth_headers(),
    )
    assert sources.status_code == 200
    payload = sources.json()[0]
    assert payload["ticket_id"] == "T-1"
    assert payload["message_group_id"] == "G-1"
    assert "ticketid" not in payload
    assert "messagegroupid" not in payload
    assert payload["message"] == "How do I reset it?"
    assert payload["answer"] == "Use the reset link."


def test_cluster_api_preserves_safe_detailed_memory_budget_error() -> None:
    detail = (
        "clustering working set estimate 600000000 bytes for 10000 records "
        "with 8192 dimensions exceeds the 536870912-byte (512 MiB) limit; "
        "reduce the dataset size or embedding dimensions, or select HDBSCAN"
    )

    class BudgetRejectingClusterService(FakeClusterService):
        def generate_for_run(
            self, project_id: UUID, run_id: UUID, *, actor_user_id: UUID
        ) -> list[Cluster]:
            assert project_id == PROJECT_ID
            assert run_id == RUN_ID
            assert actor_user_id == OWNER_ID
            raise ClusterError(detail)

    client = TestClient(
        create_app(
            auth_service=FakeAuthService(),  # type: ignore[arg-type]
            cluster_service=BudgetRejectingClusterService(),  # type: ignore[arg-type]
        )
    )

    response = client.post(
        f"/api/projects/{PROJECT_ID}/analysis-runs/{RUN_ID}/clusters/generate",
        headers=auth_headers(),
    )

    assert response.status_code == 400
    assert response.json() == {"detail": detail}
