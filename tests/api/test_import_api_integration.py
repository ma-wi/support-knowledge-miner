from __future__ import annotations

import asyncio
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from threading import Event
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException, Request
from fastapi.testclient import TestClient
from starlette.requests import ClientDisconnect

from backend.api import create_app
from backend.api.app import ImportCapacity, _spool_import_body
from backend.auth import CurrentUser
from backend.auth.service import AuthenticationError
from backend.imports import (
    DatasetVersion,
    ImportError,
    ImportLog,
    ImportLogEntry,
    ImportResult,
)


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
            first_name="Local",
            last_name="Owner",
            email="owner@example.test",
            created_at=NOW,
            updated_at=NOW,
            session_id=uuid4(),
        )


class FakeProviderService:
    def seed_ollama_provider_from_env(self) -> None:
        return None


class FakeImportService:
    def __init__(self) -> None:
        self.received_actor: UUID | None = None
        self.received_path: Path | None = None
        self.failure: Exception | None = None

    def import_file(
        self,
        project_id: UUID,
        *,
        source_type: str,
        source_name: str,
        source_path: Path,
        actor_user_id: UUID,
    ) -> ImportResult:
        assert project_id == PROJECT_ID
        assert source_type == "csv"
        assert source_name == "fixture.csv"
        assert "ticket_id" in source_path.read_text(encoding="utf-8")
        self.received_actor = actor_user_id
        self.received_path = source_path
        if self.failure is not None:
            raise self.failure
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
            dataset_display_name="fixture.csv",
            dataset_deleted_at=None,
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
            display_name="fixture.csv",
            deleted_at=None,
            created_at=NOW,
        )
        return ImportResult(
            log=log,
            dataset_version=dataset,
            skipped_entries=[
                ImportLogEntry(
                    source_location="row 3",
                    reason="message must not be empty",
                    context={"ticket_id": "T-2"},
                )
            ],
            skipped_entries_truncated=False,
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
                dataset_display_name=None,
                dataset_deleted_at=None,
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
                context={"ticket_id": "T-1"},
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
            provider_service=FakeProviderService(),  # type: ignore[arg-type]
        )
    )


def auth_headers(token: str = "valid-token") -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def import_headers(
    filename: str = "fixture.csv", content_type: str = "text/csv"
) -> dict[str, str]:
    return {
        **auth_headers(),
        "Content-Type": content_type,
        "Content-Disposition": f"attachment; filename*=UTF-8''{filename}",
    }


def test_import_routes_require_authentication(client: TestClient) -> None:
    response = client.post(
        f"/api/projects/{PROJECT_ID}/imports",
        content=b"x",
    )

    assert response.status_code == 401


def test_import_content_returns_summary_dataset_and_skipped_entries(
    client: TestClient, fake_import_service: FakeImportService
) -> None:
    response = client.post(
        f"/api/projects/{PROJECT_ID}/imports",
        headers=import_headers(),
        content=b"ticket_id,message_group_id,message,answer\nT-1,G-1,Hi,A\n",
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["log"]["total_records"] == 2
    assert payload["log"]["valid_records"] == 1
    assert payload["dataset_version"]["id"] == str(DATASET_ID)
    assert payload["skipped_entries"][0]["source_location"] == "row 3"
    assert payload["skipped_entries_truncated"] is False
    assert fake_import_service.received_actor == OWNER_ID
    assert fake_import_service.received_path is not None
    assert not fake_import_service.received_path.exists()


@pytest.mark.parametrize(
    ("headers", "expected_status", "expected_detail"),
    [
        (
            import_headers(content_type="application/octet-stream"),
            415,
            "Nicht unterstützter Dateityp",
        ),
        (
            import_headers(filename="fixture.json"),
            415,
            "Dateiendung und Medientyp passen nicht zusammen",
        ),
        (
            {**auth_headers(), "Content-Type": "text/csv"},
            400,
            "Dateiname fehlt oder ist ungültig",
        ),
    ],
)
def test_import_rejects_invalid_media_metadata(
    client: TestClient,
    headers: dict[str, str],
    expected_status: int,
    expected_detail: str,
) -> None:
    response = client.post(
        f"/api/projects/{PROJECT_ID}/imports",
        headers=headers,
        content=b"x",
    )

    assert response.status_code == expected_status
    assert expected_detail in response.json()["detail"]


def test_streamed_body_enforces_actual_bytes_and_removes_temp_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    import backend.api.app as app_module

    monkeypatch.setattr(app_module, "MAX_IMPORT_BYTES", 5)
    monkeypatch.setattr(app_module.tempfile, "tempdir", str(tmp_path))
    messages: Iterator[dict[str, object]] = iter(
        [
            {"type": "http.request", "body": b"123", "more_body": True},
            {"type": "http.request", "body": b"456", "more_body": False},
        ]
    )

    async def receive() -> dict[str, object]:
        return next(messages)

    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/imports",
            "headers": [],
        },
        receive,
    )

    with pytest.raises(HTTPException) as captured:
        asyncio.run(_spool_import_body(request))

    assert captured.value.status_code == 413
    assert "6 Byte" in str(captured.value.detail)
    assert list(tmp_path.iterdir()) == []


def test_streamed_body_accepts_exact_boundary(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    import backend.api.app as app_module

    monkeypatch.setattr(app_module, "MAX_IMPORT_BYTES", 5)
    monkeypatch.setattr(app_module.tempfile, "tempdir", str(tmp_path))
    messages = iter(
        [
            {"type": "http.request", "body": b"12", "more_body": True},
            {"type": "http.request", "body": b"345", "more_body": False},
        ]
    )

    async def receive() -> dict[str, object]:
        return next(messages)

    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/imports",
            "headers": [],
        },
        receive,
    )

    source_path = asyncio.run(_spool_import_body(request))
    try:
        assert source_path.read_bytes() == b"12345"
    finally:
        source_path.unlink()

    assert list(tmp_path.iterdir()) == []


def test_streamed_body_removes_temp_file_after_disconnect(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    import backend.api.app as app_module

    monkeypatch.setattr(app_module.tempfile, "tempdir", str(tmp_path))
    messages: Iterator[dict[str, object]] = iter(
        [
            {"type": "http.request", "body": b"12", "more_body": True},
            {"type": "http.disconnect"},
        ]
    )

    async def receive() -> dict[str, object]:
        return next(messages)

    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/imports",
            "headers": [],
        },
        receive,
    )

    with pytest.raises(ClientDisconnect):
        asyncio.run(_spool_import_body(request))

    assert list(tmp_path.iterdir()) == []


def test_streamed_body_times_out_idle_upload_and_removes_temp_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    import backend.api.app as app_module

    monkeypatch.setattr(app_module, "IMPORT_CHUNK_IDLE_TIMEOUT_SECONDS", 0.001)
    monkeypatch.setattr(app_module.tempfile, "tempdir", str(tmp_path))

    messages: Iterator[dict[str, object]] = iter(
        [{"type": "http.request", "body": b"", "more_body": True}]
    )

    async def receive() -> dict[str, object]:
        try:
            return next(messages)
        except StopIteration:
            await asyncio.Event().wait()
            return {}

    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/imports",
            "headers": [],
        },
        receive,
    )

    with pytest.raises(HTTPException) as captured:
        asyncio.run(_spool_import_body(request))

    assert captured.value.status_code == 408
    assert list(tmp_path.iterdir()) == []


def test_import_capacity_rejects_overload_and_releases_after_failure() -> None:
    fake_service = FakeImportService()
    capacity = ImportCapacity(limit=1)
    assert capacity.try_acquire() is True
    with TestClient(
        create_app(
            auth_service=FakeAuthService(),  # type: ignore[arg-type]
            import_service=fake_service,  # type: ignore[arg-type]
            import_capacity=capacity,
            provider_service=FakeProviderService(),  # type: ignore[arg-type]
        )
    ) as overload_client:
        overloaded = overload_client.post(
            f"/api/projects/{PROJECT_ID}/imports",
            headers=import_headers(),
            content=b"x",
        )
        assert overloaded.status_code == 503
        assert overloaded.headers["Retry-After"] == "5"

        capacity.release()
        fake_service.failure = ImportError("Persistenz fehlgeschlagen.")
        failed = overload_client.post(
            f"/api/projects/{PROJECT_ID}/imports",
            headers=import_headers(),
            content=b"ticket_id,message_group_id,message,answer\n",
        )

    assert failed.status_code == 400
    assert capacity.try_acquire() is True
    capacity.release()
    assert fake_service.received_path is not None
    assert not fake_service.received_path.exists()


def test_import_capacity_rejects_parallel_request_and_releases_after_success() -> None:
    class BlockingImportService(FakeImportService):
        def __init__(self) -> None:
            super().__init__()
            self.started = Event()
            self.resume = Event()

        def import_file(self, *args: object, **kwargs: object) -> ImportResult:
            self.started.set()
            if not self.resume.wait(timeout=5):
                raise RuntimeError("test import was not resumed")
            return super().import_file(*args, **kwargs)  # type: ignore[arg-type]

    fake_service = BlockingImportService()
    capacity = ImportCapacity(limit=1)
    with TestClient(
        create_app(
            auth_service=FakeAuthService(),  # type: ignore[arg-type]
            import_service=fake_service,  # type: ignore[arg-type]
            import_capacity=capacity,
            provider_service=FakeProviderService(),  # type: ignore[arg-type]
        )
    ) as parallel_client:
        with ThreadPoolExecutor(max_workers=1) as executor:
            first_response = executor.submit(
                parallel_client.post,
                f"/api/projects/{PROJECT_ID}/imports",
                headers=import_headers(),
                content=b"ticket_id,message_group_id,message,answer\n",
            )
            assert fake_service.started.wait(timeout=5)
            overloaded = parallel_client.post(
                f"/api/projects/{PROJECT_ID}/imports",
                headers=import_headers(),
                content=b"x",
            )
            fake_service.resume.set()
            completed = first_response.result(timeout=5)

    assert overloaded.status_code == 503
    assert completed.status_code == 201
    assert capacity.try_acquire() is True
    capacity.release()


def test_streamed_body_removes_temp_file_when_cancelled(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    import backend.api.app as app_module

    monkeypatch.setattr(app_module.tempfile, "tempdir", str(tmp_path))

    async def run_cancelled_upload() -> None:
        async def receive() -> dict[str, object]:
            await asyncio.Event().wait()
            return {}

        request = Request(
            {
                "type": "http",
                "method": "POST",
                "path": "/imports",
                "headers": [],
            },
            receive,
        )
        task = asyncio.create_task(_spool_import_body(request))
        await asyncio.sleep(0)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(run_cancelled_upload())

    assert list(tmp_path.iterdir()) == []


def test_slow_drip_hits_total_timeout_and_releases_route_capacity(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    import backend.api.app as app_module

    monkeypatch.setattr(app_module, "IMPORT_CHUNK_IDLE_TIMEOUT_SECONDS", 0.05)
    monkeypatch.setattr(app_module, "IMPORT_TOTAL_TIMEOUT_SECONDS", 0.12)
    monkeypatch.setattr(app_module.tempfile, "tempdir", str(tmp_path))
    capacity = ImportCapacity(limit=1)
    app = create_app(
        auth_service=FakeAuthService(),  # type: ignore[arg-type]
        import_service=FakeImportService(),  # type: ignore[arg-type]
        import_capacity=capacity,
    )
    sent_messages: list[dict[str, object]] = []
    received_chunks = 0

    async def receive() -> dict[str, object]:
        nonlocal received_chunks
        await asyncio.sleep(0.03)
        received_chunks += 1
        return {
            "type": "http.request",
            "body": b"x",
            "more_body": True,
        }

    async def send(message: dict[str, object]) -> None:
        sent_messages.append(message)

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": f"/api/projects/{PROJECT_ID}/imports",
        "raw_path": f"/api/projects/{PROJECT_ID}/imports".encode(),
        "query_string": b"",
        "root_path": "",
        "headers": [
            (b"authorization", b"Bearer valid-token"),
            (b"content-type", b"text/csv"),
            (
                b"content-disposition",
                b"attachment; filename*=UTF-8''slow.csv",
            ),
        ],
        "client": ("127.0.0.1", 12345),
        "server": ("127.0.0.1", 8080),
    }

    asyncio.run(app(scope, receive, send))  # type: ignore[arg-type]

    response_start = next(
        message for message in sent_messages if message["type"] == "http.response.start"
    )
    response_body_parts = [
        body
        for message in sent_messages
        if message["type"] == "http.response.body"
        and isinstance((body := message.get("body")), bytes)
    ]
    response_body = b"".join(response_body_parts)
    assert response_start["status"] == 408
    assert b"Maximale Uploaddauer" in response_body
    assert received_chunks >= 3
    assert list(tmp_path.iterdir()) == []
    assert capacity.try_acquire() is True
    capacity.release()


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
