from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from backend.api import create_app
from backend.auth import CurrentUser
from backend.auth.service import AuthenticationError
from backend.exports import ExportLog, ExportResult

OWNER_ID = UUID("11111111-1111-1111-1111-111111111111")
PROJECT_ID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
EXPORT_ID = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
DATASET_ID = UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
RUN_ID = UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")
NOW = datetime(2026, 7, 23, tzinfo=UTC)


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


class FakeExportService:
    def __init__(self) -> None:
        self.last_candidate_include: bool | None = None
        self.last_source_include: bool | None = None
        self.last_actor: UUID | None = None
        self.log = ExportLog(
            id=EXPORT_ID,
            project_id=PROJECT_ID,
            export_type="candidate_csv",
            include_original_text=True,
            filters={},
            selection={},
            dataset_version_id=DATASET_ID,
            analysis_run_id=RUN_ID,
            output_filename="candidate_csv-test.csv",
            output_path=None,
            row_count=1,
            created_at=NOW,
        )

    def export_candidates(
        self, project_id: UUID, *, include_original_text: bool, actor_user_id: UUID
    ) -> ExportResult:
        assert project_id == PROJECT_ID
        self.last_candidate_include = include_original_text
        self.last_actor = actor_user_id
        return ExportResult(
            log=self.log,
            csv_content="candidate_id,title\ncandidate-1,Reset FAQ\n",
            warning="Export enthaelt Originaltext.",
        )

    def export_source_assignments(
        self, project_id: UUID, *, include_original_text: bool, actor_user_id: UUID
    ) -> ExportResult:
        assert project_id == PROJECT_ID
        self.last_source_include = include_original_text
        self.last_actor = actor_user_id
        return ExportResult(
            log=ExportLog(
                **{
                    **self.log.__dict__,
                    "export_type": "source_assignment_csv",
                    "include_original_text": include_original_text,
                    "output_filename": "source_assignment_csv-test.csv",
                }
            ),
            csv_content="candidate_id,pair_id,customer_message\ncandidate-1,pair-1,\n",
            warning=None,
        )

    def list_exports(self, project_id: UUID) -> list[ExportLog]:
        assert project_id == PROJECT_ID
        return [self.log]


def auth_headers(token: str = "valid-token") -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_export_routes_require_authentication() -> None:
    client = TestClient(
        create_app(
            auth_service=FakeAuthService(),  # type: ignore[arg-type]
            export_service=FakeExportService(),  # type: ignore[arg-type]
        )
    )

    assert client.get(f"/api/projects/{PROJECT_ID}/exports").status_code == 401
    assert (
        client.post(
            f"/api/projects/{PROJECT_ID}/exports/candidates", json={}
        ).status_code
        == 401
    )


def test_export_api_creates_candidate_and_source_exports_and_lists_history() -> None:
    fake_service = FakeExportService()
    client = TestClient(
        create_app(
            auth_service=FakeAuthService(),  # type: ignore[arg-type]
            export_service=fake_service,  # type: ignore[arg-type]
        )
    )

    candidate_export = client.post(
        f"/api/projects/{PROJECT_ID}/exports/candidates",
        headers=auth_headers(),
        json={"include_original_text": True},
    )
    assert candidate_export.status_code == 201
    assert candidate_export.json()["export"]["export_type"] == "candidate_csv"
    assert candidate_export.json()["export"]["include_original_text"] is True
    assert candidate_export.json()["csv_content"].startswith("candidate_id,title")
    assert fake_service.last_candidate_include is True
    assert fake_service.last_actor == OWNER_ID

    source_export = client.post(
        f"/api/projects/{PROJECT_ID}/exports/source-assignments",
        headers=auth_headers(),
        json={"include_original_text": False},
    )
    assert source_export.status_code == 201
    assert source_export.json()["export"]["export_type"] == "source_assignment_csv"
    assert source_export.json()["export"]["include_original_text"] is False
    assert fake_service.last_source_include is False

    history = client.get(f"/api/projects/{PROJECT_ID}/exports", headers=auth_headers())
    assert history.status_code == 200
    assert history.json()[0]["output_filename"] == "candidate_csv-test.csv"
    assert history.json()[0]["row_count"] == 1


def test_candidate_export_api_returns_actual_original_text_metadata() -> None:
    fake_service = FakeExportService()
    client = TestClient(
        create_app(
            auth_service=FakeAuthService(),  # type: ignore[arg-type]
            export_service=fake_service,  # type: ignore[arg-type]
        )
    )

    response = client.post(
        f"/api/projects/{PROJECT_ID}/exports/candidates",
        headers=auth_headers(),
        json={"include_original_text": False},
    )

    assert response.status_code == 201
    assert fake_service.last_candidate_include is False
    assert response.json()["export"]["include_original_text"] is True
    assert response.json()["warning"] == "Export enthaelt Originaltext."
