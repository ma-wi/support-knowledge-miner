"""Project lifecycle and isolation boundary."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

from backend.audit import AuditService
from backend.config import DatabaseSettings
from backend.db.connection import open_database_connection


class ProjectError(ValueError):
    """Raised when a project lifecycle operation is invalid."""


@dataclass(frozen=True)
class PublicProject:
    id: UUID
    name: str
    lifecycle_state: str
    created_at: datetime
    updated_at: datetime


def _clean_name(name: str) -> str:
    cleaned = name.strip()
    if not cleaned:
        raise ProjectError("project name must not be empty")
    return cleaned


def _project_from_row(row: dict[str, object]) -> PublicProject:
    return PublicProject(
        id=UUID(str(row["id"])),
        name=str(row["name"]),
        lifecycle_state=str(row["lifecycle_state"]),
        created_at=row["created_at"],  # type: ignore[arg-type]
        updated_at=row["updated_at"],  # type: ignore[arg-type]
    )


class ProjectService:
    def __init__(self, settings: DatabaseSettings | None = None) -> None:
        self._settings = settings
        self._audit = AuditService()

    def list_projects(self) -> list[PublicProject]:
        with open_database_connection(self._settings) as connection:
            rows = connection.execute(
                """
                SELECT id, name, lifecycle_state, created_at, updated_at
                FROM projects
                WHERE deleted_at IS NULL
                ORDER BY updated_at DESC, name ASC
                """
            ).fetchall()
        return [_project_from_row(dict(row)) for row in rows]

    def get_project(self, project_id: UUID) -> PublicProject | None:
        with open_database_connection(self._settings) as connection:
            row = connection.execute(
                """
                SELECT id, name, lifecycle_state, created_at, updated_at
                FROM projects
                WHERE id = %s AND deleted_at IS NULL
                """,
                (project_id,),
            ).fetchone()
        return _project_from_row(dict(row)) if row is not None else None

    def create_project(self, name: str, *, actor_user_id: UUID) -> PublicProject:
        project_id = uuid4()
        clean_name = _clean_name(name)
        with open_database_connection(self._settings) as connection:
            with connection.transaction():
                row = connection.execute(
                    """
                    INSERT INTO projects (
                        id, name, created_by_user_id, updated_by_user_id
                    )
                    VALUES (%s, %s, %s, %s)
                    RETURNING id, name, lifecycle_state, created_at, updated_at
                    """,
                    (project_id, clean_name, actor_user_id, actor_user_id),
                ).fetchone()
                if row is None:
                    raise RuntimeError("project insert returned no row")
                self._audit.record_event(
                    connection,
                    actor_user_id=actor_user_id,
                    action="project.create",
                    target_type="project",
                    target_id=project_id,
                    metadata={"name": clean_name},
                )
        return _project_from_row(dict(row))

    def rename_project(
        self, project_id: UUID, name: str, *, actor_user_id: UUID
    ) -> PublicProject:
        clean_name = _clean_name(name)
        with open_database_connection(self._settings) as connection:
            with connection.transaction():
                row = connection.execute(
                    """
                    UPDATE projects
                    SET name = %s,
                        updated_by_user_id = %s,
                        updated_at = now()
                    WHERE id = %s AND deleted_at IS NULL
                    RETURNING id, name, lifecycle_state, created_at, updated_at
                    """,
                    (clean_name, actor_user_id, project_id),
                ).fetchone()
                if row is None:
                    raise ProjectError("project not found")
                self._audit.record_event(
                    connection,
                    actor_user_id=actor_user_id,
                    action="project.rename",
                    target_type="project",
                    target_id=project_id,
                    metadata={"name": clean_name},
                )
        return _project_from_row(dict(row))

    def delete_project(
        self,
        project_id: UUID,
        *,
        actor_user_id: UUID,
        confirmation_name: str,
    ) -> None:
        with open_database_connection(self._settings) as connection:
            with connection.transaction():
                row = connection.execute(
                    """
                    DELETE FROM projects
                    WHERE id = %s
                      AND name = %s
                      AND deleted_at IS NULL
                    RETURNING name
                    """,
                    (project_id, confirmation_name),
                ).fetchone()
                if row is None:
                    raise ProjectError(
                        "project not found or deletion confirmation does not match project name"
                    )
                self._audit.record_event(
                    connection,
                    actor_user_id=actor_user_id,
                    action="project.delete",
                    target_type="project",
                    target_id=project_id,
                    metadata={"name": str(row["name"])},
                )
