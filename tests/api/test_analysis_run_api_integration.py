from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from backend.analysis import (
    AnalysisError,
    AnalysisQueueFull,
    EmbeddingRecord,
    IndexingRun,
    IndexingRunInput,
)
from backend.api import create_app
from backend.auth import CurrentUser
from backend.auth.service import AuthenticationError

OWNER_ID = UUID("11111111-1111-1111-1111-111111111111")
PROJECT_ID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
DATASET_ID = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
RUN_ID = UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")
RUNNING_RUN_ID = UUID("dddddddd-dddd-dddd-dddd-ddddddddddde")
COMPLETED_RUN_ID = UUID("dddddddd-dddd-dddd-dddd-dddddddddddf")
FAILED_RUN_ID = UUID("dddddddd-dddd-dddd-dddd-ddddddddddda")
SOURCE_ID = UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee")
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


class FakeAnalysisService:
    def __init__(self) -> None:
        self.started_by: UUID | None = None
        self.received: IndexingRunInput | None = None
        self.enqueued_run_id: UUID | None = None
        self.cancelled_by: UUID | None = None
        self.deleted_by: UUID | None = None
        self.runs = [
            self._run(run_id=RUN_ID, status="queued", progress=0, phase="queued"),
            self._run(
                run_id=RUNNING_RUN_ID,
                status="running",
                progress=25,
                phase="embedding",
            ),
            self._run(
                run_id=COMPLETED_RUN_ID,
                status="completed",
                progress=100,
                phase="completed",
            ),
            self._run(
                run_id=FAILED_RUN_ID,
                status="failed",
                progress=65,
                phase="failed",
                error_code="UNEXPECTED_ERROR",
                error_message="RuntimeError",
            ),
        ]

    def start_run(
        self,
        project_id: UUID,
        payload: IndexingRunInput,
        *,
        actor_user_id: UUID,
    ) -> IndexingRun:
        if project_id != PROJECT_ID:
            raise AnalysisError("project not found", status_code=404)
        if "analysis_profile_id" in payload.parameters:
            raise AnalysisError(
                "analysis profile parameters are no longer supported",
                code="INDEXING_MODEL_UNAVAILABLE",
                status_code=422,
            )
        if payload.provider == "openai" and not payload.cloud_use_confirmed:
            raise AnalysisError(
                "OpenAI indexing requires explicit cloud confirmation",
                code="INDEXING_CLOUD_CONFIRMATION_REQUIRED",
                status_code=422,
                suggested_action="correct-input",
            )
        self.started_by = actor_user_id
        self.received = payload
        return self.runs[0]

    def enqueue_run(self, run_id: UUID) -> None:
        self.enqueued_run_id = run_id

    def list_runs(self, project_id: UUID) -> list[IndexingRun]:
        return [run for run in self.runs if run.project_id == project_id]

    def get_run(self, project_id: UUID, run_id: UUID) -> IndexingRun | None:
        for run in self.runs:
            if run.project_id == project_id and run.id == run_id:
                return run
        return None

    def list_embeddings(self, project_id: UUID, run_id: UUID) -> list[EmbeddingRecord]:
        if project_id != PROJECT_ID or run_id != COMPLETED_RUN_ID:
            return []
        return [
            EmbeddingRecord(
                id=uuid4(),
                project_id=PROJECT_ID,
                indexing_run_id=COMPLETED_RUN_ID,
                dataset_version_id=DATASET_ID,
                source_object_type="message_pair",
                source_object_id=SOURCE_ID,
                text_variant="message",
                model="local-embed",
                dimensions=3,
                metadata={"provider": "vllm", "source_ordinal": 1},
                created_at=NOW,
            ),
            EmbeddingRecord(
                id=uuid4(),
                project_id=PROJECT_ID,
                indexing_run_id=COMPLETED_RUN_ID,
                dataset_version_id=DATASET_ID,
                source_object_type="message_pair",
                source_object_id=SOURCE_ID,
                text_variant="answer",
                model="local-embed",
                dimensions=3,
                metadata={"provider": "vllm", "source_ordinal": 1},
                created_at=NOW,
            ),
        ]

    def cancel_run(
        self, project_id: UUID, run_id: UUID, *, actor_user_id: UUID
    ) -> IndexingRun:
        if project_id != PROJECT_ID:
            raise AnalysisError("indexing run not found", status_code=404)
        self.cancelled_by = actor_user_id
        if run_id == COMPLETED_RUN_ID:
            raise AnalysisError(
                "indexing run can no longer be cancelled",
                code="INDEXING_CANCEL_NOT_AVAILABLE",
                status_code=409,
                suggested_action="reload",
            )
        for run in self.runs:
            if run.id == run_id:
                return self._run(
                    run_id=run.id,
                    status="cancelling" if run.status == "running" else "cancelled",
                    progress=run.progress,
                    phase="cancelling" if run.status == "running" else "cancelled",
                )
        raise AnalysisError("indexing run not found", status_code=404)

    def delete_run(
        self, project_id: UUID, run_id: UUID, *, actor_user_id: UUID
    ) -> None:
        if project_id != PROJECT_ID or not any(run.id == run_id for run in self.runs):
            raise AnalysisError("indexing run not found", status_code=404)
        self.deleted_by = actor_user_id

    def _run(
        self,
        *,
        run_id: UUID,
        status: str,
        progress: int,
        phase: str,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> IndexingRun:
        return IndexingRun(
            id=run_id,
            project_id=PROJECT_ID,
            dataset_version_id=DATASET_ID,
            dataset_display_name="Support import",
            dataset_deleted_at=None,
            status=status,
            progress=progress,
            phase=phase,
            provider="vllm",
            model="local-embed",
            parameters={},
            error_code=error_code,
            error_message=error_message,
            diagnostics={"embeddings_written": 2} if status == "completed" else {},
            started_at=NOW if status in {"running", "completed", "failed"} else None,
            completed_at=NOW if status in {"completed", "failed"} else None,
            cancel_requested_at=None,
            deleted_at=None,
            created_at=NOW,
            updated_at=NOW,
        )


def auth_headers(token: str = "valid-token") -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_indexing_run_routes_require_authentication() -> None:
    client = TestClient(
        create_app(
            auth_service=FakeAuthService(),  # type: ignore[arg-type]
            analysis_service=FakeAnalysisService(),  # type: ignore[arg-type]
        )
    )

    assert client.get(f"/api/projects/{PROJECT_ID}/indexing-runs").status_code == 401
    assert (
        client.post(f"/api/projects/{PROJECT_ID}/indexing-runs", json={}).status_code
        == 401
    )


def test_indexing_run_api_starts_lists_reads_and_exposes_embedding_metadata() -> None:
    fake_service = FakeAnalysisService()
    client = TestClient(
        create_app(
            auth_service=FakeAuthService(),  # type: ignore[arg-type]
            analysis_service=fake_service,  # type: ignore[arg-type]
        )
    )

    created = client.post(
        f"/api/projects/{PROJECT_ID}/indexing-runs",
        headers=auth_headers(),
        json={
            "dataset_version_id": str(DATASET_ID),
            "provider": "vllm",
            "model": "local-embed",
        },
    )

    assert created.status_code == 201
    payload = created.json()
    assert payload["status"] == "queued"
    assert payload["progress"] == 0
    assert payload["phase"] == "queued"
    assert payload["model"] == "local-embed"
    assert "analysis_profile_id" not in payload
    assert "profile_snapshot" not in payload
    assert fake_service.started_by == OWNER_ID
    assert fake_service.enqueued_run_id == RUN_ID
    assert fake_service.received is not None
    assert fake_service.received.dataset_version_id == DATASET_ID
    assert fake_service.received.provider == "vllm"
    assert fake_service.received.model == "local-embed"

    listed = client.get(
        f"/api/projects/{PROJECT_ID}/indexing-runs", headers=auth_headers()
    )
    assert listed.status_code == 200
    assert listed.json()[0]["id"] == str(RUN_ID)
    assert {run["status"] for run in listed.json()} == {
        "queued",
        "running",
        "completed",
        "failed",
    }

    fetched = client.get(
        f"/api/projects/{PROJECT_ID}/indexing-runs/{FAILED_RUN_ID}",
        headers=auth_headers(),
    )
    assert fetched.status_code == 200
    assert fetched.json()["status"] == "failed"
    assert fetched.json()["progress"] == 65
    assert fetched.json()["error_code"] == "UNEXPECTED_ERROR"
    assert fetched.json()["error_message"] == "RuntimeError"

    embeddings = client.get(
        f"/api/projects/{PROJECT_ID}/indexing-runs/{COMPLETED_RUN_ID}/embeddings",
        headers=auth_headers(),
    )
    assert embeddings.status_code == 200
    assert {item["text_variant"] for item in embeddings.json()} == {
        "message",
        "answer",
    }
    assert embeddings.json()[0]["source_object_type"] == "message_pair"
    assert embeddings.json()[0]["dimensions"] == 3
    assert "analysis_profile_id" not in embeddings.json()[0]


def test_indexing_run_api_rejects_profile_parameters_with_problem_details() -> None:
    fake_service = FakeAnalysisService()
    client = TestClient(
        create_app(
            auth_service=FakeAuthService(),  # type: ignore[arg-type]
            analysis_service=fake_service,  # type: ignore[arg-type]
        )
    )

    response = client.post(
        f"/api/projects/{PROJECT_ID}/indexing-runs",
        headers=auth_headers(),
        json={
            "dataset_version_id": str(DATASET_ID),
            "provider": "vllm",
            "model": "local-embed",
            "parameters": {"analysis_profile_id": "legacy"},
        },
    )

    assert response.status_code == 422
    assert response.json()["type"] == "urn:skm:error:INDEXING_MODEL_UNAVAILABLE"
    assert response.json()["code"] == "INDEXING_MODEL_UNAVAILABLE"
    assert response.json()["detail"] == (
        "Das gewählte Embedding-Modell ist nicht verfügbar."
    )
    assert fake_service.started_by is None
    assert fake_service.enqueued_run_id is None


def test_indexing_run_api_requires_openai_cloud_confirmation() -> None:
    fake_service = FakeAnalysisService()
    client = TestClient(
        create_app(
            auth_service=FakeAuthService(),  # type: ignore[arg-type]
            analysis_service=fake_service,  # type: ignore[arg-type]
        )
    )

    response = client.post(
        f"/api/projects/{PROJECT_ID}/indexing-runs",
        headers=auth_headers(),
        json={
            "dataset_version_id": str(DATASET_ID),
            "provider": "openai",
            "model": "local-embed",
        },
    )

    assert response.status_code == 422
    assert response.json()["type"] == (
        "urn:skm:error:INDEXING_CLOUD_CONFIRMATION_REQUIRED"
    )
    assert response.json()["code"] == "INDEXING_CLOUD_CONFIRMATION_REQUIRED"
    assert response.json()["title"] == "Cloud-Nutzung muss bestätigt werden."
    assert response.json()["suggestedAction"] == (
        "Cloud-Nutzung bestätigen oder ein lokales Modell wählen."
    )
    assert fake_service.enqueued_run_id is None


def test_indexing_run_api_reports_bounded_queue_overload() -> None:
    class FullAnalysisService(FakeAnalysisService):
        def enqueue_run(self, run_id: UUID) -> None:
            self.enqueued_run_id = run_id
            raise AnalysisQueueFull("local indexing capacity is exhausted; retry later")

    fake_service = FullAnalysisService()
    client = TestClient(
        create_app(
            auth_service=FakeAuthService(),  # type: ignore[arg-type]
            analysis_service=fake_service,  # type: ignore[arg-type]
        )
    )

    response = client.post(
        f"/api/projects/{PROJECT_ID}/indexing-runs",
        headers=auth_headers(),
        json={
            "dataset_version_id": str(DATASET_ID),
            "provider": "vllm",
            "model": "local-embed",
        },
    )

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "Ein unerwarteter Fehler ist aufgetreten; die Eingaben bleiben soweit "
        "sicher erhalten."
    )
    assert response.json()["code"] == "UNEXPECTED_ERROR"


def test_indexing_cancel_and_delete_routes_are_project_scoped() -> None:
    fake_service = FakeAnalysisService()
    client = TestClient(
        create_app(
            auth_service=FakeAuthService(),  # type: ignore[arg-type]
            analysis_service=fake_service,  # type: ignore[arg-type]
        )
    )

    cancelled = client.post(
        f"/api/projects/{PROJECT_ID}/indexing-runs/{RUNNING_RUN_ID}/cancel",
        headers=auth_headers(),
    )

    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelling"
    assert fake_service.cancelled_by == OWNER_ID

    rejected = client.post(
        f"/api/projects/{PROJECT_ID}/indexing-runs/{COMPLETED_RUN_ID}/cancel",
        headers=auth_headers(),
    )

    assert rejected.status_code == 409
    assert rejected.json()["type"] == "urn:skm:error:INDEXING_CANCEL_NOT_AVAILABLE"
    assert rejected.json()["code"] == "INDEXING_CANCEL_NOT_AVAILABLE"

    deleted = client.delete(
        f"/api/projects/{PROJECT_ID}/indexing-runs/{RUN_ID}",
        headers=auth_headers(),
    )

    assert deleted.status_code == 204
    assert fake_service.deleted_by == OWNER_ID
