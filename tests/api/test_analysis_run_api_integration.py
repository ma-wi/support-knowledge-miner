from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from backend.analysis import (
    AnalysisError,
    AnalysisQueueFull,
    AnalysisRun,
    AnalysisRunInput,
    EmbeddingRecord,
)
from backend.api import create_app
from backend.auth import CurrentUser
from backend.auth.service import AuthenticationError

OWNER_ID = UUID("11111111-1111-1111-1111-111111111111")
PROJECT_ID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
DATASET_ID = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
PROFILE_ID = UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
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
        self.received: AnalysisRunInput | None = None
        self.enqueued_run_id: UUID | None = None
        self.runs = [
            self._run(run_id=RUN_ID, status="queued", progress=0),
            self._run(run_id=RUNNING_RUN_ID, status="running", progress=5),
            self._run(run_id=COMPLETED_RUN_ID, status="completed", progress=100),
            self._run(
                run_id=FAILED_RUN_ID,
                status="failed",
                progress=65,
                error_message="RuntimeError",
            ),
        ]

    def start_run(
        self,
        project_id: UUID,
        payload: AnalysisRunInput,
        *,
        actor_user_id: UUID,
    ) -> AnalysisRun:
        if project_id != PROJECT_ID:
            raise AnalysisError("project not found")
        if "mode" in payload.parameters:
            raise AnalysisError("parameters.mode is no longer supported")
        self.started_by = actor_user_id
        self.received = payload
        return self.runs[0]

    def enqueue_run(self, run_id: UUID) -> None:
        self.enqueued_run_id = run_id

    def list_runs(self, project_id: UUID) -> list[AnalysisRun]:
        return [run for run in self.runs if run.project_id == project_id]

    def get_run(self, project_id: UUID, run_id: UUID) -> AnalysisRun | None:
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
                analysis_run_id=COMPLETED_RUN_ID,
                dataset_version_id=DATASET_ID,
                analysis_profile_id=PROFILE_ID,
                source_object_type="message_pair",
                source_object_id=SOURCE_ID,
                text_variant="message",
                model="local-embed",
                dimensions=3,
                metadata={"provider": "vllm", "source_ordinal": 1},
                created_at=NOW,
            )
        ]

    def _run(
        self,
        *,
        run_id: UUID,
        status: str,
        progress: int,
        error_message: str | None = None,
    ) -> AnalysisRun:
        return AnalysisRun(
            id=run_id,
            project_id=PROJECT_ID,
            dataset_version_id=DATASET_ID,
            analysis_profile_id=PROFILE_ID,
            status=status,
            progress=progress,
            profile_snapshot={
                "id": str(PROFILE_ID),
                "name": "Local profile",
                "provider": "vllm",
                "model": "local-embed",
                "thresholds": {"similarity": 0.78},
            },
            provider="vllm",
            model="local-embed",
            parameters={},
            error_message=error_message,
            diagnostics={"embeddings_written": 2} if status == "completed" else {},
            started_at=NOW if status in {"running", "completed", "failed"} else None,
            completed_at=NOW if status in {"completed", "failed"} else None,
            created_at=NOW,
            updated_at=NOW,
        )


def auth_headers(token: str = "valid-token") -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_analysis_run_routes_require_authentication() -> None:
    client = TestClient(
        create_app(
            auth_service=FakeAuthService(),  # type: ignore[arg-type]
            analysis_service=FakeAnalysisService(),  # type: ignore[arg-type]
        )
    )

    assert client.get(f"/api/projects/{PROJECT_ID}/analysis-runs").status_code == 401
    assert (
        client.post(f"/api/projects/{PROJECT_ID}/analysis-runs", json={}).status_code
        == 401
    )


def test_analysis_run_api_starts_lists_reads_and_exposes_embedding_metadata() -> None:
    fake_service = FakeAnalysisService()
    client = TestClient(
        create_app(
            auth_service=FakeAuthService(),  # type: ignore[arg-type]
            analysis_service=fake_service,  # type: ignore[arg-type]
        )
    )

    created = client.post(
        f"/api/projects/{PROJECT_ID}/analysis-runs",
        headers=auth_headers(),
        json={
            "dataset_version_id": str(DATASET_ID),
            "analysis_profile_id": str(PROFILE_ID),
            "parameters": {},
        },
    )

    assert created.status_code == 201
    payload = created.json()
    assert payload["status"] == "queued"
    assert payload["progress"] == 0
    assert payload["profile_snapshot"]["model"] == "local-embed"
    assert fake_service.started_by == OWNER_ID
    assert fake_service.enqueued_run_id == RUN_ID
    assert fake_service.received is not None
    assert fake_service.received.dataset_version_id == DATASET_ID
    assert fake_service.received.parameters == {}

    listed = client.get(
        f"/api/projects/{PROJECT_ID}/analysis-runs", headers=auth_headers()
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
        f"/api/projects/{PROJECT_ID}/analysis-runs/{FAILED_RUN_ID}",
        headers=auth_headers(),
    )
    assert fetched.status_code == 200
    assert fetched.json()["status"] == "failed"
    assert fetched.json()["progress"] == 65
    assert fetched.json()["error_message"] == "RuntimeError"

    embeddings = client.get(
        f"/api/projects/{PROJECT_ID}/analysis-runs/{COMPLETED_RUN_ID}/embeddings",
        headers=auth_headers(),
    )
    assert embeddings.status_code == 200
    assert embeddings.json()[0]["source_object_type"] == "message_pair"
    assert embeddings.json()[0]["dimensions"] == 3


def test_analysis_run_api_rejects_removed_mode_without_starting_run() -> None:
    fake_service = FakeAnalysisService()
    client = TestClient(
        create_app(
            auth_service=FakeAuthService(),  # type: ignore[arg-type]
            analysis_service=fake_service,  # type: ignore[arg-type]
        )
    )

    response = client.post(
        f"/api/projects/{PROJECT_ID}/analysis-runs",
        headers=auth_headers(),
        json={
            "dataset_version_id": str(DATASET_ID),
            "analysis_profile_id": str(PROFILE_ID),
            "parameters": {"mode": "fixture"},
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "parameters.mode is no longer supported"
    assert fake_service.started_by is None
    assert fake_service.enqueued_run_id is None


def test_analysis_run_api_reports_bounded_queue_overload() -> None:
    class FullAnalysisService(FakeAnalysisService):
        def enqueue_run(self, run_id: UUID) -> None:
            self.enqueued_run_id = run_id
            raise AnalysisQueueFull("local analysis capacity is exhausted; retry later")

    fake_service = FullAnalysisService()
    client = TestClient(
        create_app(
            auth_service=FakeAuthService(),  # type: ignore[arg-type]
            analysis_service=fake_service,  # type: ignore[arg-type]
        )
    )

    response = client.post(
        f"/api/projects/{PROJECT_ID}/analysis-runs",
        headers=auth_headers(),
        json={
            "dataset_version_id": str(DATASET_ID),
            "analysis_profile_id": str(PROFILE_ID),
        },
    )

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "local analysis capacity is exhausted; retry later"
    )
