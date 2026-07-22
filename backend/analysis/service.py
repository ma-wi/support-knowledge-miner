"""Analysis-run scaffold and embedding persistence seam."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
import threading
from typing import Any
from uuid import UUID, uuid4

from psycopg.types.json import Jsonb

from backend.audit import AuditService
from backend.config import DatabaseSettings
from backend.db.connection import open_database_connection

RUN_STATUSES = {"queued", "running", "completed", "failed", "cancelled"}
EMBEDDING_DIMENSIONS = 3


class AnalysisError(ValueError):
    """Raised when analysis-run input or state is invalid."""


class LocalBackgroundJobRunner:
    """Small local background seam for MVP analysis scaffolds."""

    def submit(self, task: Callable[[], None]) -> None:
        thread = threading.Thread(
            target=task,
            name="skm-analysis-run",
            daemon=True,
        )
        thread.start()


@dataclass(frozen=True)
class AnalysisRunInput:
    dataset_version_id: UUID
    analysis_profile_id: UUID
    parameters: dict[str, Any]


@dataclass(frozen=True)
class AnalysisRun:
    id: UUID
    project_id: UUID
    dataset_version_id: UUID
    analysis_profile_id: UUID
    status: str
    progress: int
    profile_snapshot: dict[str, Any]
    provider: str
    model: str
    parameters: dict[str, Any]
    error_message: str | None
    diagnostics: dict[str, Any]
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class EmbeddingRecord:
    id: UUID
    project_id: UUID
    analysis_run_id: UUID
    dataset_version_id: UUID
    analysis_profile_id: UUID
    source_object_type: str
    source_object_id: UUID
    text_variant: str
    model: str
    dimensions: int
    metadata: dict[str, Any]
    created_at: datetime


def _object(value: dict[str, Any], field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise AnalysisError(f"{field} must be an object")
    return value


def _run_from_row(row: dict[str, object]) -> AnalysisRun:
    profile_snapshot = row["profile_snapshot"]
    parameters = row["parameters"]
    diagnostics = row["diagnostics"]
    return AnalysisRun(
        id=UUID(str(row["id"])),
        project_id=UUID(str(row["project_id"])),
        dataset_version_id=UUID(str(row["dataset_version_id"])),
        analysis_profile_id=UUID(str(row["analysis_profile_id"])),
        status=str(row["status"]),
        progress=int(str(row["progress"])),
        profile_snapshot=(
            dict(profile_snapshot) if isinstance(profile_snapshot, dict) else {}
        ),
        provider=str(row["provider"]),
        model=str(row["model"]),
        parameters=dict(parameters) if isinstance(parameters, dict) else {},
        error_message=(
            str(row["error_message"]) if row["error_message"] is not None else None
        ),
        diagnostics=dict(diagnostics) if isinstance(diagnostics, dict) else {},
        started_at=row["started_at"],  # type: ignore[arg-type]
        completed_at=row["completed_at"],  # type: ignore[arg-type]
        created_at=row["created_at"],  # type: ignore[arg-type]
        updated_at=row["updated_at"],  # type: ignore[arg-type]
    )


def _embedding_from_row(row: dict[str, object]) -> EmbeddingRecord:
    metadata = row["metadata"]
    return EmbeddingRecord(
        id=UUID(str(row["id"])),
        project_id=UUID(str(row["project_id"])),
        analysis_run_id=UUID(str(row["analysis_run_id"])),
        dataset_version_id=UUID(str(row["dataset_version_id"])),
        analysis_profile_id=UUID(str(row["analysis_profile_id"])),
        source_object_type=str(row["source_object_type"]),
        source_object_id=UUID(str(row["source_object_id"])),
        text_variant=str(row["text_variant"]),
        model=str(row["model"]),
        dimensions=int(str(row["dimensions"])),
        metadata=dict(metadata) if isinstance(metadata, dict) else {},
        created_at=row["created_at"],  # type: ignore[arg-type]
    )


def _datetime_iso(value: object, field: str) -> str:
    if not isinstance(value, datetime):
        raise AnalysisError(f"{field} must be a datetime")
    return value.isoformat()


class AnalysisService:
    def __init__(
        self,
        settings: DatabaseSettings | None = None,
        *,
        job_runner: LocalBackgroundJobRunner | None = None,
    ) -> None:
        self._settings = settings
        self._audit = AuditService()
        self._job_runner = job_runner or LocalBackgroundJobRunner()

    def start_run(
        self,
        project_id: UUID,
        payload: AnalysisRunInput,
        *,
        actor_user_id: UUID,
    ) -> AnalysisRun:
        parameters = _object(payload.parameters, "parameters")
        run_id = uuid4()
        with open_database_connection(self._settings) as connection:
            with connection.transaction():
                dataset = connection.execute(
                    """
                    SELECT id, record_count
                    FROM dataset_versions
                    WHERE id = %s AND project_id = %s
                    """,
                    (payload.dataset_version_id, project_id),
                ).fetchone()
                if dataset is None:
                    raise AnalysisError("dataset version not found")

                profile = connection.execute(
                    """
                    SELECT id, name, provider, model, is_cloud_provider,
                           thresholds, algorithm_settings, prompt_identifier,
                           prompt_template, created_at, updated_at
                    FROM analysis_profiles
                    WHERE id = %s AND project_id = %s
                    """,
                    (payload.analysis_profile_id, project_id),
                ).fetchone()
                if profile is None:
                    raise AnalysisError("analysis profile not found")

                snapshot = self._profile_snapshot(dict(profile))
                row = connection.execute(
                    """
                    INSERT INTO analysis_runs (
                        id, project_id, dataset_version_id, analysis_profile_id,
                        status, progress, profile_snapshot, provider, model,
                        parameters, created_by_user_id
                    )
                    VALUES (%s, %s, %s, %s, 'queued', 0, %s, %s, %s, %s, %s)
                    RETURNING id, project_id, dataset_version_id, analysis_profile_id,
                              status, progress, profile_snapshot, provider, model,
                              parameters, error_message, diagnostics, started_at,
                              completed_at, created_at, updated_at
                    """,
                    (
                        run_id,
                        project_id,
                        payload.dataset_version_id,
                        payload.analysis_profile_id,
                        Jsonb(snapshot),
                        snapshot["provider"],
                        snapshot["model"],
                        Jsonb(parameters),
                        actor_user_id,
                    ),
                ).fetchone()
                if row is None:
                    raise RuntimeError("analysis run insert returned no row")
                self._audit.record_event(
                    connection,
                    actor_user_id=actor_user_id,
                    action="analysis_run.start",
                    target_type="analysis_run",
                    target_id=run_id,
                    metadata={
                        "project_id": str(project_id),
                        "dataset_version_id": str(payload.dataset_version_id),
                        "analysis_profile_id": str(payload.analysis_profile_id),
                        "provider": snapshot["provider"],
                        "model": snapshot["model"],
                    },
                )
        return _run_from_row(dict(row))

    def enqueue_run(self, run_id: UUID) -> None:
        self._job_runner.submit(lambda: self.execute_queued_run(run_id))

    def list_runs(self, project_id: UUID) -> list[AnalysisRun]:
        with open_database_connection(self._settings) as connection:
            rows = connection.execute(
                """
                SELECT id, project_id, dataset_version_id, analysis_profile_id,
                       status, progress, profile_snapshot, provider, model,
                       parameters, error_message, diagnostics, started_at,
                       completed_at, created_at, updated_at
                FROM analysis_runs
                WHERE project_id = %s
                ORDER BY created_at DESC
                """,
                (project_id,),
            ).fetchall()
        return [_run_from_row(dict(row)) for row in rows]

    def get_run(self, project_id: UUID, run_id: UUID) -> AnalysisRun | None:
        with open_database_connection(self._settings) as connection:
            row = connection.execute(
                """
                SELECT id, project_id, dataset_version_id, analysis_profile_id,
                       status, progress, profile_snapshot, provider, model,
                       parameters, error_message, diagnostics, started_at,
                       completed_at, created_at, updated_at
                FROM analysis_runs
                WHERE id = %s AND project_id = %s
                """,
                (run_id, project_id),
            ).fetchone()
        return _run_from_row(dict(row)) if row is not None else None

    def list_embeddings(self, project_id: UUID, run_id: UUID) -> list[EmbeddingRecord]:
        with open_database_connection(self._settings) as connection:
            rows = connection.execute(
                """
                SELECT id, project_id, analysis_run_id, dataset_version_id,
                       analysis_profile_id, source_object_type, source_object_id,
                       text_variant, model, dimensions, metadata, created_at
                FROM embeddings
                WHERE project_id = %s AND analysis_run_id = %s
                ORDER BY created_at ASC, text_variant ASC
                """,
                (project_id, run_id),
            ).fetchall()
        return [_embedding_from_row(dict(row)) for row in rows]

    def execute_queued_run(self, run_id: UUID) -> None:
        with open_database_connection(self._settings) as connection:
            with connection.transaction():
                run_row = connection.execute(
                    """
                    UPDATE analysis_runs
                    SET status = 'running', progress = 5, started_at = now(),
                        updated_at = now()
                    WHERE id = %s AND status = 'queued'
                    RETURNING id, project_id, dataset_version_id,
                              analysis_profile_id, model
                    """,
                    (run_id,),
                ).fetchone()
                if run_row is None:
                    return
                try:
                    pairs = connection.execute(
                        """
                        SELECT id, ordinal, message, answer
                        FROM message_pairs
                        WHERE project_id = %s AND dataset_version_id = %s
                        ORDER BY ordinal ASC
                        """,
                        (run_row["project_id"], run_row["dataset_version_id"]),
                    ).fetchall()
                    for pair in pairs:
                        for variant in ("message", "answer"):
                            text = str(pair[variant])
                            connection.execute(
                                """
                                INSERT INTO embeddings (
                                    id, project_id, analysis_run_id,
                                    dataset_version_id, analysis_profile_id,
                                    source_object_type, source_object_id,
                                    text_variant, model, dimensions, embedding,
                                    metadata
                                )
                                VALUES (
                                    %s, %s, %s, %s, %s, 'message_pair', %s,
                                    %s, %s, %s, NULL, %s
                                )
                                """,
                                (
                                    uuid4(),
                                    run_row["project_id"],
                                    run_id,
                                    run_row["dataset_version_id"],
                                    run_row["analysis_profile_id"],
                                    pair["id"],
                                    variant,
                                    run_row["model"],
                                    EMBEDDING_DIMENSIONS,
                                    Jsonb(
                                        {
                                            "scaffold": "deterministic-local",
                                            "source_length": len(text),
                                            "source_ordinal": pair["ordinal"],
                                        }
                                    ),
                                ),
                            )
                    connection.execute(
                        """
                        UPDATE analysis_runs
                        SET status = 'completed', progress = 100,
                            completed_at = now(), updated_at = now(),
                            diagnostics = %s
                        WHERE id = %s
                        """,
                        (
                            Jsonb(
                                {
                                    "scaffold": "deterministic-local",
                                    "message_pairs": len(pairs),
                                    "embeddings_written": len(pairs) * 2,
                                }
                            ),
                            run_id,
                        ),
                    )
                except Exception as exc:
                    connection.execute(
                        """
                        UPDATE analysis_runs
                        SET status = 'failed', progress = 100,
                            error_message = %s, completed_at = now(),
                            updated_at = now(), diagnostics = %s
                        WHERE id = %s
                        """,
                        (
                            exc.__class__.__name__,
                            Jsonb({"scaffold": "deterministic-local"}),
                            run_id,
                        ),
                    )

    def _profile_snapshot(self, profile: dict[str, object]) -> dict[str, Any]:
        thresholds = profile["thresholds"]
        algorithm_settings = profile["algorithm_settings"]
        return {
            "id": str(profile["id"]),
            "name": str(profile["name"]),
            "provider": str(profile["provider"]),
            "model": str(profile["model"]),
            "is_cloud_provider": bool(profile["is_cloud_provider"]),
            "thresholds": dict(thresholds) if isinstance(thresholds, dict) else {},
            "algorithm_settings": (
                dict(algorithm_settings) if isinstance(algorithm_settings, dict) else {}
            ),
            "prompt_identifier": (
                str(profile["prompt_identifier"])
                if profile["prompt_identifier"] is not None
                else None
            ),
            "prompt_template": (
                str(profile["prompt_template"])
                if profile["prompt_template"] is not None
                else None
            ),
            "created_at": _datetime_iso(profile["created_at"], "created_at"),
            "updated_at": _datetime_iso(profile["updated_at"], "updated_at"),
        }
