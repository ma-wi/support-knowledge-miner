"""Project lifecycle and isolation boundary."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Final
from urllib.parse import urlsplit
from uuid import UUID, uuid4

from backend.audit import AuditService
from backend.config import DatabaseSettings
from backend.db.connection import open_database_connection


class ProjectError(ValueError):
    """Raised when a project lifecycle operation is invalid."""

    code = "VALIDATION_FAILED"
    status_code = 422
    retryable = True
    suggested_action = "correct-input"

    def __init__(
        self,
        message: str,
        *,
        field_errors: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.field_errors = field_errors or {}


class ProjectNotFoundError(ProjectError):
    """Raised when an active project does not exist."""

    code = "PROJECT_NOT_FOUND"
    status_code = 404
    retryable = True
    suggested_action = "reload"


MAX_TICKET_URL_TEMPLATE_LENGTH: Final = 2048
TICKET_ID_PLACEHOLDER: Final = "<ticket_id>"
_INVALID_TICKET_URL_TEMPLATE_MESSAGE: Final = (
    "Die Ticket-Link-Vorlage muss eine http(s)-URL mit <ticket_id> sein."
)


@dataclass(frozen=True)
class PublicProject:
    id: UUID
    name: str
    lifecycle_state: str
    created_at: datetime
    updated_at: datetime
    ticket_url_template: str | None = None


def _clean_name(name: str) -> str:
    cleaned = name.strip()
    if not cleaned:
        raise ProjectError("project name must not be empty")
    return cleaned


def _clean_ticket_url_template(template: str | None) -> str | None:
    if template is None:
        return None
    cleaned = template.strip()
    if cleaned == "":
        return None
    field_errors = {"ticket_url_template": _INVALID_TICKET_URL_TEMPLATE_MESSAGE}
    if (
        len(cleaned) > MAX_TICKET_URL_TEMPLATE_LENGTH
        or TICKET_ID_PLACEHOLDER not in cleaned
        or any(ord(character) <= 32 for character in cleaned)
    ):
        raise ProjectError(
            "ticket URL template is invalid",
            field_errors=field_errors,
        )
    parsed = urlsplit(cleaned)
    try:
        parsed.port
    except ValueError as exc:
        raise ProjectError(
            "ticket URL template is invalid",
            field_errors=field_errors,
        ) from exc
    if (
        parsed.scheme.lower() not in {"http", "https"}
        or not parsed.netloc
        or parsed.username is not None
        or parsed.password is not None
    ):
        raise ProjectError(
            "ticket URL template is invalid",
            field_errors=field_errors,
        )
    return cleaned


def _project_from_row(row: dict[str, object]) -> PublicProject:
    return PublicProject(
        id=UUID(str(row["id"])),
        name=str(row["name"]),
        lifecycle_state=str(row["lifecycle_state"]),
        created_at=row["created_at"],  # type: ignore[arg-type]
        updated_at=row["updated_at"],  # type: ignore[arg-type]
        ticket_url_template=(
            str(row["ticket_url_template"])
            if row.get("ticket_url_template") is not None
            else None
        ),
    )


class ProjectService:
    def __init__(self, settings: DatabaseSettings | None = None) -> None:
        self._settings = settings
        self._audit = AuditService()

    def list_projects(self) -> list[PublicProject]:
        with open_database_connection(self._settings) as connection:
            rows = connection.execute(
                """
                SELECT
                    id, name, lifecycle_state, created_at, updated_at,
                    ticket_url_template
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
                SELECT
                    id, name, lifecycle_state, created_at, updated_at,
                    ticket_url_template
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
                    RETURNING
                        id, name, lifecycle_state, created_at, updated_at,
                        ticket_url_template
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
        return self.update_project_settings(
            project_id,
            name=name,
            ticket_url_template_unchanged=True,
            actor_user_id=actor_user_id,
        )

    def update_project_settings(
        self,
        project_id: UUID,
        *,
        name: str,
        ticket_url_template: str | None = None,
        ticket_url_template_unchanged: bool = False,
        actor_user_id: UUID,
    ) -> PublicProject:
        clean_name = _clean_name(name)
        clean_template = _clean_ticket_url_template(ticket_url_template)
        with open_database_connection(self._settings) as connection:
            with connection.transaction():
                if ticket_url_template_unchanged:
                    row = connection.execute(
                        """
                        UPDATE projects
                        SET name = %s,
                            updated_by_user_id = %s,
                            updated_at = now()
                        WHERE id = %s AND deleted_at IS NULL
                        RETURNING
                            id, name, lifecycle_state, created_at, updated_at,
                            ticket_url_template
                        """,
                        (clean_name, actor_user_id, project_id),
                    ).fetchone()
                else:
                    row = connection.execute(
                        """
                        UPDATE projects
                        SET name = %s,
                            ticket_url_template = %s,
                            updated_by_user_id = %s,
                            updated_at = now()
                        WHERE id = %s AND deleted_at IS NULL
                        RETURNING
                            id, name, lifecycle_state, created_at, updated_at,
                            ticket_url_template
                        """,
                        (clean_name, clean_template, actor_user_id, project_id),
                    ).fetchone()
                if row is None:
                    raise ProjectNotFoundError("project not found")
                self._audit.record_event(
                    connection,
                    actor_user_id=actor_user_id,
                    action="project.update_settings",
                    target_type="project",
                    target_id=project_id,
                    metadata={
                        "name": clean_name,
                        "ticket_url_template_set": (
                            None
                            if ticket_url_template_unchanged
                            else clean_template is not None
                        ),
                    },
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
