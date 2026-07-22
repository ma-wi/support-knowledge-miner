from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest

import backend.projects.service as project_service_module
from backend.projects import ProjectError, ProjectService


PROJECT_ID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
ACTOR_ID = UUID("11111111-1111-1111-1111-111111111111")
NOW = datetime(2026, 7, 22, tzinfo=UTC)


class FakeResult:
    def __init__(self, row: dict[str, object] | None = None, rowcount: int = 0) -> None:
        self._row = row
        self.rowcount = rowcount

    def fetchone(self) -> dict[str, object] | None:
        return self._row


class FakeTransaction:
    def __enter__(self) -> FakeTransaction:
        return self

    def __exit__(self, *_: object) -> None:
        return None


class RenameBetweenConfirmationAndDeleteConnection:
    deleted_without_confirmed_name = False

    def __enter__(self) -> RenameBetweenConfirmationAndDeleteConnection:
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def transaction(self) -> FakeTransaction:
        return FakeTransaction()

    def execute(
        self, query: str, params: tuple[object, ...] | None = None
    ) -> FakeResult:
        normalized = " ".join(query.split())
        if normalized.startswith("SELECT id, name"):
            return FakeResult(
                {
                    "id": PROJECT_ID,
                    "name": "Alpha",
                    "lifecycle_state": "active",
                    "created_at": NOW,
                    "updated_at": NOW,
                }
            )
        if normalized.startswith("DELETE FROM projects"):
            if "name = %s" in normalized:
                assert params == (PROJECT_ID, "Alpha")
                return FakeResult(None, rowcount=0)
            self.deleted_without_confirmed_name = True
            return FakeResult(rowcount=1)
        if normalized.startswith("INSERT INTO audit_events"):
            return FakeResult(rowcount=1)
        raise AssertionError(f"unexpected query: {normalized}")


def test_delete_project_rejects_stale_confirmation_when_name_changed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_connection = RenameBetweenConfirmationAndDeleteConnection()
    monkeypatch.setattr(
        project_service_module,
        "open_database_connection",
        lambda _: fake_connection,
    )

    with pytest.raises(ProjectError, match="confirmation"):
        ProjectService().delete_project(
            PROJECT_ID,
            actor_user_id=ACTOR_ID,
            confirmation_name="Alpha",
        )

    assert fake_connection.deleted_without_confirmed_name is False
