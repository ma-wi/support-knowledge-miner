"""Profile-free indexing orchestration and bounded embedding persistence."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from datetime import datetime
import logging
import math
from queue import Full, Queue
from threading import Thread
from typing import Any
from uuid import UUID, uuid4

from psycopg.types.json import Jsonb

from backend.audit import AuditService
from backend.config import DatabaseSettings
from backend.db.connection import open_database_connection
from backend.providers import ProviderError, ProviderService

INDEXING_STATUSES = {
    "queued",
    "running",
    "cancelling",
    "completed",
    "failed",
    "cancelled",
}
TERMINAL_INDEXING_STATUSES = {"completed", "failed", "cancelled"}
SUPPORTED_EMBEDDING_PROVIDERS = {"openai", "ollama", "vllm"}
EMBEDDING_BATCH_SIZE = 64
MAX_EMBEDDING_CHUNK_BYTES = 1024
RUN_START_PROGRESS = 5
RUN_MAX_WORKING_PROGRESS = 95
LOGGER = logging.getLogger(__name__)


class AnalysisError(ValueError):
    """Raised when indexing input or state is invalid."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "UNEXPECTED_ERROR",
        status_code: int = 400,
        retryable: bool = True,
        suggested_action: str = "retry",
        field_errors: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code
        self.retryable = retryable
        self.suggested_action = suggested_action
        self.field_errors = field_errors or {}


IndexingError = AnalysisError


class AnalysisQueueFull(AnalysisError):
    """Raised when bounded local indexing capacity is exhausted."""

    def __init__(self, message: str) -> None:
        super().__init__(
            message,
            code="UNEXPECTED_ERROR",
            status_code=503,
            retryable=True,
            suggested_action="retry",
        )


class IndexingCancelled(Exception):
    """Internal control-flow exception for cooperative cancellation."""


class LocalBackgroundJobRunner:
    """Fixed daemon workers with a bounded local in-memory queue."""

    def __init__(self, *, worker_count: int = 2, queue_capacity: int = 8) -> None:
        if worker_count < 1 or queue_capacity < 1:
            raise ValueError("worker_count and queue_capacity must be positive")
        self._queue: Queue[Callable[[], None]] = Queue(maxsize=queue_capacity)
        self._workers = [
            Thread(
                target=self._work,
                name=f"skm-indexing-worker-{index + 1}",
                daemon=True,
            )
            for index in range(worker_count)
        ]
        for worker in self._workers:
            worker.start()

    def submit(self, task: Callable[[], None]) -> None:
        try:
            self._queue.put_nowait(task)
        except Full as exc:
            raise AnalysisQueueFull(
                "local indexing capacity is exhausted; retry later"
            ) from exc

    def _work(self) -> None:
        while True:
            task = self._queue.get()
            try:
                task()
            except Exception as exc:
                # AnalysisService persists safe run failures. Keep the fixed worker
                # alive if an unexpected task implementation still escapes.
                LOGGER.error(
                    "indexing background task failed unexpectedly: %s",
                    exc.__class__.__name__,
                )
            finally:
                self._queue.task_done()


@dataclass(frozen=True)
class IndexingRunInput:
    dataset_version_id: UUID
    provider: str
    model: str
    parameters: dict[str, Any] = field(default_factory=dict)
    cloud_use_confirmed: bool = False


@dataclass(frozen=True)
class IndexingRun:
    id: UUID
    project_id: UUID
    dataset_version_id: UUID
    dataset_display_name: str | None
    dataset_deleted_at: datetime | None
    status: str
    progress: int
    phase: str
    provider: str
    model: str
    parameters: dict[str, Any]
    error_code: str | None
    error_message: str | None
    diagnostics: dict[str, Any]
    started_at: datetime | None
    completed_at: datetime | None
    cancel_requested_at: datetime | None
    deleted_at: datetime | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class EmbeddingRecord:
    id: UUID
    project_id: UUID
    indexing_run_id: UUID
    dataset_version_id: UUID
    source_object_type: str
    source_object_id: UUID
    text_variant: str
    model: str
    dimensions: int
    metadata: dict[str, Any]
    created_at: datetime


# Transitional aliases keep internal imports stable while the active API contract
# has moved to IndexingRun naming.
AnalysisRunInput = IndexingRunInput
AnalysisRun = IndexingRun


def _object(value: dict[str, Any], field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise AnalysisError(f"{field} must be an object")
    return value


def _provider(provider: str) -> str:
    cleaned = provider.strip().lower()
    if cleaned not in SUPPORTED_EMBEDDING_PROVIDERS:
        raise AnalysisError(
            "provider must be openai, ollama, or vllm",
            code="INDEXING_MODEL_UNAVAILABLE",
            status_code=422,
            suggested_action="correct-input",
            field_errors={"provider": "provider must be openai, ollama, or vllm"},
        )
    return cleaned


def _model(model: str) -> str:
    cleaned = model.strip()
    if not cleaned:
        raise AnalysisError(
            "model must not be empty",
            code="INDEXING_MODEL_UNAVAILABLE",
            status_code=422,
            suggested_action="correct-input",
            field_errors={"model": "model must not be empty"},
        )
    return cleaned


def _run_from_row(row: dict[str, object]) -> IndexingRun:
    parameters = row["parameters"]
    diagnostics = row["diagnostics"]
    dataset_deleted_at = row.get("dataset_deleted_at")
    return IndexingRun(
        id=UUID(str(row["id"])),
        project_id=UUID(str(row["project_id"])),
        dataset_version_id=UUID(str(row["dataset_version_id"])),
        dataset_display_name=(
            str(row["dataset_display_name"])
            if row.get("dataset_display_name") is not None
            else None
        ),
        dataset_deleted_at=(
            dataset_deleted_at  # type: ignore[assignment]
            if isinstance(dataset_deleted_at, datetime)
            else None
        ),
        status=str(row["status"]),
        progress=int(str(row["progress"])),
        phase=str(row["phase"]),
        provider=str(row["provider"]),
        model=str(row["model"]),
        parameters=dict(parameters) if isinstance(parameters, dict) else {},
        error_code=str(row["error_code"]) if row["error_code"] is not None else None,
        error_message=(
            str(row["error_message"]) if row["error_message"] is not None else None
        ),
        diagnostics=dict(diagnostics) if isinstance(diagnostics, dict) else {},
        started_at=row["started_at"],  # type: ignore[arg-type]
        completed_at=row["completed_at"],  # type: ignore[arg-type]
        cancel_requested_at=row["cancel_requested_at"],  # type: ignore[arg-type]
        deleted_at=row["deleted_at"],  # type: ignore[arg-type]
        created_at=row["created_at"],  # type: ignore[arg-type]
        updated_at=row["updated_at"],  # type: ignore[arg-type]
    )


def _embedding_from_row(row: dict[str, object]) -> EmbeddingRecord:
    metadata = row["metadata"]
    return EmbeddingRecord(
        id=UUID(str(row["id"])),
        project_id=UUID(str(row["project_id"])),
        indexing_run_id=UUID(str(row["indexing_run_id"])),
        dataset_version_id=UUID(str(row["dataset_version_id"])),
        source_object_type=str(row["source_object_type"]),
        source_object_id=UUID(str(row["source_object_id"])),
        text_variant=str(row["text_variant"]),
        model=str(row["model"]),
        dimensions=int(str(row["dimensions"])),
        metadata=dict(metadata) if isinstance(metadata, dict) else {},
        created_at=row["created_at"],  # type: ignore[arg-type]
    )


def _vector_literal(vector: list[float]) -> str:
    return "[" + ",".join(format(value, ".17g") for value in vector) + "]"


def _utf8_byte_length(text: str) -> int:
    return sum(
        1
        if codepoint <= 0x7F
        else 2
        if codepoint <= 0x7FF
        else 3
        if codepoint <= 0xFFFF
        else 4
        for codepoint in map(ord, text)
    )


def _text_chunks(
    text: str, *, max_bytes: int = MAX_EMBEDDING_CHUNK_BYTES
) -> Iterator[str]:
    if max_bytes < 4:
        raise ValueError("max_bytes must fit one UTF-8 character")
    cleaned = text.strip()
    if not cleaned:
        raise AnalysisError("embedding input must not be empty")

    start = 0
    yielded = False
    while start < len(cleaned):
        while start < len(cleaned) and cleaned[start].isspace():
            start += 1
        if start >= len(cleaned):
            break

        cursor = start
        used_bytes = 0
        whitespace_split: int | None = None
        whitespace_bytes = 0
        while cursor < len(cleaned):
            character_bytes = len(cleaned[cursor].encode("utf-8"))
            if used_bytes + character_bytes > max_bytes:
                break
            used_bytes += character_bytes
            cursor += 1
            if cleaned[cursor - 1].isspace():
                whitespace_split = cursor
                whitespace_bytes = used_bytes

        if cursor == len(cleaned):
            split = cursor
        elif whitespace_split is not None and whitespace_bytes >= max_bytes // 2:
            split = whitespace_split
        else:
            split = cursor
        chunk = cleaned[start:split].strip()
        if chunk:
            yielded = True
            yield chunk
        start = split

    if not yielded:
        raise AnalysisError("embedding input must not be empty")


def _message_embeddings(
    provider_service: ProviderService,
    provider: str,
    model: str,
    messages: list[str],
    *,
    on_provider_batch_confirmed: Callable[[], None] | None = None,
) -> list[tuple[list[float], int, int, str]]:
    weighted_sums: list[list[float] | None] = [None] * len(messages)
    first_vectors: list[list[float] | None] = [None] * len(messages)
    total_weights = [0] * len(messages)
    chunk_counts = [0] * len(messages)
    source_bytes = [_utf8_byte_length(message) for message in messages]
    dimensions: int | None = None

    def embed_batch(batch: list[tuple[int, str, int]]) -> None:
        nonlocal dimensions
        vectors = provider_service.embed_texts(
            provider,
            model,
            [chunk for _, chunk, _ in batch],
        )
        if len(vectors) != len(batch):
            raise AnalysisError("provider returned the wrong number of vectors")
        for (message_index, _, weight), vector in zip(batch, vectors, strict=True):
            if not vector or any(not math.isfinite(value) for value in vector):
                raise AnalysisError("provider returned an invalid embedding vector")
            if dimensions is None:
                dimensions = len(vector)
            elif len(vector) != dimensions:
                raise AnalysisError(
                    "provider returned inconsistent embedding dimensions"
                )
            if first_vectors[message_index] is None:
                first_vectors[message_index] = list(vector)
                weighted_sums[message_index] = [0.0] * len(vector)
            weighted_sum = weighted_sums[message_index]
            if weighted_sum is None:
                raise RuntimeError("embedding accumulator was not initialized")
            for index, value in enumerate(vector):
                weighted_sum[index] += value * weight
            total_weights[message_index] += weight
        if on_provider_batch_confirmed is not None:
            on_provider_batch_confirmed()

    batch: list[tuple[int, str, int]] = []
    for message_index, message in enumerate(messages):
        for chunk in _text_chunks(message):
            chunk_counts[message_index] += 1
            batch.append((message_index, chunk, _utf8_byte_length(chunk)))
            if len(batch) == EMBEDDING_BATCH_SIZE:
                embed_batch(batch)
                batch = []
    if batch:
        embed_batch(batch)

    results: list[tuple[list[float], int, int, str]] = []
    for message_index, chunk_count in enumerate(chunk_counts):
        first_vector = first_vectors[message_index]
        weighted_sum = weighted_sums[message_index]
        weight = total_weights[message_index]
        if first_vector is None or weighted_sum is None or weight < 1:
            raise RuntimeError("embedding accumulator is incomplete")
        if chunk_count == 1:
            vector = first_vector
            pooling = "none"
        else:
            pooled = [value / weight for value in weighted_sum]
            norm = math.sqrt(sum(value * value for value in pooled))
            if not math.isfinite(norm) or norm <= 0:
                raise AnalysisError("pooled embedding has an invalid norm")
            vector = [value / norm for value in pooled]
            pooling = "byte_weighted_mean_l2"
        results.append(
            (
                vector,
                chunk_count,
                source_bytes[message_index],
                pooling,
            )
        )
    return results


def _provider_batch_count(messages: list[str]) -> int:
    chunk_count = sum(1 for message in messages for _ in _text_chunks(message))
    return (chunk_count + EMBEDDING_BATCH_SIZE - 1) // EMBEDDING_BATCH_SIZE


def _safe_run_failure(exc: Exception) -> tuple[str, str]:
    if isinstance(exc, AnalysisError):
        message = str(exc).strip()
        return exc.code, (message[:500] if message else exc.__class__.__name__)
    if isinstance(exc, ProviderError):
        message = str(exc).strip()
        if message:
            code = (
                "INDEXING_MODEL_UNAVAILABLE"
                if "model" in message.casefold()
                or "api key" in message.casefold()
                or "provider" in message.casefold()
                else "UNEXPECTED_ERROR"
            )
            return code, message[:500]
    return "UNEXPECTED_ERROR", exc.__class__.__name__


class AnalysisService:
    def __init__(
        self,
        settings: DatabaseSettings | None = None,
        *,
        job_runner: LocalBackgroundJobRunner | None = None,
        provider_service: ProviderService | None = None,
    ) -> None:
        self._settings = settings
        self._audit = AuditService()
        self._job_runner = job_runner or LocalBackgroundJobRunner()
        self._provider_service = provider_service or ProviderService(settings)

    def start_run(
        self,
        project_id: UUID,
        payload: IndexingRunInput,
        *,
        actor_user_id: UUID,
    ) -> IndexingRun:
        parameters = _object(payload.parameters, "parameters")
        if parameters:
            raise AnalysisError(
                "indexing runs no longer accept profile, run mode, or algorithm parameters",
                code="INDEXING_MODEL_UNAVAILABLE",
                status_code=422,
                suggested_action="correct-input",
                field_errors={
                    "parameters": (
                        "indexing runs no longer accept profile, run mode, "
                        "or algorithm parameters"
                    )
                },
            )
        provider = _provider(payload.provider)
        model = _model(payload.model)
        run_id = uuid4()
        with open_database_connection(self._settings) as connection:
            with connection.transaction():
                dataset = connection.execute(
                    """
                    SELECT id, record_count, display_name, deleted_at
                    FROM dataset_versions
                    WHERE id = %s AND project_id = %s
                    """,
                    (payload.dataset_version_id, project_id),
                ).fetchone()
                if dataset is None or dataset["deleted_at"] is not None:
                    raise AnalysisError("dataset version not found")

                self._require_configured_embedding_model(connection, provider, model)
                if provider == "openai" and payload.cloud_use_confirmed is not True:
                    raise AnalysisError(
                        "OpenAI indexing requires explicit cloud confirmation",
                        code="INDEXING_CLOUD_CONFIRMATION_REQUIRED",
                        status_code=422,
                        suggested_action="correct-input",
                        field_errors={
                            "cloud_use_confirmed": "OpenAI cloud confirmation is required"
                        },
                    )

                row = connection.execute(
                    """
                    INSERT INTO analysis_runs (
                        id, project_id, dataset_version_id, status, progress,
                        phase, provider, model, parameters, created_by_user_id
                    )
                    VALUES (%s, %s, %s, 'queued', 0, 'queued', %s, %s, %s, %s)
                    RETURNING id, project_id, dataset_version_id,
                              %s::text AS dataset_display_name,
                              NULL::timestamptz AS dataset_deleted_at,
                              status, progress, phase, provider, model,
                              parameters, error_code, error_message,
                              diagnostics, started_at, completed_at,
                              cancel_requested_at, deleted_at, created_at,
                              updated_at
                    """,
                    (
                        run_id,
                        project_id,
                        payload.dataset_version_id,
                        provider,
                        model,
                        Jsonb(parameters),
                        actor_user_id,
                        dataset["display_name"],
                    ),
                ).fetchone()
                if row is None:
                    raise RuntimeError("indexing run insert returned no row")
                self._audit.record_event(
                    connection,
                    actor_user_id=actor_user_id,
                    action="indexing_run.start",
                    target_type="indexing_run",
                    target_id=run_id,
                    metadata={
                        "project_id": str(project_id),
                        "dataset_version_id": str(payload.dataset_version_id),
                        "provider": provider,
                        "model": model,
                    },
                )
        return _run_from_row(dict(row))

    def enqueue_run(self, run_id: UUID) -> None:
        try:
            self._job_runner.submit(lambda: self.execute_queued_run(run_id))
        except AnalysisQueueFull:
            with open_database_connection(self._settings) as connection:
                with connection.transaction():
                    connection.execute(
                        """
                        UPDATE analysis_runs
                        SET status = 'failed',
                            phase = 'failed',
                            error_code = 'UNEXPECTED_ERROR',
                            error_message = 'AnalysisQueueFull',
                            completed_at = now(), updated_at = now(),
                            diagnostics = %s
                        WHERE id = %s AND status = 'queued' AND deleted_at IS NULL
                        """,
                        (
                            Jsonb({"failure_type": "AnalysisQueueFull"}),
                            run_id,
                        ),
                    )
            raise

    def list_runs(self, project_id: UUID) -> list[IndexingRun]:
        with open_database_connection(self._settings) as connection:
            rows = connection.execute(
                """
                SELECT r.id, r.project_id, r.dataset_version_id,
                       d.display_name AS dataset_display_name,
                       d.deleted_at AS dataset_deleted_at,
                       r.status, r.progress, r.phase, r.provider, r.model,
                       r.parameters, r.error_code, r.error_message, r.diagnostics,
                       r.started_at, r.completed_at, r.cancel_requested_at,
                       r.deleted_at, r.created_at, r.updated_at
                FROM analysis_runs r
                JOIN dataset_versions d
                  ON d.id = r.dataset_version_id AND d.project_id = r.project_id
                WHERE r.project_id = %s AND r.deleted_at IS NULL
                ORDER BY r.created_at DESC
                """,
                (project_id,),
            ).fetchall()
        return [_run_from_row(dict(row)) for row in rows]

    def get_run(self, project_id: UUID, run_id: UUID) -> IndexingRun | None:
        with open_database_connection(self._settings) as connection:
            row = connection.execute(
                """
                SELECT r.id, r.project_id, r.dataset_version_id,
                       d.display_name AS dataset_display_name,
                       d.deleted_at AS dataset_deleted_at,
                       r.status, r.progress, r.phase, r.provider, r.model,
                       r.parameters, r.error_code, r.error_message, r.diagnostics,
                       r.started_at, r.completed_at, r.cancel_requested_at,
                       r.deleted_at, r.created_at, r.updated_at
                FROM analysis_runs r
                JOIN dataset_versions d
                  ON d.id = r.dataset_version_id AND d.project_id = r.project_id
                WHERE r.id = %s AND r.project_id = %s AND r.deleted_at IS NULL
                """,
                (run_id, project_id),
            ).fetchone()
        return _run_from_row(dict(row)) if row is not None else None

    def list_embeddings(self, project_id: UUID, run_id: UUID) -> list[EmbeddingRecord]:
        with open_database_connection(self._settings) as connection:
            rows = connection.execute(
                """
                SELECT id, project_id, analysis_run_id AS indexing_run_id,
                       dataset_version_id, source_object_type, source_object_id,
                       text_variant, model, dimensions, metadata, created_at
                FROM embeddings
                WHERE project_id = %s AND analysis_run_id = %s
                ORDER BY source_object_id ASC, text_variant ASC, created_at ASC
                """,
                (project_id, run_id),
            ).fetchall()
        return [_embedding_from_row(dict(row)) for row in rows]

    def cancel_run(
        self, project_id: UUID, run_id: UUID, *, actor_user_id: UUID
    ) -> IndexingRun:
        with open_database_connection(self._settings) as connection:
            with connection.transaction():
                current = connection.execute(
                    """
                    SELECT status
                    FROM analysis_runs
                    WHERE id = %s AND project_id = %s AND deleted_at IS NULL
                    """,
                    (run_id, project_id),
                ).fetchone()
                if current is None:
                    raise AnalysisError("indexing run not found", status_code=404)
                status_value = str(current["status"])
                if status_value in TERMINAL_INDEXING_STATUSES:
                    raise AnalysisError(
                        "indexing run can no longer be cancelled",
                        code="INDEXING_CANCEL_NOT_AVAILABLE",
                        status_code=409,
                        suggested_action="reload",
                    )
                next_status = "cancelled" if status_value == "queued" else "cancelling"
                row = connection.execute(
                    """
                    UPDATE analysis_runs
                    SET status = %s,
                        phase = %s,
                        cancel_requested_at = COALESCE(cancel_requested_at, now()),
                        completed_at = CASE
                            WHEN %s = 'cancelled' THEN COALESCE(completed_at, now())
                            ELSE completed_at
                        END,
                        updated_at = now()
                    WHERE id = %s AND project_id = %s AND deleted_at IS NULL
                    RETURNING id, project_id, dataset_version_id,
                              NULL::text AS dataset_display_name,
                              NULL::timestamptz AS dataset_deleted_at,
                              status, progress, phase, provider, model,
                              parameters, error_code, error_message,
                              diagnostics, started_at, completed_at,
                              cancel_requested_at, deleted_at, created_at,
                              updated_at
                    """,
                    (
                        next_status,
                        "cancelled" if next_status == "cancelled" else "cancelling",
                        next_status,
                        run_id,
                        project_id,
                    ),
                ).fetchone()
                if row is None:
                    raise RuntimeError("indexing cancel update returned no row")
                self._audit.record_event(
                    connection,
                    actor_user_id=actor_user_id,
                    action="indexing_run.cancel",
                    target_type="indexing_run",
                    target_id=run_id,
                    metadata={"project_id": str(project_id), "status": next_status},
                )
        fresh = self.get_run(project_id, run_id)
        return fresh if fresh is not None else _run_from_row(dict(row))

    def delete_run(
        self, project_id: UUID, run_id: UUID, *, actor_user_id: UUID
    ) -> None:
        with open_database_connection(self._settings) as connection:
            with connection.transaction():
                row = connection.execute(
                    """
                    UPDATE analysis_runs
                    SET deleted_at = now(),
                        deleted_by_user_id = %s,
                        status = CASE
                            WHEN status IN ('queued', 'running', 'cancelling')
                            THEN 'cancelled'
                            ELSE status
                        END,
                        phase = 'deleted',
                        completed_at = CASE
                            WHEN status IN ('queued', 'running', 'cancelling')
                            THEN COALESCE(completed_at, now())
                            ELSE completed_at
                        END,
                        updated_at = now()
                    WHERE id = %s AND project_id = %s AND deleted_at IS NULL
                    RETURNING id
                    """,
                    (actor_user_id, run_id, project_id),
                ).fetchone()
                if row is None:
                    raise AnalysisError("indexing run not found", status_code=404)
                self._audit.record_event(
                    connection,
                    actor_user_id=actor_user_id,
                    action="indexing_run.delete",
                    target_type="indexing_run",
                    target_id=run_id,
                    metadata={"project_id": str(project_id)},
                )

    def execute_queued_run(self, run_id: UUID) -> None:
        with open_database_connection(self._settings) as connection:
            with connection.transaction():
                run_row = connection.execute(
                    """
                    UPDATE analysis_runs
                    SET status = 'running', progress = %s, phase = 'embedding',
                        started_at = now(), updated_at = now()
                    WHERE id = %s AND status = 'queued' AND deleted_at IS NULL
                    RETURNING id, project_id, dataset_version_id, provider, model
                    """,
                    (RUN_START_PROGRESS, run_id),
                ).fetchone()
                if run_row is None:
                    return
        try:
            embeddings_written = 0
            variant_embedding_counts = {"message": 0, "answer": 0}
            chunks_embedded = 0
            chunked_texts = 0
            dimensions: int | None = None
            confirmed_provider_batches = 0
            with open_database_connection(self._settings) as connection:
                with connection.transaction():
                    total_provider_batches = 0
                    with connection.cursor(
                        name=f"indexing_count_{run_id.hex}"
                    ) as count_cursor:
                        count_cursor.execute(
                            """
                            SELECT message, answer
                            FROM message_pairs
                            WHERE project_id = %s AND dataset_version_id = %s
                            ORDER BY ordinal ASC
                            """,
                            (
                                run_row["project_id"],
                                run_row["dataset_version_id"],
                            ),
                        )
                        while count_pairs := count_cursor.fetchmany(
                            EMBEDDING_BATCH_SIZE
                        ):
                            total_provider_batches += _provider_batch_count(
                                [str(pair["message"]) for pair in count_pairs]
                            )
                            total_provider_batches += _provider_batch_count(
                                [str(pair["answer"]) for pair in count_pairs]
                            )
                    if total_provider_batches < 1:
                        raise AnalysisError(
                            "indexing dataset does not contain any support pairs"
                        )

                    def publish_confirmed_provider_batch() -> None:
                        nonlocal confirmed_provider_batches
                        confirmed_provider_batches += 1
                        progress = min(
                            RUN_MAX_WORKING_PROGRESS,
                            RUN_START_PROGRESS
                            + (
                                (RUN_MAX_WORKING_PROGRESS - RUN_START_PROGRESS)
                                * confirmed_provider_batches
                                // total_provider_batches
                            ),
                        )
                        self._publish_run_progress(run_id, progress)

                    with connection.cursor(
                        name=f"indexing_embed_{run_id.hex}"
                    ) as cursor:
                        cursor.execute(
                            """
                            SELECT id, ordinal, message, answer
                            FROM message_pairs
                            WHERE project_id = %s AND dataset_version_id = %s
                            ORDER BY ordinal ASC
                            """,
                            (run_row["project_id"], run_row["dataset_version_id"]),
                        )
                        while pairs := cursor.fetchmany(EMBEDDING_BATCH_SIZE):
                            self._raise_if_cancelled(connection, run_id)
                            by_variant = {
                                "message": _message_embeddings(
                                    self._provider_service,
                                    str(run_row["provider"]),
                                    str(run_row["model"]),
                                    [str(pair["message"]) for pair in pairs],
                                    on_provider_batch_confirmed=(
                                        publish_confirmed_provider_batch
                                    ),
                                ),
                                "answer": _message_embeddings(
                                    self._provider_service,
                                    str(run_row["provider"]),
                                    str(run_row["model"]),
                                    [str(pair["answer"]) for pair in pairs],
                                    on_provider_batch_confirmed=(
                                        publish_confirmed_provider_batch
                                    ),
                                ),
                            }
                            self._raise_if_cancelled(connection, run_id)
                            for text_variant in ("message", "answer"):
                                for pair, embedded in zip(
                                    pairs, by_variant[text_variant], strict=True
                                ):
                                    vector, chunk_count, source_bytes, pooling = (
                                        embedded
                                    )
                                    if dimensions is None:
                                        dimensions = len(vector)
                                    elif len(vector) != dimensions:
                                        raise AnalysisError(
                                            "provider returned inconsistent embedding "
                                            "dimensions"
                                        )
                                    self._insert_embedding(
                                        connection,
                                        project_id=UUID(str(run_row["project_id"])),
                                        run_id=run_id,
                                        dataset_version_id=UUID(
                                            str(run_row["dataset_version_id"])
                                        ),
                                        pair_id=pair["id"],
                                        source_ordinal=pair["ordinal"],
                                        text_variant=text_variant,
                                        provider=str(run_row["provider"]),
                                        model=str(run_row["model"]),
                                        vector=vector,
                                        chunk_count=chunk_count,
                                        source_bytes=source_bytes,
                                        pooling=pooling,
                                    )
                                    embeddings_written += 1
                                    variant_embedding_counts[text_variant] += 1
                                    chunks_embedded += chunk_count
                                    if chunk_count > 1:
                                        chunked_texts += 1
                    connection.execute(
                        """
                        UPDATE analysis_runs
                        SET status = CASE
                                WHEN status = 'cancelling' THEN 'cancelled'
                                ELSE 'completed'
                            END,
                            progress = CASE
                                WHEN status = 'cancelling' THEN progress
                                ELSE 100
                            END,
                            phase = CASE
                                WHEN status = 'cancelling' THEN 'cancelled'
                                ELSE 'completed'
                            END,
                            completed_at = now(), updated_at = now(),
                            diagnostics = diagnostics || %s
                        WHERE id = %s AND status IN ('running', 'cancelling')
                        """,
                        (
                            Jsonb(
                                {
                                    "provider": str(run_row["provider"]),
                                    "model": str(run_row["model"]),
                                    "dimensions": dimensions,
                                    "message_embeddings": variant_embedding_counts[
                                        "message"
                                    ],
                                    "answer_embeddings": variant_embedding_counts[
                                        "answer"
                                    ],
                                    "embeddings_written": embeddings_written,
                                    "chunks_embedded": chunks_embedded,
                                    "chunked_texts": chunked_texts,
                                }
                            ),
                            run_id,
                        ),
                    )
        except IndexingCancelled:
            with open_database_connection(self._settings) as connection:
                with connection.transaction():
                    connection.execute(
                        """
                        UPDATE analysis_runs
                        SET status = 'cancelled',
                            phase = 'cancelled',
                            completed_at = now(),
                            updated_at = now(),
                            diagnostics = diagnostics || %s
                        WHERE id = %s AND status IN ('running', 'cancelling')
                        """,
                        (Jsonb({"cancelled": True}), run_id),
                    )
        except Exception as exc:
            code, message = _safe_run_failure(exc)
            with open_database_connection(self._settings) as connection:
                with connection.transaction():
                    connection.execute(
                        """
                        UPDATE analysis_runs
                        SET status = 'failed',
                            phase = 'failed',
                            error_code = %s,
                            error_message = %s,
                            completed_at = now(),
                            updated_at = now(),
                            diagnostics = %s
                        WHERE id = %s AND deleted_at IS NULL
                        """,
                        (
                            code,
                            message,
                            Jsonb(
                                {
                                    "provider": str(run_row["provider"]),
                                    "model": str(run_row["model"]),
                                    "failure_type": exc.__class__.__name__,
                                }
                            ),
                            run_id,
                        ),
                    )

    def _publish_run_progress(self, run_id: UUID, progress: int) -> None:
        with open_database_connection(self._settings) as connection:
            with connection.transaction():
                connection.execute(
                    """
                    UPDATE analysis_runs
                    SET progress = %s, updated_at = now()
                    WHERE id = %s AND status = 'running' AND progress < %s
                    """,
                    (progress, run_id, progress),
                )

    def _raise_if_cancelled(self, connection: Any, run_id: UUID) -> None:
        row = connection.execute(
            """
            SELECT status
            FROM analysis_runs
            WHERE id = %s
            """,
            (run_id,),
        ).fetchone()
        if row is not None and row["status"] in {"cancelling", "cancelled"}:
            raise IndexingCancelled()

    def _insert_embedding(
        self,
        connection: Any,
        *,
        project_id: UUID,
        run_id: UUID,
        dataset_version_id: UUID,
        pair_id: object,
        source_ordinal: object,
        text_variant: str,
        provider: str,
        model: str,
        vector: list[float],
        chunk_count: int,
        source_bytes: int,
        pooling: str,
    ) -> None:
        connection.execute(
            """
            INSERT INTO embeddings (
                id, project_id, analysis_run_id, dataset_version_id,
                source_object_type, source_object_id, text_variant, model,
                dimensions, embedding, metadata
            )
            VALUES (
                %s, %s, %s, %s, 'message_pair', %s, %s, %s, %s, %s::vector, %s
            )
            """,
            (
                uuid4(),
                project_id,
                run_id,
                dataset_version_id,
                pair_id,
                text_variant,
                model,
                len(vector),
                _vector_literal(vector),
                Jsonb(
                    {
                        "provider": provider,
                        "source_ordinal": source_ordinal,
                        "source_chunk_count": chunk_count,
                        "source_bytes": source_bytes,
                        "pooling": pooling,
                    }
                ),
            ),
        )

    def _require_configured_embedding_model(
        self, connection: Any, provider: str, model: str
    ) -> None:
        row = connection.execute(
            """
            SELECT manual_models, api_key_secret, endpoint_url
            FROM provider_configurations
            WHERE provider = %s
            """,
            (provider,),
        ).fetchone()
        if row is None:
            raise AnalysisError(
                "embedding provider is not configured",
                code="INDEXING_MODEL_UNAVAILABLE",
                status_code=422,
                suggested_action="correct-input",
                field_errors={"provider": "embedding provider is not configured"},
            )
        models = row["manual_models"]
        manual_models = list(models) if isinstance(models, list) else []
        if model not in manual_models:
            raise AnalysisError(
                "selected embedding model is not configured",
                code="INDEXING_MODEL_UNAVAILABLE",
                status_code=422,
                suggested_action="correct-input",
                field_errors={"model": "selected embedding model is not configured"},
            )
        if provider == "openai" and row["api_key_secret"] is None:
            raise AnalysisError(
                "OpenAI API key is not configured",
                code="INDEXING_MODEL_UNAVAILABLE",
                status_code=422,
                suggested_action="correct-input",
                field_errors={"provider": "OpenAI API key is not configured"},
            )
        if provider in {"ollama", "vllm"} and row["endpoint_url"] is None:
            raise AnalysisError(
                f"{provider} endpoint_url is required",
                code="INDEXING_MODEL_UNAVAILABLE",
                status_code=422,
                suggested_action="correct-input",
                field_errors={"provider": f"{provider} endpoint_url is required"},
            )
