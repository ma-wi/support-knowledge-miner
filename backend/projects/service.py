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
DEFAULT_LLM_TAXONOMY_MAX_SOURCE_CLUSTERS: Final = 200
MIN_LLM_TAXONOMY_MAX_SOURCE_CLUSTERS: Final = 1
HARD_MAX_LLM_TAXONOMY_SOURCE_CLUSTERS: Final = 500
DEFAULT_LLM_TAXONOMY_MAX_PROMPT_CHARACTERS: Final = 80_000
MIN_LLM_TAXONOMY_MAX_PROMPT_CHARACTERS: Final = 10_000
HARD_MAX_LLM_TAXONOMY_PROMPT_CHARACTERS: Final = 500_000
DEFAULT_CLUSTER_KEYWORD_MAX_TOTAL_TERMS: Final = 250_000
MIN_CLUSTER_KEYWORD_MAX_TOTAL_TERMS: Final = 1_000
HARD_MAX_CLUSTER_KEYWORD_TOTAL_TERMS: Final = 1_000_000
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
    llm_taxonomy_max_source_clusters: int = DEFAULT_LLM_TAXONOMY_MAX_SOURCE_CLUSTERS
    llm_taxonomy_max_prompt_characters: int = DEFAULT_LLM_TAXONOMY_MAX_PROMPT_CHARACTERS
    llm_taxonomy_max_total_keyword_terms: int = DEFAULT_CLUSTER_KEYWORD_MAX_TOTAL_TERMS


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


def _clean_budget(
    value: int | None,
    *,
    field: str,
    minimum: int,
    maximum: int,
) -> int:
    message = (
        f"Der Wert muss eine ganze Zahl zwischen {minimum:,} und {maximum:,} sein."
    ).replace(",", ".")
    if (
        value is None
        or isinstance(value, bool)
        or not isinstance(value, int)
        or value < minimum
        or value > maximum
    ):
        raise ProjectError(
            "project cluster budget is invalid",
            field_errors={field: message},
        )
    return value


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
        llm_taxonomy_max_source_clusters=int(
            str(
                row.get(
                    "llm_taxonomy_max_source_clusters",
                    DEFAULT_LLM_TAXONOMY_MAX_SOURCE_CLUSTERS,
                )
            )
        ),
        llm_taxonomy_max_prompt_characters=int(
            str(
                row.get(
                    "llm_taxonomy_max_prompt_characters",
                    DEFAULT_LLM_TAXONOMY_MAX_PROMPT_CHARACTERS,
                )
            )
        ),
        llm_taxonomy_max_total_keyword_terms=int(
            str(
                row.get(
                    "llm_taxonomy_max_total_keyword_terms",
                    DEFAULT_CLUSTER_KEYWORD_MAX_TOTAL_TERMS,
                )
            )
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
                    ticket_url_template,
                    llm_taxonomy_max_source_clusters,
                    llm_taxonomy_max_prompt_characters,
                    llm_taxonomy_max_total_keyword_terms
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
                    ticket_url_template,
                    llm_taxonomy_max_source_clusters,
                    llm_taxonomy_max_prompt_characters,
                    llm_taxonomy_max_total_keyword_terms
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
                        ticket_url_template,
                        llm_taxonomy_max_source_clusters,
                        llm_taxonomy_max_prompt_characters,
                        llm_taxonomy_max_total_keyword_terms
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
            llm_taxonomy_max_source_clusters_unchanged=True,
            llm_taxonomy_max_prompt_characters_unchanged=True,
            llm_taxonomy_max_total_keyword_terms_unchanged=True,
            actor_user_id=actor_user_id,
        )

    def update_project_settings(
        self,
        project_id: UUID,
        *,
        name: str,
        ticket_url_template: str | None = None,
        ticket_url_template_unchanged: bool = False,
        llm_taxonomy_max_source_clusters: int | None = None,
        llm_taxonomy_max_source_clusters_unchanged: bool = True,
        llm_taxonomy_max_prompt_characters: int | None = None,
        llm_taxonomy_max_prompt_characters_unchanged: bool = True,
        llm_taxonomy_max_total_keyword_terms: int | None = None,
        llm_taxonomy_max_total_keyword_terms_unchanged: bool = True,
        actor_user_id: UUID,
    ) -> PublicProject:
        clean_name = _clean_name(name)
        clean_template = (
            None
            if ticket_url_template_unchanged
            else _clean_ticket_url_template(ticket_url_template)
        )
        clean_source_clusters = (
            None
            if llm_taxonomy_max_source_clusters_unchanged
            else _clean_budget(
                llm_taxonomy_max_source_clusters,
                field="llm_taxonomy_max_source_clusters",
                minimum=MIN_LLM_TAXONOMY_MAX_SOURCE_CLUSTERS,
                maximum=HARD_MAX_LLM_TAXONOMY_SOURCE_CLUSTERS,
            )
        )
        clean_prompt_characters = (
            None
            if llm_taxonomy_max_prompt_characters_unchanged
            else _clean_budget(
                llm_taxonomy_max_prompt_characters,
                field="llm_taxonomy_max_prompt_characters",
                minimum=MIN_LLM_TAXONOMY_MAX_PROMPT_CHARACTERS,
                maximum=HARD_MAX_LLM_TAXONOMY_PROMPT_CHARACTERS,
            )
        )
        clean_keyword_terms = (
            None
            if llm_taxonomy_max_total_keyword_terms_unchanged
            else _clean_budget(
                llm_taxonomy_max_total_keyword_terms,
                field="llm_taxonomy_max_total_keyword_terms",
                minimum=MIN_CLUSTER_KEYWORD_MAX_TOTAL_TERMS,
                maximum=HARD_MAX_CLUSTER_KEYWORD_TOTAL_TERMS,
            )
        )
        with open_database_connection(self._settings) as connection:
            with connection.transaction():
                row = connection.execute(
                    """
                    UPDATE projects
                    SET name = %s,
                        ticket_url_template = CASE
                            WHEN %s THEN ticket_url_template ELSE %s END,
                        llm_taxonomy_max_source_clusters = CASE
                            WHEN %s THEN llm_taxonomy_max_source_clusters
                            ELSE %s END,
                        llm_taxonomy_max_prompt_characters = CASE
                            WHEN %s THEN llm_taxonomy_max_prompt_characters
                            ELSE %s END,
                        llm_taxonomy_max_total_keyword_terms = CASE
                            WHEN %s THEN llm_taxonomy_max_total_keyword_terms
                            ELSE %s END,
                        updated_by_user_id = %s,
                        updated_at = now()
                    WHERE id = %s AND deleted_at IS NULL
                    RETURNING
                        id, name, lifecycle_state, created_at, updated_at,
                        ticket_url_template,
                        llm_taxonomy_max_source_clusters,
                        llm_taxonomy_max_prompt_characters,
                        llm_taxonomy_max_total_keyword_terms
                    """,
                    (
                        clean_name,
                        ticket_url_template_unchanged,
                        clean_template,
                        llm_taxonomy_max_source_clusters_unchanged,
                        clean_source_clusters,
                        llm_taxonomy_max_prompt_characters_unchanged,
                        clean_prompt_characters,
                        llm_taxonomy_max_total_keyword_terms_unchanged,
                        clean_keyword_terms,
                        actor_user_id,
                        project_id,
                    ),
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
                        "llm_taxonomy_max_source_clusters": clean_source_clusters,
                        "llm_taxonomy_max_prompt_characters": clean_prompt_characters,
                        "llm_taxonomy_max_total_keyword_terms": clean_keyword_terms,
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
