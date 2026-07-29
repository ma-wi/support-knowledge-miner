"""Analysis-run orchestration and bounded provider embedding persistence."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass
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

RUN_STATUSES = {"queued", "running", "completed", "failed", "cancelled"}
EMBEDDING_BATCH_SIZE = 64
MAX_EMBEDDING_CHUNK_BYTES = 1024
RUN_START_PROGRESS = 5
RUN_MAX_WORKING_PROGRESS = 95
LOGGER = logging.getLogger(__name__)


class AnalysisError(ValueError):
    """Raised when analysis-run input or state is invalid."""


class AnalysisQueueFull(AnalysisError):
    """Raised when bounded local analysis capacity is exhausted."""


class LocalBackgroundJobRunner:
    """Fixed daemon workers with a bounded local in-memory queue."""

    def __init__(self, *, worker_count: int = 2, queue_capacity: int = 8) -> None:
        if worker_count < 1 or queue_capacity < 1:
            raise ValueError("worker_count and queue_capacity must be positive")
        self._queue: Queue[Callable[[], None]] = Queue(maxsize=queue_capacity)
        self._workers = [
            Thread(
                target=self._work,
                name=f"skm-analysis-worker-{index + 1}",
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
                "local analysis capacity is exhausted; retry later"
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
                    "analysis background task failed unexpectedly: %s",
                    exc.__class__.__name__,
                )
            finally:
                self._queue.task_done()


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


def _safe_run_error(exc: Exception) -> str:
    if isinstance(exc, (AnalysisError, ProviderError)):
        message = str(exc).strip()
        if message:
            return message[:500]
    return exc.__class__.__name__


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
        payload: AnalysisRunInput,
        *,
        actor_user_id: UUID,
    ) -> AnalysisRun:
        parameters = _object(payload.parameters, "parameters")
        if "mode" in parameters:
            raise AnalysisError("parameters.mode is no longer supported")
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
                           thresholds, algorithm_settings, prompt_template,
                           created_at, updated_at
                    FROM analysis_profiles
                    WHERE id = %s AND project_id = %s
                    """,
                    (payload.analysis_profile_id, project_id),
                ).fetchone()
                if profile is None:
                    raise AnalysisError("analysis profile not found")
                if (
                    bool(profile["is_cloud_provider"])
                    and parameters.get("cloud_use_confirmed") is not True
                ):
                    raise AnalysisError(
                        "cloud_use_confirmed must be true for OpenAI analysis runs"
                    )

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
        try:
            self._job_runner.submit(lambda: self.execute_queued_run(run_id))
        except AnalysisQueueFull:
            with open_database_connection(self._settings) as connection:
                with connection.transaction():
                    connection.execute(
                        """
                        UPDATE analysis_runs
                        SET status = 'failed',
                            error_message = 'AnalysisQueueFull',
                            completed_at = now(), updated_at = now(),
                            diagnostics = %s
                        WHERE id = %s AND status = 'queued'
                        """,
                        (
                            Jsonb({"failure_type": "AnalysisQueueFull"}),
                            run_id,
                        ),
                    )
            raise

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
                    SET status = 'running', progress = %s, started_at = now(),
                        updated_at = now()
                    WHERE id = %s AND status = 'queued'
                    RETURNING id, project_id, dataset_version_id,
                              analysis_profile_id, provider, model
                    """,
                    (RUN_START_PROGRESS, run_id),
                ).fetchone()
                if run_row is None:
                    return
        try:
            embeddings_written = 0
            chunks_embedded = 0
            chunked_messages = 0
            dimensions: int | None = None
            confirmed_provider_batches = 0
            with open_database_connection(self._settings) as connection:
                with connection.transaction():
                    total_provider_batches = 0
                    with connection.cursor(
                        name=f"analysis_count_{run_id.hex}"
                    ) as count_cursor:
                        count_cursor.execute(
                            """
                            SELECT message
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
                    if total_provider_batches < 1:
                        raise AnalysisError(
                            "analysis dataset does not contain any messages"
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
                        name=f"analysis_embed_{run_id.hex}"
                    ) as cursor:
                        cursor.execute(
                            """
                            SELECT id, ordinal, message
                            FROM message_pairs
                            WHERE project_id = %s AND dataset_version_id = %s
                            ORDER BY ordinal ASC
                            """,
                            (run_row["project_id"], run_row["dataset_version_id"]),
                        )
                        while pairs := cursor.fetchmany(EMBEDDING_BATCH_SIZE):
                            embedded_messages = _message_embeddings(
                                self._provider_service,
                                str(run_row["provider"]),
                                str(run_row["model"]),
                                [str(pair["message"]) for pair in pairs],
                                on_provider_batch_confirmed=(
                                    publish_confirmed_provider_batch
                                ),
                            )
                            for pair, embedded in zip(
                                pairs, embedded_messages, strict=True
                            ):
                                vector, chunk_count, source_bytes, pooling = embedded
                                if dimensions is None:
                                    dimensions = len(vector)
                                elif len(vector) != dimensions:
                                    raise AnalysisError(
                                        "provider returned inconsistent embedding "
                                        "dimensions"
                                    )
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
                                        'message', %s, %s, %s::vector, %s
                                    )
                                    """,
                                    (
                                        uuid4(),
                                        run_row["project_id"],
                                        run_id,
                                        run_row["dataset_version_id"],
                                        run_row["analysis_profile_id"],
                                        pair["id"],
                                        run_row["model"],
                                        len(vector),
                                        _vector_literal(vector),
                                        Jsonb(
                                            {
                                                "provider": str(run_row["provider"]),
                                                "source_ordinal": pair["ordinal"],
                                                "source_chunk_count": chunk_count,
                                                "source_bytes": source_bytes,
                                                "pooling": pooling,
                                            }
                                        ),
                                    ),
                                )
                                embeddings_written += 1
                                chunks_embedded += chunk_count
                                if chunk_count > 1:
                                    chunked_messages += 1
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
                                    "provider": str(run_row["provider"]),
                                    "model": str(run_row["model"]),
                                    "dimensions": dimensions,
                                    "message_embeddings": embeddings_written,
                                    "embeddings_written": embeddings_written,
                                    "chunks_embedded": chunks_embedded,
                                    "chunked_messages": chunked_messages,
                                }
                            ),
                            run_id,
                        ),
                    )
        except Exception as exc:
            with open_database_connection(self._settings) as connection:
                with connection.transaction():
                    connection.execute(
                        """
                        UPDATE analysis_runs
                        SET status = 'failed',
                            error_message = %s, completed_at = now(),
                            updated_at = now(), diagnostics = %s
                        WHERE id = %s
                        """,
                        (
                            _safe_run_error(exc),
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
            "prompt_template": (
                str(profile["prompt_template"])
                if profile["prompt_template"] is not None
                else None
            ),
            "created_at": _datetime_iso(profile["created_at"], "created_at"),
            "updated_at": _datetime_iso(profile["updated_at"], "updated_at"),
        }
