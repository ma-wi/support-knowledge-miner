from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from backend.api import create_app
from backend.auth import CurrentUser
from backend.auth.service import AuthenticationError
from backend.imports import DatasetVersion, ImportLog, ImportLogEntry, ImportResult


OWNER_ID = UUID("11111111-1111-1111-1111-111111111111")
PROJECT_ID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
IMPORT_LOG_ID = UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")
DATASET_ID = UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee")
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


class FakeImportService:
    def __init__(self) -> None:
        self.received_actor: UUID | None = None

    def import_content(
        self,
        project_id: UUID,
        *,
        source_type: str,
        source_name: str,
        content: str,
        actor_user_id: UUID,
    ) -> ImportResult:
        assert project_id == PROJECT_ID
        assert source_type == "csv"
        assert source_name == "fixture.csv"
        assert "ticketid" in content
        self.received_actor = actor_user_id
        log = ImportLog(
            id=IMPORT_LOG_ID,
            project_id=project_id,
            source_type="csv",
            source_name="fixture.csv",
            status="completed",
            failure_reason=None,
            total_records=2,
            valid_records=1,
            skipped_records=1,
            dataset_version_id=DATASET_ID,
            started_at=NOW,
            completed_at=NOW,
        )
        dataset = DatasetVersion(
            id=DATASET_ID,
            project_id=project_id,
            version_number=1,
            import_log_id=IMPORT_LOG_ID,
            record_count=1,
            source_type="csv",
            source_name="fixture.csv",
            created_at=NOW,
        )
        return ImportResult(
            log=log,
            dataset_version=dataset,
            skipped_entries=[
                ImportLogEntry(
                    source_location="row 3",
                    reason="message must not be empty",
                    context={"ticketid": "T-2"},
                )
            ],
        )

    def list_logs(self, project_id: UUID) -> list[ImportLog]:
        return [
            ImportLog(
                id=IMPORT_LOG_ID,
                project_id=project_id,
                source_type="json",
                source_name="fixture.json",
                status="failed",
                failure_reason="no valid records found",
                total_records=1,
                valid_records=0,
                skipped_records=1,
                dataset_version_id=None,
                started_at=NOW,
                completed_at=NOW,
            )
        ]

    def get_log_entries(
        self, project_id: UUID, import_log_id: UUID
    ) -> list[ImportLogEntry]:
        assert project_id == PROJECT_ID
        assert import_log_id == IMPORT_LOG_ID
        return [
            ImportLogEntry(
                source_location="object 1",
                reason="answer must not be empty",
                context={"ticketid": "T-1"},
            )
        ]


@pytest.fixture
def fake_import_service() -> FakeImportService:
    return FakeImportService()


@pytest.fixture
def client(fake_import_service: FakeImportService) -> TestClient:
    return TestClient(
        create_app(
            auth_service=FakeAuthService(),  # type: ignore[arg-type]
            import_service=fake_import_service,  # type: ignore[arg-type]
        )
    )


def auth_headers(token: str = "valid-token") -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_import_routes_require_authentication(client: TestClient) -> None:
    response = client.post(
        f"/api/projects/{PROJECT_ID}/imports",
        json={"source_type": "csv", "source_name": "fixture.csv", "content": "x"},
    )

    assert response.status_code == 401


def test_import_content_returns_summary_dataset_and_skipped_entries(
    client: TestClient, fake_import_service: FakeImportService
) -> None:
    response = client.post(
        f"/api/projects/{PROJECT_ID}/imports",
        headers=auth_headers(),
        json={
            "source_type": "csv",
            "source_name": "fixture.csv",
            "content": "ticketid,messagegroupid,message,answer\nT-1,G-1,Hi,A\n",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["log"]["total_records"] == 2
    assert payload["log"]["valid_records"] == 1
    assert payload["dataset_version"]["id"] == str(DATASET_ID)
    assert payload["skipped_entries"][0]["source_location"] == "row 3"
    assert fake_import_service.received_actor == OWNER_ID


def test_import_log_listing_and_entry_detail(client: TestClient) -> None:
    logs = client.get(f"/api/projects/{PROJECT_ID}/imports", headers=auth_headers())
    assert logs.status_code == 200
    assert logs.json()[0]["status"] == "failed"
    assert logs.json()[0]["dataset_version_id"] is None

    entries = client.get(
        f"/api/projects/{PROJECT_ID}/imports/{IMPORT_LOG_ID}/entries",
        headers=auth_headers(),
    )
    assert entries.status_code == 200
    assert entries.json()[0]["reason"] == "answer must not be empty"
