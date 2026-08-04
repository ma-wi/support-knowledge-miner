from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from backend.api import create_app
from backend.auth import CurrentUser
from backend.auth.service import AuthenticationError
from backend.exports import ExplorerExportInput, ExportError, ExportLog, ExportResult

OWNER_ID = UUID("11111111-1111-1111-1111-111111111111")
PROJECT_ID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
EXPORT_ID = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
DATASET_ID = UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
RUN_ID = UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")
CLUSTER_SET_ID = UUID("99999999-9999-9999-9999-999999999999")
CLUSTER_ID = UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee")
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
        self.last_payload: ExplorerExportInput | None = None
        self.last_actor: UUID | None = None
        self.raise_error: ExportError | None = None
        self.log = ExportLog(
            id=EXPORT_ID,
            project_id=PROJECT_ID,
            export_type="explorer_csv",
            include_original_text=False,
            filters={"search_query": "reset"},
            selection={"cluster_ids": [str(CLUSTER_ID)]},
            dataset_version_id=DATASET_ID,
            analysis_run_id=RUN_ID,
            cluster_set_id=CLUSTER_SET_ID,
            output_filename="explorer_csv-test.csv",
            output_path=None,
            row_count=1,
            created_at=NOW,
        )

    def export_explorer(
        self,
        project_id: UUID,
        payload: ExplorerExportInput,
        *,
        actor_user_id: UUID,
    ) -> ExportResult:
        assert project_id == PROJECT_ID
        self.last_payload = payload
        self.last_actor = actor_user_id
        if self.raise_error is not None:
            raise self.raise_error
        return ExportResult(
            log=self.log,
            content="cluster_id,title\ncluster-1,Reset FAQ\n",
            content_type="text/csv",
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
            f"/api/projects/{PROJECT_ID}/exports/explorer",
            json={"cluster_set_id": str(CLUSTER_SET_ID)},
        ).status_code
        == 401
    )


def test_explorer_export_api_creates_export_and_lists_history() -> None:
    fake_service = FakeExportService()
    client = TestClient(
        create_app(
            auth_service=FakeAuthService(),  # type: ignore[arg-type]
            export_service=fake_service,  # type: ignore[arg-type]
        )
    )

    response = client.post(
        f"/api/projects/{PROJECT_ID}/exports/explorer",
        headers=auth_headers(),
        json={
            "cluster_set_id": str(CLUSTER_SET_ID),
            "export_format": "csv",
            "search_query": "reset",
            "category": "account",
            "include_excluded": False,
            "include_outliers": True,
            "cluster_ids": [str(CLUSTER_ID)],
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["export"]["export_type"] == "explorer_csv"
    assert payload["export"]["cluster_set_id"] == str(CLUSTER_SET_ID)
    assert payload["content_type"] == "text/csv"
    assert payload["content"].startswith("cluster_id,title")
    assert fake_service.last_payload == ExplorerExportInput(
        cluster_set_id=CLUSTER_SET_ID,
        export_format="csv",
        search_query="reset",
        category="account",
        include_excluded=False,
        include_outliers=True,
        cluster_ids=[CLUSTER_ID],
    )
    assert fake_service.last_actor == OWNER_ID

    history = client.get(f"/api/projects/{PROJECT_ID}/exports", headers=auth_headers())
    assert history.status_code == 200
    assert history.json()[0]["output_filename"] == "explorer_csv-test.csv"
    assert history.json()[0]["cluster_set_id"] == str(CLUSTER_SET_ID)


def test_explorer_export_api_maps_empty_filter_problem() -> None:
    fake_service = FakeExportService()
    fake_service.raise_error = ExportError(
        "empty",
        code="EXPLORER_EXPORT_EMPTY",
        status_code=422,
        retryable=True,
        suggested_action="adjust-filter",
    )
    client = TestClient(
        create_app(
            auth_service=FakeAuthService(),  # type: ignore[arg-type]
            export_service=fake_service,  # type: ignore[arg-type]
        )
    )

    response = client.post(
        f"/api/projects/{PROJECT_ID}/exports/explorer",
        headers=auth_headers(),
        json={"cluster_set_id": str(CLUSTER_SET_ID), "export_format": "csv"},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "EXPLORER_EXPORT_EMPTY"
    assert response.json()["suggestedAction"] == "adjust-filter"


def test_explorer_export_api_maps_validation_problem_details() -> None:
    fake_service = FakeExportService()
    fake_service.raise_error = ExportError(
        "unsupported format",
        code="EXPLORER_EXPORT_FORMAT_INVALID",
        status_code=422,
        retryable=True,
        suggested_action="choose-format",
        field_errors={"export_format": "Export format must be csv or json."},
    )
    client = TestClient(
        create_app(
            auth_service=FakeAuthService(),  # type: ignore[arg-type]
            export_service=fake_service,  # type: ignore[arg-type]
        )
    )

    response = client.post(
        f"/api/projects/{PROJECT_ID}/exports/explorer",
        headers=auth_headers(),
        json={"cluster_set_id": str(CLUSTER_SET_ID), "export_format": "xlsx"},
    )

    assert response.status_code == 422
    payload = response.json()
    assert payload["type"] == "urn:skm:error:EXPLORER_EXPORT_FORMAT_INVALID"
    assert payload["code"] == "EXPLORER_EXPORT_FORMAT_INVALID"
    assert payload["detail"] != "unsupported format"
    assert payload["suggestedAction"] == "choose-format"
    assert payload["fieldErrors"] == [
        {"field": "export_format", "message": "Export format must be csv or json."}
    ]


def test_old_candidate_export_routes_are_not_active() -> None:
    client = TestClient(
        create_app(
            auth_service=FakeAuthService(),  # type: ignore[arg-type]
            export_service=FakeExportService(),  # type: ignore[arg-type]
        )
    )

    assert (
        client.post(
            f"/api/projects/{PROJECT_ID}/exports/candidates",
            headers=auth_headers(),
            json={},
        ).status_code
        == 404
    )
    assert (
        client.post(
            f"/api/projects/{PROJECT_ID}/exports/source-assignments",
            headers=auth_headers(),
            json={},
        ).status_code
        == 404
    )
