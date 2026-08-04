from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from backend.api import create_app
from backend.auth import CurrentUser
from backend.auth.service import AuthenticationError
from backend.clusters import (
    Cluster,
    ClusterError,
    ClusterManualUpdate,
    ClusterSet,
    ClusterSetEvent,
    ClusterSetInput,
    ClusterSource,
    ClusterSourcePage,
)

OWNER_ID = UUID("11111111-1111-1111-1111-111111111111")
PROJECT_ID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
RUN_ID = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
DATASET_ID = UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
CLUSTER_ID = UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")
CLUSTER_SET_ID = UUID("99999999-9999-9999-9999-999999999999")
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
        self.started_payload: ClusterSetInput | None = None
        self.started_by: UUID | None = None
        self.enqueued_id: UUID | None = None
        self.cancelled_by: UUID | None = None
        self.deleted_by: UUID | None = None
        self.cluster = self._cluster()
        self.cluster_set = self._cluster_set()
        self.update_error: ClusterError | None = None
        self.source_error: ClusterError | None = None

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
        if self.update_error is not None:
            raise self.update_error
        self.cluster = self._cluster(
            manual_title=payload.manual_title,
            manual_category=payload.manual_category,
            manual_status=payload.manual_status,
        )
        return self.cluster

    def list_sources(
        self,
        project_id: UUID,
        cluster_id: UUID,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> ClusterSourcePage:
        assert project_id == PROJECT_ID
        assert cluster_id == CLUSTER_ID
        assert limit == 1
        assert offset == 0
        if self.source_error is not None:
            raise self.source_error
        return ClusterSourcePage(
            sources=[
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
            ],
            limit=limit,
            offset=offset,
            next_offset=1,
            has_more=True,
        )

    def start_cluster_set(
        self,
        project_id: UUID,
        payload: ClusterSetInput,
        *,
        actor_user_id: UUID,
    ) -> ClusterSet:
        assert project_id == PROJECT_ID
        self.started_payload = payload
        self.started_by = actor_user_id
        self.cluster_set = self._cluster_set(
            display_name=payload.display_name or "Cluster-Set",
            vector_basis=payload.vector_basis,
            status="queued",
        )
        return self.cluster_set

    def enqueue_cluster_set(self, cluster_set_id: UUID) -> None:
        self.enqueued_id = cluster_set_id

    def list_cluster_sets(self, project_id: UUID) -> list[ClusterSet]:
        assert project_id == PROJECT_ID
        return [self.cluster_set]

    def get_cluster_set(
        self, project_id: UUID, cluster_set_id: UUID
    ) -> ClusterSet | None:
        assert project_id == PROJECT_ID
        assert cluster_set_id == CLUSTER_SET_ID
        return self.cluster_set

    def cancel_cluster_set(
        self, project_id: UUID, cluster_set_id: UUID, *, actor_user_id: UUID
    ) -> ClusterSet:
        assert project_id == PROJECT_ID
        assert cluster_set_id == CLUSTER_SET_ID
        self.cancelled_by = actor_user_id
        self.cluster_set = self._cluster_set(status="cancelled", phase="cancelled")
        return self.cluster_set

    def delete_cluster_set(
        self, project_id: UUID, cluster_set_id: UUID, *, actor_user_id: UUID
    ) -> None:
        assert project_id == PROJECT_ID
        assert cluster_set_id == CLUSTER_SET_ID
        self.deleted_by = actor_user_id

    def list_clusters_for_set(
        self, project_id: UUID, cluster_set_id: UUID
    ) -> list[Cluster]:
        assert project_id == PROJECT_ID
        assert cluster_set_id == CLUSTER_SET_ID
        return [
            self._cluster(
                manual_title=self.cluster.manual_title,
                manual_category=self.cluster.manual_category,
                manual_status=self.cluster.manual_status,
            )
        ]

    def list_cluster_set_events(
        self, project_id: UUID, cluster_set_id: UUID
    ) -> list[ClusterSetEvent]:
        assert project_id == PROJECT_ID
        assert cluster_set_id == CLUSTER_SET_ID
        return [
            ClusterSetEvent(
                id=UUID("88888888-8888-8888-8888-888888888888"),
                project_id=PROJECT_ID,
                cluster_set_id=CLUSTER_SET_ID,
                event_type="created",
                metadata={"vector_basis": "combined"},
                created_at=NOW,
            )
        ]

    def _cluster_set(
        self,
        *,
        display_name: str = "Reset Cluster-Set",
        vector_basis: str = "combined",
        status: str = "completed",
        phase: str = "completed",
    ) -> ClusterSet:
        return ClusterSet(
            id=CLUSTER_SET_ID,
            project_id=PROJECT_ID,
            indexing_run_id=RUN_ID,
            dataset_version_id=DATASET_ID,
            dataset_display_name="Support Import",
            indexing_deleted_at=None,
            parent_cluster_set_id=None,
            display_name=display_name,
            status=status,
            progress=100 if status == "completed" else 0,
            phase=phase,
            derivation_type="root",
            vector_basis=vector_basis,
            message_weight=0.5,
            answer_weight=0.5,
            algorithm="hdbscan",
            parameters={"min_cluster_size": 2},
            source_snapshot={"type": "all_dataset_pairs", "source_pair_count": 2},
            llm_provider="ollama",
            llm_model="llama3.1",
            llm_parameters={"enabled": True},
            llm_sample_strategy={"strategy": "random", "requested": 2, "seed": 7},
            error_code=None,
            error_message=None,
            diagnostics={},
            started_at=NOW,
            completed_at=NOW if status == "completed" else None,
            cancel_requested_at=None,
            deleted_at=None,
            created_at=NOW,
            updated_at=NOW,
            cluster_count=1,
        )

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
            cluster_set_id=CLUSTER_SET_ID,
            auto_summary_question="How do I reset it?",
            auto_summary_answer="Use the reset link.",
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
    assert client.get(f"/api/projects/{PROJECT_ID}/cluster-sets").status_code == 401


def test_cluster_api_replaces_run_bound_generation_updates_and_exposes_sources() -> (
    None
):
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
    assert generated.status_code == 410
    assert generated.json()["code"] == "CLUSTER_RUN_BOUND_API_REPLACED"
    assert generated.json()["suggestedAction"] == "create-cluster-set"
    assert fake_service.generated_by is None

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
        f"/api/projects/{PROJECT_ID}/clusters/{CLUSTER_ID}/sources?limit=1&offset=0",
        headers=auth_headers(),
    )
    assert sources.status_code == 200
    page = sources.json()
    assert page["limit"] == 1
    assert page["offset"] == 0
    assert page["next_offset"] == 1
    assert page["has_more"] is True
    payload = page["sources"][0]
    assert payload["ticket_id"] == "T-1"
    assert payload["message_group_id"] == "G-1"
    assert "ticketid" not in payload
    assert "messagegroupid" not in payload
    assert payload["message"] == "How do I reset it?"
    assert payload["answer"] == "Use the reset link."


def test_cluster_api_maps_manual_update_and_source_errors_safely() -> None:
    fake_service = FakeClusterService()
    client = TestClient(
        create_app(
            auth_service=FakeAuthService(),  # type: ignore[arg-type]
            cluster_service=fake_service,  # type: ignore[arg-type]
        )
    )

    fake_service.update_error = ClusterError(
        "raw cluster update diagnostic",
        code="CLUSTER_MANUAL_UPDATE_INVALID",
        status_code=422,
        retryable=True,
        suggested_action="correct-input",
        field_errors={"manual_status": "unsupported status"},
    )
    updated = client.patch(
        f"/api/projects/{PROJECT_ID}/clusters/{CLUSTER_ID}",
        headers=auth_headers(),
        json={"manual_status": "unsupported"},
    )
    assert updated.status_code == 422
    update_problem = updated.json()
    assert update_problem["code"] == "CLUSTER_MANUAL_UPDATE_INVALID"
    assert update_problem["detail"] != "raw cluster update diagnostic"
    assert update_problem["suggestedAction"] == "correct-input"
    assert update_problem["fieldErrors"] == [
        {"field": "manual_status", "message": "unsupported status"}
    ]

    fake_service.update_error = None
    fake_service.source_error = ClusterError(
        "raw source lookup diagnostic",
        code="CLUSTER_SOURCE_NOT_FOUND",
        status_code=404,
        retryable=True,
        suggested_action="reload",
    )
    sources = client.get(
        f"/api/projects/{PROJECT_ID}/clusters/{CLUSTER_ID}/sources?limit=1&offset=0",
        headers=auth_headers(),
    )
    assert sources.status_code == 404
    source_problem = sources.json()
    assert source_problem["code"] == "CLUSTER_SOURCE_NOT_FOUND"
    assert source_problem["detail"] != "raw source lookup diagnostic"
    assert source_problem["suggestedAction"] == "reload"

    invalid_sources = client.get(
        f"/api/projects/{PROJECT_ID}/clusters/{CLUSTER_ID}/sources?limit=nope",
        headers=auth_headers(),
    )
    assert invalid_sources.status_code == 422
    invalid_problem = invalid_sources.json()
    assert invalid_problem["code"] == "CLUSTER_SOURCE_PAGE_INVALID"
    assert invalid_problem["detail"] != "nope"
    assert invalid_problem["suggestedAction"] == "correct-input"


def test_cluster_api_replaces_run_bound_cluster_loading() -> None:
    fake_service = FakeClusterService()
    client = TestClient(
        create_app(
            auth_service=FakeAuthService(),  # type: ignore[arg-type]
            cluster_service=fake_service,  # type: ignore[arg-type]
        )
    )

    response = client.get(
        f"/api/projects/{PROJECT_ID}/analysis-runs/{RUN_ID}/clusters",
        headers=auth_headers(),
    )

    assert response.status_code == 410
    assert response.json()["code"] == "CLUSTER_RUN_BOUND_API_REPLACED"


def test_cluster_set_api_creates_lists_cancels_deletes_and_exposes_events() -> None:
    fake_service = FakeClusterService()
    client = TestClient(
        create_app(
            auth_service=FakeAuthService(),  # type: ignore[arg-type]
            cluster_service=fake_service,  # type: ignore[arg-type]
        )
    )

    created = client.post(
        f"/api/projects/{PROJECT_ID}/cluster-sets",
        headers=auth_headers(),
        json={
            "indexing_run_id": str(RUN_ID),
            "display_name": "Antworten fein",
            "vector_basis": "combined",
            "message_weight": 0.4,
            "answer_weight": 0.6,
            "algorithm_settings": {"algorithm": "hdbscan", "min_cluster_size": 2},
            "outlier_threshold": 0.7,
            "llm_provider": "ollama",
            "llm_model": "llama3.1",
            "llm_sample_count": 2,
        },
    )
    assert created.status_code == 201
    assert created.json()["display_name"] == "Antworten fein"
    assert created.json()["vector_basis"] == "combined"
    assert fake_service.started_by == OWNER_ID
    assert fake_service.started_payload is not None
    assert fake_service.started_payload.answer_weight == 0.6
    assert fake_service.started_payload.outlier_threshold == 0.7
    assert fake_service.enqueued_id == CLUSTER_SET_ID

    listed = client.get(
        f"/api/projects/{PROJECT_ID}/cluster-sets", headers=auth_headers()
    )
    assert listed.status_code == 200
    assert listed.json()[0]["cluster_count"] == 1
    assert listed.json()[0]["llm_sample_strategy"]["requested"] == 2

    clusters = client.get(
        f"/api/projects/{PROJECT_ID}/cluster-sets/{CLUSTER_SET_ID}/clusters",
        headers=auth_headers(),
    )
    assert clusters.status_code == 200
    assert clusters.json()[0]["cluster_set_id"] == str(CLUSTER_SET_ID)
    assert clusters.json()[0]["auto_summary_question"] == "How do I reset it?"

    events = client.get(
        f"/api/projects/{PROJECT_ID}/cluster-sets/{CLUSTER_SET_ID}/events",
        headers=auth_headers(),
    )
    assert events.status_code == 200
    assert events.json()[0]["event_type"] == "created"

    cancelled = client.post(
        f"/api/projects/{PROJECT_ID}/cluster-sets/{CLUSTER_SET_ID}/cancel",
        headers=auth_headers(),
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    assert fake_service.cancelled_by == OWNER_ID

    deleted = client.delete(
        f"/api/projects/{PROJECT_ID}/cluster-sets/{CLUSTER_SET_ID}",
        headers=auth_headers(),
    )
    assert deleted.status_code == 204
    assert fake_service.deleted_by == OWNER_ID


def test_cluster_set_api_returns_catalogued_problem_details() -> None:
    class NotCompleteClusterService(FakeClusterService):
        def start_cluster_set(
            self,
            project_id: UUID,
            payload: ClusterSetInput,
            *,
            actor_user_id: UUID,
        ) -> ClusterSet:
            raise ClusterError(
                "indexing run must be completed before clustering",
                code="INDEXING_NOT_COMPLETE",
                status_code=422,
                field_errors={
                    "indexing_run_id": (
                        "indexing run must be completed before clustering"
                    )
                },
            )

    client = TestClient(
        create_app(
            auth_service=FakeAuthService(),  # type: ignore[arg-type]
            cluster_service=NotCompleteClusterService(),  # type: ignore[arg-type]
        )
    )

    response = client.post(
        f"/api/projects/{PROJECT_ID}/cluster-sets",
        headers=auth_headers(),
        json={"indexing_run_id": str(RUN_ID)},
    )

    assert response.status_code == 422
    payload = response.json()
    assert payload["type"] == "urn:skm:error:INDEXING_NOT_COMPLETE"
    assert payload["code"] == "INDEXING_NOT_COMPLETE"
    assert payload["detail"] == "Diese Indizierung ist noch nicht abgeschlossen."
    assert payload["fieldErrors"] == [
        {
            "field": "indexing_run_id",
            "message": "indexing run must be completed before clustering",
        }
    ]


def test_cluster_set_api_maps_invalid_llm_sample_count_to_problem_details() -> None:
    fake_service = FakeClusterService()
    client = TestClient(
        create_app(
            auth_service=FakeAuthService(),  # type: ignore[arg-type]
            cluster_service=fake_service,  # type: ignore[arg-type]
        )
    )

    for request_body in (
        {"indexing_run_id": str(RUN_ID), "llm_sample_count": 1.5},
        {"indexing_run_id": str(RUN_ID), "llm_sample_count": "2"},
    ):
        response = client.post(
            f"/api/projects/{PROJECT_ID}/cluster-sets",
            headers=auth_headers(),
            json=request_body,
        )
        assert response.status_code == 422
        payload = response.json()
        assert payload["type"] == "urn:skm:error:CLUSTER_SUMMARY_SAMPLE_COUNT_INVALID"
        assert payload["code"] == "CLUSTER_SUMMARY_SAMPLE_COUNT_INVALID"
        assert payload["suggestedAction"] == "correct-input"
        assert payload["fieldErrors"] == [
            {
                "field": "llm_sample_count",
                "message": ("LLM summary sample count must be a positive integer"),
            }
        ]

    exponent_response = client.post(
        f"/api/projects/{PROJECT_ID}/cluster-sets",
        headers={**auth_headers(), "Content-Type": "application/json"},
        content=f'{{"indexing_run_id":"{RUN_ID}","llm_sample_count":1e2}}',
    )
    assert exponent_response.status_code == 422
    assert exponent_response.json()["code"] == "CLUSTER_SUMMARY_SAMPLE_COUNT_INVALID"
    assert fake_service.started_by is None


def test_cluster_set_api_unexpected_error_uses_stable_suggested_action() -> None:
    class UnexpectedClusterService(FakeClusterService):
        def start_cluster_set(
            self,
            project_id: UUID,
            payload: ClusterSetInput,
            *,
            actor_user_id: UUID,
        ) -> ClusterSet:
            raise ClusterError(
                "unexpected cluster failure",
                status_code=500,
                retryable=True,
            )

    client = TestClient(
        create_app(
            auth_service=FakeAuthService(),  # type: ignore[arg-type]
            cluster_service=UnexpectedClusterService(),  # type: ignore[arg-type]
        )
    )

    response = client.post(
        f"/api/projects/{PROJECT_ID}/cluster-sets",
        headers=auth_headers(),
        json={"indexing_run_id": str(RUN_ID)},
    )

    assert response.status_code == 500
    payload = response.json()
    assert payload["type"] == "urn:skm:error:UNEXPECTED_ERROR"
    assert payload["code"] == "UNEXPECTED_ERROR"
    assert payload["suggestedAction"] == "retry"


def test_cluster_set_clusters_require_completed_set() -> None:
    class RunningClusterService(FakeClusterService):
        def list_clusters_for_set(
            self, project_id: UUID, cluster_set_id: UUID
        ) -> list[Cluster]:
            raise ClusterError(
                "Cluster-Set is not completed",
                code="CLUSTER_SET_NOT_COMPLETE",
                status_code=409,
                retryable=True,
                suggested_action="wait",
            )

    client = TestClient(
        create_app(
            auth_service=FakeAuthService(),  # type: ignore[arg-type]
            cluster_service=RunningClusterService(),  # type: ignore[arg-type]
        )
    )

    response = client.get(
        f"/api/projects/{PROJECT_ID}/cluster-sets/{CLUSTER_SET_ID}/clusters",
        headers=auth_headers(),
    )

    assert response.status_code == 409
    payload = response.json()
    assert payload["type"] == "urn:skm:error:CLUSTER_SET_NOT_COMPLETE"
    assert payload["code"] == "CLUSTER_SET_NOT_COMPLETE"
    assert payload["retryable"] is True
