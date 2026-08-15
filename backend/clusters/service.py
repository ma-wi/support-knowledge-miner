"""Validated clustering over persisted run embeddings and source traceability."""

from __future__ import annotations

import ast
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
import importlib
import json
import logging
import math
import re
from queue import Full, Queue
from random import Random
from threading import Thread
from time import perf_counter
from typing import Any, cast
from uuid import UUID, uuid4

import numpy as np
from pgvector import Vector
from psycopg.types.json import Jsonb
from scipy.sparse.csgraph import connected_components  # type: ignore[import-untyped]
from sklearn import config_context  # type: ignore[import-untyped]
from sklearn.cluster import AgglomerativeClustering, HDBSCAN  # type: ignore[import-untyped]
from sklearn.decomposition import PCA  # type: ignore[import-untyped]
from sklearn.neighbors import kneighbors_graph  # type: ignore[import-untyped]

from backend.audit import AuditService
from backend.config import DatabaseSettings
from backend.db.connection import open_database_connection
from backend.providers import ProviderError, ProviderService

LOGGER = logging.getLogger(__name__)
VALID_STATUSES = {"unreviewed", "in_progress", "reviewed", "rejected", "outlier"}
TERMINAL_CLUSTER_SET_STATUSES = {"completed", "failed", "cancelled"}
SUPPORTED_VECTOR_BASES = {"message", "answer", "combined"}
SUPPORTED_DERIVATION_TYPES = {
    "root",
    "refinement",
    "outlier_exclusion",
    "manual_edit",
}
SUPPORTED_REFINEMENT_MODES = {"common", "per_parent"}
AGGLOMERATIVE_MAX_RECORDS = 10_000
HDBSCAN_MAX_RECORDS = 100_000
MAX_CLUSTER_DIMENSIONS = 8_192
MAX_CLUSTER_WORKING_SET_MIB = 5 * 1024
MAX_CLUSTER_WORKING_SET_BYTES = MAX_CLUSTER_WORKING_SET_MIB * 1024 * 1024
NATIVE_VECTOR_FETCH_BATCH_SIZE = 64
NATIVE_MATRIX_BYTES_PER_VALUE = np.dtype(np.float32).itemsize
ESTIMATOR_MATRIX_BYTES_PER_VALUE = np.dtype(np.float64).itemsize
NATIVE_FETCH_BYTES_PER_VALUE = np.dtype(np.float32).itemsize
HDBSCAN_BYTES_PER_VECTOR_VALUE = (
    NATIVE_MATRIX_BYTES_PER_VALUE + ESTIMATOR_MATRIX_BYTES_PER_VALUE
)
AGGLOMERATIVE_ESTIMATOR_BYTES_PER_VALUE = 2 * ESTIMATOR_MATRIX_BYTES_PER_VALUE
AGGLOMERATIVE_BYTES_PER_VECTOR_VALUE = (
    NATIVE_MATRIX_BYTES_PER_VALUE + AGGLOMERATIVE_ESTIMATOR_BYTES_PER_VALUE
)
HDBSCAN_NEIGHBOR_BYTES_PER_CELL = 16
HDBSCAN_FIXED_BYTES_PER_RECORD = 256
HDBSCAN_N_JOBS = -1
AGGLOMERATIVE_NEIGHBOR_COUNT = 30
AGGLOMERATIVE_NEIGHBOR_WORKING_BYTES = 64 * 1024 * 1024
AGGLOMERATIVE_GRAPH_BYTES_PER_CELL = 256
AGGLOMERATIVE_DISTANCE_BYTES_PER_CELL_VALUE = 3 * NATIVE_MATRIX_BYTES_PER_VALUE
AGGLOMERATIVE_FIXED_BYTES_PER_RECORD = 512
SUPPORTED_ALGORITHMS = {"hdbscan", "agglomerative"}
AGGLOMERATIVE_LINKAGES = {"ward", "complete", "average", "single"}
HDBSCAN_REDUCTION_METHODS = {"none", "pca", "umap"}
HDBSCAN_EXECUTION_BACKENDS = {"auto", "cpu", "cuml"}
HDBSCAN_DEFAULT_REDUCTION_DIMENSIONS = 10
HDBSCAN_MAX_REDUCTION_DIMENSIONS = 512
UMAP_DEFAULT_N_NEIGHBORS = 15
UMAP_MAX_N_NEIGHBORS = 512
CLUSTER_SET_START_PROGRESS = 5
CLUSTER_SET_LOAD_PROGRESS = 25
CLUSTER_SET_REDUCTION_PROGRESS = 40
CLUSTER_SET_CLUSTERING_PROGRESS = 60
CLUSTER_SET_PERSIST_PROGRESS = 75
CLUSTER_SET_SUMMARY_PROGRESS = 85
DEFAULT_CLUSTER_SET_ALGORITHM = {
    "algorithm": "hdbscan",
    "min_cluster_size": 2,
    "reduction_method": "none",
    "execution_backend": "auto",
}
MAX_CLUSTER_SET_NAME_LENGTH = 160
MAX_CLUSTER_ORIGIN_TITLE_LENGTH = 160
MAX_PER_PARENT_REFINEMENT_GROUPS = 100
MAX_SUMMARY_PROMPT_CHARACTERS = 50_000
MAX_SUMMARY_EXAMPLE_FIELD_CHARACTERS = 1_200
MAX_SUMMARY_FIELD_CHARACTERS = 500
MAX_LLM_SUMMARY_CLUSTERS = 500
SUMMARY_RESPONSE_WRAPPER_KEYS = {
    "cluster",
    "cluster_summary",
    "clusters",
    "data",
    "output",
    "result",
    "summary",
    "zusammenfassung",
}
SUMMARY_FIELD_ALIASES = {
    "title": ("title", "titel", "headline", "überschrift", "ueberschrift"),
    "category": (
        "category",
        "kategorie",
        "theme",
        "thema",
        "bereich",
        "themenbereich",
    ),
    "question": (
        "question",
        "frage",
        "summary_question",
        "zusammengefasste_frage",
        "customer_question",
        "kundenfrage",
        "kundenanfrage",
    ),
    "answer": (
        "answer",
        "antwort",
        "summary_answer",
        "zusammengefasste_antwort",
        "support_answer",
        "antwortvorschlag",
    ),
    "rationale": (
        "rationale",
        "begründung",
        "begruendung",
        "reasoning",
        "grund",
    ),
}
SUMMARY_REQUIRED_FIELDS = ("title", "question", "answer")
SUMMARY_PLACEHOLDER_VALUES = {"...", "null", "string", "string|null"}
DEFAULT_CLUSTER_SOURCE_PAGE_SIZE = 50
MAX_CLUSTER_SOURCE_PAGE_SIZE = 50
MAX_CLUSTER_SOURCE_OFFSET = 100_000


class ClusterError(ValueError):
    """Raised when cluster input or state is invalid."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "UNEXPECTED_ERROR",
        status_code: int = 400,
        retryable: bool = False,
        suggested_action: str = "correct-input",
        field_errors: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code
        self.retryable = retryable
        self.suggested_action = suggested_action
        self.field_errors = field_errors or {}


class ClusterSetQueueFull(ClusterError):
    """Raised when local Cluster-Set background capacity is exhausted."""

    def __init__(self, message: str) -> None:
        super().__init__(
            message,
            code="UNEXPECTED_ERROR",
            status_code=503,
            retryable=True,
            suggested_action="retry",
        )


class ClusterSetCancelled(Exception):
    """Internal control-flow exception for cooperative Cluster-Set cancellation."""


class LocalClusterSetJobRunner:
    """Fixed daemon workers with a bounded local Cluster-Set queue."""

    def __init__(self, *, worker_count: int = 2, queue_capacity: int = 8) -> None:
        if worker_count < 1 or queue_capacity < 1:
            raise ValueError("worker_count and queue_capacity must be positive")
        self._queue: Queue[Callable[[], None]] = Queue(maxsize=queue_capacity)
        self._workers = [
            Thread(
                target=self._work,
                name=f"skm-cluster-set-worker-{index + 1}",
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
            raise ClusterSetQueueFull(
                "local Cluster-Set capacity is exhausted; retry later"
            ) from exc

    def _work(self) -> None:
        while True:
            task = self._queue.get()
            try:
                task()
            except Exception as exc:
                LOGGER.error(
                    "Cluster-Set background task failed unexpectedly: %s",
                    exc.__class__.__name__,
                )
            finally:
                self._queue.task_done()


@dataclass(frozen=True)
class AlgorithmConfiguration:
    name: str
    parameters: dict[str, int | float | str | None]

    def as_settings(self) -> dict[str, int | float | str | None]:
        return {"algorithm": self.name, **self.parameters}


@dataclass(frozen=True)
class ClusterSetBasisBudget:
    output_dimensions: int
    message_dimensions: int | None
    answer_dimensions: int | None


@dataclass(frozen=True)
class BatchRefinementGroup:
    cluster_id: UUID
    title: str
    label: int | None
    is_outlier: bool
    pair_ids: list[UUID]


@dataclass(frozen=True)
class ClusterOrigin:
    source_parent_cluster_id: UUID
    source_parent_cluster_title: str
    source_parent_cluster_label: int | None
    source_parent_cluster_is_outlier: bool
    batch_group_index: int
    local_cluster_label: int

    def as_metadata(self) -> dict[str, Any]:
        return {
            "mode": "per_parent",
            "source_parent_cluster_id": str(self.source_parent_cluster_id),
            "source_parent_cluster_title": self.source_parent_cluster_title,
            "source_parent_cluster_label": self.source_parent_cluster_label,
            "source_parent_cluster_is_outlier": self.source_parent_cluster_is_outlier,
            "batch_group_index": self.batch_group_index,
            "local_cluster_label": self.local_cluster_label,
        }


@dataclass(frozen=True)
class ClusterManualUpdate:
    manual_title: str | None = None
    manual_category: str | None = None
    manual_status: str | None = None
    fields_to_update: frozenset[str] = field(default_factory=frozenset)


@dataclass(frozen=True)
class ClusterSetInput:
    indexing_run_id: UUID
    display_name: str | None = None
    parent_cluster_set_id: UUID | None = None
    derivation_type: str = "root"
    vector_basis: str = "message"
    message_weight: float = 0.5
    answer_weight: float = 0.5
    algorithm_settings: dict[str, Any] = field(
        default_factory=lambda: dict(DEFAULT_CLUSTER_SET_ALGORITHM)
    )
    refinement_mode: str = "common"
    source_cluster_ids: list[UUID] = field(default_factory=list)
    source_pair_ids: list[UUID] = field(default_factory=list)
    outlier_threshold: float | None = None
    llm_provider_id: UUID | None = None
    llm_provider: str | None = None
    llm_model: str | None = None
    llm_sample_count: int | None = 10
    llm_sample_all: bool = False
    llm_cloud_use_confirmed: bool = False


@dataclass(frozen=True)
class ClusterSetSummaryInput:
    llm_provider_id: UUID | None = None
    llm_provider: str | None = None
    llm_model: str | None = None
    llm_sample_count: int | None = 10
    llm_sample_all: bool = False
    llm_cloud_use_confirmed: bool = False


@dataclass(frozen=True)
class ClusterSet:
    id: UUID
    project_id: UUID
    indexing_run_id: UUID
    dataset_version_id: UUID
    dataset_display_name: str | None
    indexing_deleted_at: datetime | None
    parent_cluster_set_id: UUID | None
    display_name: str
    status: str
    progress: int
    phase: str
    derivation_type: str
    vector_basis: str
    message_weight: float
    answer_weight: float
    algorithm: str
    parameters: dict[str, Any]
    source_snapshot: dict[str, Any]
    llm_provider: str | None
    llm_provider_configuration_id: UUID | None
    llm_provider_display_name: str | None
    llm_model: str | None
    llm_parameters: dict[str, Any]
    llm_sample_strategy: dict[str, Any]
    error_code: str | None
    error_message: str | None
    diagnostics: dict[str, Any]
    started_at: datetime | None
    completed_at: datetime | None
    cancel_requested_at: datetime | None
    deleted_at: datetime | None
    created_at: datetime
    updated_at: datetime
    cluster_count: int
    active_cluster_count: int = 0
    active_message_pair_count: int = 0


@dataclass(frozen=True)
class ClusterSetEvent:
    id: UUID
    project_id: UUID
    cluster_set_id: UUID
    event_type: str
    metadata: dict[str, Any]
    created_at: datetime


@dataclass(frozen=True)
class Cluster:
    id: UUID
    project_id: UUID
    analysis_run_id: UUID
    dataset_version_id: UUID
    auto_title: str
    manual_title: str | None
    effective_title: str
    auto_category: str | None
    manual_category: str | None
    effective_category: str | None
    auto_status: str
    manual_status: str | None
    effective_status: str
    score: float
    is_outlier: bool
    algorithm: str
    member_count: int
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    cluster_set_id: UUID | None = None
    auto_summary_question: str | None = None
    auto_summary_answer: str | None = None


@dataclass(frozen=True)
class ClusterSource:
    cluster_id: UUID
    message_pair_id: UUID
    ticket_id: str
    message_group_id: str
    message: str
    answer: str
    membership_score: float
    is_outlier: bool
    assignment_type: str


@dataclass(frozen=True)
class ClusterSourcePage:
    sources: list[ClusterSource]
    limit: int
    offset: int
    next_offset: int | None
    has_more: bool


def _clean_optional(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _integer(
    settings: dict[str, Any],
    field: str,
    *,
    default: int | None = None,
    minimum: int = 1,
    maximum: int | None = None,
) -> int | None:
    value = settings.get(field, default)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise _algorithm_settings_error(
            f"{field} must be an integer >= {minimum}", field
        )
    if maximum is not None and value > maximum:
        raise _algorithm_settings_error(
            f"{field} must be an integer <= {maximum}", field
        )
    return value


def _number(
    settings: dict[str, Any],
    field: str,
    *,
    default: float,
    minimum: float,
    maximum: float | None = None,
) -> float:
    value = settings.get(field, default)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise _algorithm_settings_error(f"{field} must be a number >= {minimum}", field)
    result = float(value)
    if not math.isfinite(result) or result < minimum:
        raise _algorithm_settings_error(f"{field} must be a number >= {minimum}", field)
    if maximum is not None and result > maximum:
        raise _algorithm_settings_error(f"{field} must be a number <= {maximum}", field)
    return result


def _choice(
    settings: dict[str, Any],
    field: str,
    *,
    default: str,
    allowed: set[str],
) -> str:
    value = settings.get(field, default)
    if not isinstance(value, str):
        raise _algorithm_settings_error(
            f"{field} must be one of {', '.join(sorted(allowed))}", field
        )
    cleaned = value.strip().lower()
    if cleaned not in allowed:
        raise _algorithm_settings_error(
            f"{field} must be one of {', '.join(sorted(allowed))}", field
        )
    return cleaned


def _algorithm_settings_error(message: str, field: str | None = None) -> ClusterError:
    return ClusterError(
        message,
        code="CLUSTER_ALGORITHM_PARAMETERS_INVALID",
        status_code=422,
        field_errors={field: message} if field is not None else {},
    )


def validate_algorithm_settings(settings: dict[str, Any]) -> AlgorithmConfiguration:
    """Validate and normalize the accepted profile algorithm contract."""
    if not isinstance(settings, dict):
        raise _algorithm_settings_error(
            "algorithm_settings must be an object", "algorithm_settings"
        )
    algorithm = settings.get("algorithm")
    if not isinstance(algorithm, str) or algorithm not in SUPPORTED_ALGORITHMS:
        raise _algorithm_settings_error(
            "algorithm must be hdbscan or agglomerative", "algorithm"
        )

    if algorithm == "hdbscan":
        allowed = {
            "algorithm",
            "min_cluster_size",
            "min_samples",
            "cluster_selection_epsilon",
            "outlier_threshold",
            "reduction_method",
            "reduction_dimensions",
            "umap_n_neighbors",
            "umap_min_dist",
            "execution_backend",
        }
        unknown = set(settings) - allowed
        if unknown:
            field = sorted(unknown)[0]
            raise _algorithm_settings_error(f"unknown hdbscan setting: {field}", field)
        outlier_threshold = _outlier_threshold(settings.get("outlier_threshold"))
        reduction_method = _choice(
            settings,
            "reduction_method",
            default="none",
            allowed=HDBSCAN_REDUCTION_METHODS,
        )
        reduction_dimensions = (
            _integer(
                settings,
                "reduction_dimensions",
                default=HDBSCAN_DEFAULT_REDUCTION_DIMENSIONS,
                minimum=2,
                maximum=HDBSCAN_MAX_REDUCTION_DIMENSIONS,
            )
            if reduction_method != "none"
            else None
        )
        execution_backend = _choice(
            settings,
            "execution_backend",
            default="auto",
            allowed=HDBSCAN_EXECUTION_BACKENDS,
        )
        return AlgorithmConfiguration(
            name=algorithm,
            parameters={
                "min_cluster_size": _integer(
                    settings,
                    "min_cluster_size",
                    default=5,
                    minimum=2,
                    maximum=HDBSCAN_MAX_RECORDS,
                ),
                "min_samples": _integer(
                    settings,
                    "min_samples",
                    maximum=HDBSCAN_MAX_RECORDS,
                ),
                "cluster_selection_epsilon": _number(
                    settings,
                    "cluster_selection_epsilon",
                    default=0.0,
                    minimum=0.0,
                ),
                "outlier_threshold": outlier_threshold,
                "reduction_method": reduction_method,
                "reduction_dimensions": reduction_dimensions,
                "umap_n_neighbors": (
                    _integer(
                        settings,
                        "umap_n_neighbors",
                        default=UMAP_DEFAULT_N_NEIGHBORS,
                        minimum=2,
                        maximum=UMAP_MAX_N_NEIGHBORS,
                    )
                    if reduction_method == "umap"
                    else None
                ),
                "umap_min_dist": (
                    _number(
                        settings,
                        "umap_min_dist",
                        default=0.0,
                        minimum=0.0,
                        maximum=0.99,
                    )
                    if reduction_method == "umap"
                    else None
                ),
                "execution_backend": execution_backend,
            },
        )

    allowed = {
        "algorithm",
        "n_clusters",
        "distance_threshold",
        "linkage",
        "outlier_threshold",
    }
    unknown = set(settings) - allowed
    if unknown:
        field = sorted(unknown)[0]
        raise _algorithm_settings_error(
            f"unknown agglomerative setting: {field}", field
        )
    outlier_threshold = _outlier_threshold(settings.get("outlier_threshold"))
    active_settings = {
        key: value
        for key, value in settings.items()
        if key not in {"n_clusters", "distance_threshold"} or value is not None
    }
    has_n_clusters = active_settings.get("n_clusters") is not None
    has_distance_threshold = active_settings.get("distance_threshold") is not None
    if has_n_clusters == has_distance_threshold:
        raise _algorithm_settings_error(
            "agglomerative requires exactly one of n_clusters or distance_threshold",
            "n_clusters",
        )
    n_clusters = _integer(active_settings, "n_clusters", default=None, minimum=1)
    distance_threshold_value = active_settings.get("distance_threshold")
    distance_threshold: float | None = None
    if distance_threshold_value is not None:
        distance_threshold = _number(
            active_settings, "distance_threshold", default=0.0, minimum=0.0
        )
        n_clusters = None
    linkage = active_settings.get("linkage", "ward")
    if not isinstance(linkage, str) or linkage not in AGGLOMERATIVE_LINKAGES:
        raise _algorithm_settings_error(
            "linkage must be ward, complete, average, or single", "linkage"
        )
    return AlgorithmConfiguration(
        name=algorithm,
        parameters={
            "n_clusters": n_clusters,
            "distance_threshold": distance_threshold,
            "linkage": linkage,
            "outlier_threshold": outlier_threshold,
        },
    )


def validate_cluster_input_budget(
    config: AlgorithmConfiguration,
    *,
    record_count: int,
    embedding_count: int,
    minimum_dimensions: int | None,
    maximum_dimensions: int | None,
) -> int:
    """Validate completeness and a conservative total estimator working set."""
    if record_count < 1:
        raise ClusterError("analysis run has no message embeddings")
    if embedding_count != record_count:
        raise ClusterError("analysis run has missing message embeddings")
    if (
        minimum_dimensions is None
        or maximum_dimensions is None
        or minimum_dimensions != maximum_dimensions
    ):
        raise ClusterError("analysis run has inconsistent embedding dimensions")
    dimensions = minimum_dimensions
    if dimensions < 1 or dimensions > MAX_CLUSTER_DIMENSIONS:
        raise ClusterError("embedding dimensionality is outside safe limits")
    if config.name == "agglomerative" and record_count > AGGLOMERATIVE_MAX_RECORDS:
        raise ClusterError(
            "agglomerative supports at most 10000 records; select hdbscan"
        )
    if config.name == "hdbscan" and record_count > HDBSCAN_MAX_RECORDS:
        raise ClusterError("hdbscan supports at most 100000 records")
    if config.name == "hdbscan":
        reduction_dimensions = config.parameters.get("reduction_dimensions")
        estimator_dimensions = (
            min(cast(int, reduction_dimensions), dimensions, max(record_count - 1, 1))
            if isinstance(reduction_dimensions, int)
            else dimensions
        )
        estimated_bytes = record_count * dimensions * NATIVE_MATRIX_BYTES_PER_VALUE
        estimated_bytes += (
            record_count * estimator_dimensions * ESTIMATOR_MATRIX_BYTES_PER_VALUE
        )
    else:
        estimated_bytes = (
            record_count * dimensions * AGGLOMERATIVE_BYTES_PER_VECTOR_VALUE
        )
    estimated_bytes += (
        min(record_count, NATIVE_VECTOR_FETCH_BATCH_SIZE)
        * dimensions
        * NATIVE_FETCH_BYTES_PER_VALUE
    )
    if config.name == "hdbscan":
        min_samples = config.parameters["min_samples"]
        effective_neighbor_count = (
            cast(int, config.parameters["min_cluster_size"])
            if min_samples is None
            else cast(int, min_samples)
        )
        if effective_neighbor_count > record_count:
            raise ClusterError(
                "effective HDBSCAN min_samples cannot exceed the number of records"
            )
        estimated_bytes += (
            record_count * effective_neighbor_count * HDBSCAN_NEIGHBOR_BYTES_PER_CELL
        )
        estimated_bytes += record_count * HDBSCAN_FIXED_BYTES_PER_RECORD
    else:
        estimated_bytes += AGGLOMERATIVE_NEIGHBOR_WORKING_BYTES
        neighbor_count = min(
            AGGLOMERATIVE_NEIGHBOR_COUNT,
            max(record_count - 1, 0),
        )
        directed_neighbor_cells = record_count * neighbor_count
        symmetric_neighbor_cells = min(
            2 * directed_neighbor_cells,
            record_count * max(record_count - 1, 0),
        )
        estimated_bytes += symmetric_neighbor_cells * AGGLOMERATIVE_GRAPH_BYTES_PER_CELL
        if config.parameters["linkage"] != "ward":
            estimated_bytes += (
                symmetric_neighbor_cells
                * dimensions
                * AGGLOMERATIVE_DISTANCE_BYTES_PER_CELL_VALUE
            )
        estimated_bytes += record_count * AGGLOMERATIVE_FIXED_BYTES_PER_RECORD
    if estimated_bytes > MAX_CLUSTER_WORKING_SET_BYTES:
        recommendation = (
            "reduce the dataset size, embedding dimensions, or HDBSCAN min_samples"
            if config.name == "hdbscan"
            else "reduce the dataset size or embedding dimensions, or select HDBSCAN"
        )
        raise ClusterError(
            "clustering working set estimate "
            f"{estimated_bytes} bytes for {record_count} records with "
            f"{dimensions} dimensions exceeds the "
            f"{MAX_CLUSTER_WORKING_SET_BYTES}-byte (5 GiB) limit; "
            f"{recommendation}"
        )
    return dimensions


def _cluster_from_row(row: dict[str, object]) -> Cluster:
    metadata = row["metadata"]
    manual_title = row["manual_title"]
    manual_category = row["manual_category"]
    manual_status = row["manual_status"]
    auto_category = row["auto_category"]
    cluster_set_id = row.get("cluster_set_id")
    auto_summary_question = row.get("auto_summary_question")
    auto_summary_answer = row.get("auto_summary_answer")
    return Cluster(
        id=UUID(str(row["id"])),
        project_id=UUID(str(row["project_id"])),
        analysis_run_id=UUID(str(row["analysis_run_id"])),
        dataset_version_id=UUID(str(row["dataset_version_id"])),
        auto_title=str(row["auto_title"]),
        manual_title=str(manual_title) if manual_title is not None else None,
        effective_title=(
            str(manual_title) if manual_title is not None else str(row["auto_title"])
        ),
        auto_category=str(auto_category) if auto_category is not None else None,
        manual_category=str(manual_category) if manual_category is not None else None,
        effective_category=(
            str(manual_category)
            if manual_category is not None
            else (str(auto_category) if auto_category is not None else None)
        ),
        auto_status=str(row["auto_status"]),
        manual_status=str(manual_status) if manual_status is not None else None,
        effective_status=(
            str(manual_status) if manual_status is not None else str(row["auto_status"])
        ),
        score=float(str(row["score"])),
        is_outlier=bool(row["is_outlier"]),
        algorithm=str(row["algorithm"]),
        member_count=int(str(row["member_count"])),
        metadata=dict(metadata) if isinstance(metadata, dict) else {},
        created_at=row["created_at"],  # type: ignore[arg-type]
        updated_at=row["updated_at"],  # type: ignore[arg-type]
        cluster_set_id=(
            UUID(str(cluster_set_id)) if cluster_set_id is not None else None
        ),
        auto_summary_question=(
            str(auto_summary_question) if auto_summary_question is not None else None
        ),
        auto_summary_answer=(
            str(auto_summary_answer) if auto_summary_answer is not None else None
        ),
    )


def _source_from_row(row: dict[str, object]) -> ClusterSource:
    return ClusterSource(
        cluster_id=UUID(str(row["cluster_id"])),
        message_pair_id=UUID(str(row["message_pair_id"])),
        ticket_id=str(row["ticket_id"]),
        message_group_id=str(row["message_group_id"]),
        message=str(row["message"]),
        answer=str(row["answer"]),
        membership_score=float(str(row["membership_score"])),
        is_outlier=bool(row["is_outlier"]),
        assignment_type=str(row["assignment_type"]),
    )


def _cluster_set_from_row(row: dict[str, object]) -> ClusterSet:
    parameters = row["parameters"]
    source_snapshot = row["source_snapshot"]
    llm_parameters = row["llm_parameters"]
    llm_sample_strategy = row["llm_sample_strategy"]
    diagnostics = row["diagnostics"]
    parent_id = row["parent_cluster_set_id"]
    llm_provider = row["llm_provider"]
    llm_model = row["llm_model"]
    dataset_display_name = row["dataset_display_name"]
    return ClusterSet(
        id=UUID(str(row["id"])),
        project_id=UUID(str(row["project_id"])),
        indexing_run_id=UUID(str(row["indexing_run_id"])),
        dataset_version_id=UUID(str(row["dataset_version_id"])),
        dataset_display_name=(
            str(dataset_display_name) if dataset_display_name is not None else None
        ),
        indexing_deleted_at=row["indexing_deleted_at"],  # type: ignore[arg-type]
        parent_cluster_set_id=UUID(str(parent_id)) if parent_id is not None else None,
        display_name=str(row["display_name"]),
        status=str(row["status"]),
        progress=int(str(row["progress"])),
        phase=str(row["phase"]),
        derivation_type=str(row["derivation_type"]),
        vector_basis=str(row["vector_basis"]),
        message_weight=float(str(row["message_weight"])),
        answer_weight=float(str(row["answer_weight"])),
        algorithm=str(row["algorithm"]),
        parameters=dict(parameters) if isinstance(parameters, dict) else {},
        source_snapshot=(
            dict(source_snapshot) if isinstance(source_snapshot, dict) else {}
        ),
        llm_provider=str(llm_provider) if llm_provider is not None else None,
        llm_provider_configuration_id=(
            UUID(str(row["llm_provider_configuration_id"]))
            if row.get("llm_provider_configuration_id") is not None
            else None
        ),
        llm_provider_display_name=(
            str(row["llm_provider_display_name"])
            if row.get("llm_provider_display_name") is not None
            else None
        ),
        llm_model=str(llm_model) if llm_model is not None else None,
        llm_parameters=(
            dict(llm_parameters) if isinstance(llm_parameters, dict) else {}
        ),
        llm_sample_strategy=(
            dict(llm_sample_strategy) if isinstance(llm_sample_strategy, dict) else {}
        ),
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
        cluster_count=int(str(row.get("cluster_count", 0))),
        active_cluster_count=int(str(row.get("active_cluster_count", 0))),
        active_message_pair_count=int(str(row.get("active_message_pair_count", 0))),
    )


def _cluster_set_event_from_row(row: dict[str, object]) -> ClusterSetEvent:
    metadata = row["metadata"]
    return ClusterSetEvent(
        id=UUID(str(row["id"])),
        project_id=UUID(str(row["project_id"])),
        cluster_set_id=UUID(str(row["cluster_set_id"])),
        event_type=str(row["event_type"]),
        metadata=dict(metadata) if isinstance(metadata, dict) else {},
        created_at=row["created_at"],  # type: ignore[arg-type]
    )


def _display_name(value: str | None, *, fallback: str) -> str:
    cleaned = _clean_optional(value)
    if cleaned is None:
        return fallback
    if len(cleaned) > MAX_CLUSTER_SET_NAME_LENGTH:
        raise ClusterError(
            "display_name is too long",
            code="UNEXPECTED_ERROR",
            status_code=422,
            field_errors={"display_name": "display_name is too long"},
        )
    return cleaned


def _duplicate_display_name(value: object) -> str:
    base_name = str(value).strip() or "Cluster-Set"
    suffix = " (Kopie)"
    return f"{base_name[: MAX_CLUSTER_SET_NAME_LENGTH - len(suffix)]}{suffix}"


def _derivation_type(value: str) -> str:
    cleaned = value.strip().lower()
    if cleaned not in SUPPORTED_DERIVATION_TYPES:
        raise ClusterError(
            "derivation_type is invalid",
            code="CLUSTER_REFINEMENT_EMPTY_SOURCE",
            status_code=422,
            field_errors={"derivation_type": "derivation_type is invalid"},
        )
    return cleaned


def _refinement_mode(value: str) -> str:
    cleaned = value.strip().lower().replace("-", "_")
    if cleaned not in SUPPORTED_REFINEMENT_MODES:
        raise ClusterError(
            "refinement_mode is invalid",
            code="CLUSTER_ALGORITHM_PARAMETERS_INVALID",
            status_code=422,
            field_errors={"refinement_mode": "refinement_mode is invalid"},
        )
    return cleaned


def _vector_basis(value: str) -> str:
    cleaned = value.strip().lower()
    if cleaned not in SUPPORTED_VECTOR_BASES:
        raise ClusterError(
            "vector_basis must be message, answer, or combined",
            code="CLUSTER_VECTOR_BASIS_UNAVAILABLE",
            status_code=422,
            field_errors={
                "vector_basis": "vector_basis must be message, answer, or combined"
            },
        )
    return cleaned


def _weight(value: float, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ClusterError(
            f"{field} must be a non-negative number",
            code="CLUSTER_VECTOR_BASIS_UNAVAILABLE",
            status_code=422,
            field_errors={field: f"{field} must be a non-negative number"},
        )
    result = float(value)
    if not math.isfinite(result) or result < 0:
        raise ClusterError(
            f"{field} must be a non-negative number",
            code="CLUSTER_VECTOR_BASIS_UNAVAILABLE",
            status_code=422,
            field_errors={field: f"{field} must be a non-negative number"},
        )
    return result


def _outlier_threshold(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ClusterError(
            "outlier_threshold must be between 0 and 1",
            code="CLUSTER_OUTLIER_EMPTY_RESULT",
            status_code=422,
            field_errors={
                "outlier_threshold": "outlier_threshold must be between 0 and 1"
            },
        )
    result = float(value)
    if not math.isfinite(result) or result < 0 or result > 1:
        raise ClusterError(
            "outlier_threshold must be between 0 and 1",
            code="CLUSTER_OUTLIER_EMPTY_RESULT",
            status_code=422,
            field_errors={
                "outlier_threshold": "outlier_threshold must be between 0 and 1"
            },
        )
    return result


def _apply_outlier_threshold(
    labels: list[int], probabilities: list[float], threshold: float | None
) -> list[int]:
    if threshold is None:
        return labels
    adjusted = [
        label if label == -1 or probability >= threshold else -1
        for label, probability in zip(labels, probabilities, strict=True)
    ]
    if all(label == -1 for label in adjusted):
        raise ClusterError(
            "outlier threshold removes all records",
            code="CLUSTER_OUTLIER_EMPTY_RESULT",
            status_code=422,
            field_errors={"outlier_threshold": "outlier threshold removes all records"},
        )
    return adjusted


def _validate_summary_call_budget(cluster_count: int) -> None:
    if cluster_count > MAX_LLM_SUMMARY_CLUSTERS:
        raise ClusterError(
            "Cluster summary call budget exceeded",
            code="CLUSTER_BUDGET_EXCEEDED",
            status_code=422,
            field_errors={
                "llm_sample_count": (
                    "summary generation supports at most "
                    f"{MAX_LLM_SUMMARY_CLUSTERS} clusters per job"
                )
            },
        )


def _llm_provider(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip().lower()
    if cleaned not in {"openai", "ollama"}:
        raise ClusterError(
            "LLM provider must be openai or ollama",
            code="LLM_PROVIDER_UNAVAILABLE",
            status_code=422,
            field_errors={"llm_provider": "LLM provider must be openai or ollama"},
        )
    return cleaned


def _llm_model(value: str | None) -> str | None:
    cleaned = _clean_optional(value)
    if cleaned is not None and len(cleaned) > 160:
        raise ClusterError(
            "LLM model is too long",
            code="LLM_PROVIDER_UNAVAILABLE",
            status_code=422,
            field_errors={"llm_model": "LLM model is too long"},
        )
    return cleaned


def _summary_sample_strategy(payload: ClusterSetInput) -> dict[str, Any]:
    if payload.llm_sample_all:
        return {"strategy": "random", "requested": "all", "seed": uuid4().int >> 64}
    count = payload.llm_sample_count if payload.llm_sample_count is not None else 10
    if isinstance(count, bool) or not isinstance(count, int) or count < 1:
        raise ClusterError(
            "summary sample count is invalid",
            code="CLUSTER_SUMMARY_SAMPLE_COUNT_INVALID",
            status_code=422,
            field_errors={
                "llm_sample_count": ("llm_sample_count must be a positive integer")
            },
        )
    return {"strategy": "random", "requested": count, "seed": uuid4().int >> 64}


def _json_object(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _safe_cluster_failure(exc: Exception) -> tuple[str, str, bool]:
    if isinstance(exc, ClusterError):
        return exc.code, str(exc)[:500], exc.retryable
    if isinstance(exc, ProviderError):
        message = str(exc).strip() or "LLM provider is unavailable"
        return "LLM_PROVIDER_UNAVAILABLE", message[:500], True
    return "UNEXPECTED_ERROR", exc.__class__.__name__, False


class ClusterService:
    def __init__(
        self,
        settings: DatabaseSettings | None = None,
        *,
        job_runner: LocalClusterSetJobRunner | None = None,
        provider_service: ProviderService | None = None,
    ) -> None:
        self._settings = settings
        self._audit = AuditService()
        self._job_runner = job_runner or LocalClusterSetJobRunner()
        self._provider_service = provider_service or ProviderService(settings)

    def start_cluster_set(
        self,
        project_id: UUID,
        payload: ClusterSetInput,
        *,
        actor_user_id: UUID,
    ) -> ClusterSet:
        vector_basis = _vector_basis(payload.vector_basis)
        if vector_basis == "message":
            message_weight = 1.0
            answer_weight = 0.0
        elif vector_basis == "answer":
            message_weight = 0.0
            answer_weight = 1.0
        else:
            message_weight = _weight(payload.message_weight, "message_weight")
            answer_weight = _weight(payload.answer_weight, "answer_weight")
            if message_weight + answer_weight <= 0:
                raise ClusterError(
                    "combined vector weights must not both be zero",
                    code="CLUSTER_VECTOR_BASIS_UNAVAILABLE",
                    status_code=422,
                    field_errors={
                        "message_weight": "combined vector weights must not both be zero",
                        "answer_weight": "combined vector weights must not both be zero",
                    },
                )
        derivation_type = _derivation_type(payload.derivation_type)
        refinement_mode = _refinement_mode(payload.refinement_mode)
        if derivation_type != "refinement" and refinement_mode != "common":
            raise ClusterError(
                "per-parent refinement requires a refinement Cluster-Set",
                code="CLUSTER_ALGORITHM_PARAMETERS_INVALID",
                status_code=422,
                field_errors={
                    "refinement_mode": (
                        "per-parent refinement requires a refinement Cluster-Set"
                    )
                },
            )
        algorithm_settings = dict(
            payload.algorithm_settings or DEFAULT_CLUSTER_SET_ALGORITHM
        )
        if payload.outlier_threshold is not None:
            algorithm_settings["outlier_threshold"] = payload.outlier_threshold
        config = validate_algorithm_settings(algorithm_settings)
        llm_model = _llm_model(payload.llm_model)
        legacy_llm_provider = _llm_provider(payload.llm_provider)
        llm_enabled = (
            payload.llm_provider_id is not None
            or legacy_llm_provider is not None
            or llm_model is not None
        )
        if llm_enabled and (
            llm_model is None
            or (payload.llm_provider_id is None and legacy_llm_provider is None)
        ):
            raise ClusterError(
                "LLM provider and model must be set together",
                code="LLM_PROVIDER_UNAVAILABLE",
                status_code=422,
                field_errors={
                    "llm_provider": "LLM provider and model must be set together",
                    "llm_model": "LLM provider and model must be set together",
                },
            )
        llm_provider: str | None = None
        llm_provider_configuration_id: UUID | None = None
        llm_provider_display_name: str | None = None
        if llm_enabled and llm_model is not None:
            try:
                provider_config = self._provider_service.ensure_text_generation_model(
                    payload.llm_provider_id
                    if payload.llm_provider_id is not None
                    else str(legacy_llm_provider),
                    llm_model,
                )
            except ProviderError as exc:
                provider_message = str(exc).strip() or "LLM provider is unavailable"
                raise ClusterError(
                    provider_message,
                    code="LLM_PROVIDER_UNAVAILABLE",
                    status_code=503,
                    retryable=True,
                    field_errors={"llm_provider": provider_message[:500]},
                ) from exc
            llm_provider = provider_config.provider
            llm_provider_configuration_id = provider_config.id
            llm_provider_display_name = provider_config.display_name
            if llm_provider == "openai" and payload.llm_cloud_use_confirmed is not True:
                raise ClusterError(
                    "OpenAI LLM summaries require explicit cloud confirmation",
                    code="LLM_CLOUD_CONFIRMATION_REQUIRED",
                    status_code=422,
                    field_errors={
                        "llm_cloud_use_confirmed": (
                            "OpenAI cloud confirmation is required"
                        )
                    },
                )
        llm_sample_strategy = _summary_sample_strategy(payload) if llm_enabled else {}
        source_cluster_ids = list(dict.fromkeys(payload.source_cluster_ids))
        source_pair_ids = list(dict.fromkeys(payload.source_pair_ids))
        if (
            refinement_mode == "per_parent"
            and len(source_cluster_ids) > MAX_PER_PARENT_REFINEMENT_GROUPS
        ):
            raise ClusterError(
                "per-parent refinement selects too many parent clusters",
                code="CLUSTER_BATCH_REFINEMENT_EMPTY_GROUP",
                status_code=422,
                retryable=True,
                suggested_action="select-sources",
                field_errors={
                    "source_cluster_ids": (
                        "per-parent refinement selects too many parent clusters"
                    )
                },
            )
        cluster_set_id = uuid4()
        with open_database_connection(self._settings) as connection:
            with connection.transaction():
                run = connection.execute(
                    """
                    SELECT r.id, r.project_id, r.dataset_version_id, r.status,
                           r.deleted_at AS indexing_deleted_at,
                           d.display_name AS dataset_display_name,
                           d.deleted_at AS dataset_deleted_at
                    FROM analysis_runs r
                    JOIN dataset_versions d
                      ON d.id = r.dataset_version_id AND d.project_id = r.project_id
                    WHERE r.id = %s AND r.project_id = %s
                    """,
                    (payload.indexing_run_id, project_id),
                ).fetchone()
                if run is None or run["indexing_deleted_at"] is not None:
                    raise ClusterError(
                        "indexing run not found",
                        code="CLUSTER_SET_NOT_FOUND",
                        status_code=404,
                    )
                if run["status"] != "completed":
                    raise ClusterError(
                        "indexing run must be completed before clustering",
                        code="INDEXING_NOT_COMPLETE",
                        status_code=422,
                        field_errors={
                            "indexing_run_id": (
                                "indexing run must be completed before clustering"
                            )
                        },
                    )
                parent_id = payload.parent_cluster_set_id
                if parent_id is not None:
                    parent = connection.execute(
                        """
                        SELECT id, indexing_run_id, status
                        FROM cluster_sets
                        WHERE id = %s AND project_id = %s AND deleted_at IS NULL
                        """,
                        (parent_id, project_id),
                    ).fetchone()
                    if parent is None:
                        raise ClusterError(
                            "parent Cluster-Set not found",
                            code="CLUSTER_SET_NOT_FOUND",
                            status_code=404,
                        )
                    if parent["status"] != "completed":
                        raise ClusterError(
                            "parent Cluster-Set is not completed",
                            code="CLUSTER_SET_NOT_COMPLETE",
                            status_code=409,
                            retryable=True,
                            suggested_action="wait",
                            field_errors={
                                "parent_cluster_set_id": (
                                    "parent Cluster-Set must be completed"
                                )
                            },
                        )
                    if UUID(str(parent["indexing_run_id"])) != payload.indexing_run_id:
                        raise ClusterError(
                            "parent Cluster-Set must use the selected indexing run",
                            code="CLUSTER_REFINEMENT_EMPTY_SOURCE",
                            status_code=422,
                            field_errors={
                                "parent_cluster_set_id": (
                                    "parent Cluster-Set must use the selected indexing run"
                                )
                            },
                        )
                    if derivation_type == "root":
                        raise ClusterError(
                            "parent Cluster-Set requires a refinement derivation type",
                            code="CLUSTER_REFINEMENT_EMPTY_SOURCE",
                            status_code=422,
                            field_errors={
                                "derivation_type": (
                                    "parent Cluster-Set requires a refinement derivation type"
                                )
                            },
                        )
                    if not source_cluster_ids and not source_pair_ids:
                        raise ClusterError(
                            "refinement requires at least one source selection",
                            code="CLUSTER_REFINEMENT_EMPTY_SOURCE",
                            status_code=422,
                            field_errors={
                                "source_cluster_ids": (
                                    "refinement requires at least one source selection"
                                ),
                                "source_pair_ids": (
                                    "refinement requires at least one source selection"
                                ),
                            },
                        )
                elif derivation_type != "root":
                    raise ClusterError(
                        "refinement requires a parent Cluster-Set",
                        code="CLUSTER_REFINEMENT_EMPTY_SOURCE",
                        status_code=422,
                        field_errors={
                            "parent_cluster_set_id": (
                                "refinement requires a parent Cluster-Set"
                            )
                        },
                    )

                selected_pair_ids = self._resolve_source_pair_ids(
                    connection,
                    project_id=project_id,
                    dataset_version_id=UUID(str(run["dataset_version_id"])),
                    parent_cluster_set_id=parent_id,
                    source_cluster_ids=source_cluster_ids,
                    source_pair_ids=source_pair_ids,
                )
                source_snapshot = self._source_snapshot(
                    connection,
                    project_id=project_id,
                    dataset_version_id=UUID(str(run["dataset_version_id"])),
                    parent_cluster_set_id=parent_id,
                    source_cluster_ids=source_cluster_ids,
                    selected_pair_ids=selected_pair_ids,
                    refinement_mode=refinement_mode,
                )
                display_name = _display_name(
                    payload.display_name, fallback="Cluster-Set"
                )
                row = connection.execute(
                    """
                    INSERT INTO cluster_sets (
                        id, project_id, indexing_run_id, dataset_version_id,
                        parent_cluster_set_id, display_name, derivation_type,
                        vector_basis, message_weight, answer_weight,
                        algorithm, parameters, source_snapshot,
                        llm_provider, llm_provider_configuration_id,
                        llm_provider_display_name, llm_model, llm_parameters,
                        llm_sample_strategy, created_by_user_id
                    )
                    VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s
                    )
                    RETURNING id, project_id, indexing_run_id, dataset_version_id,
                              %s::text AS dataset_display_name,
                              %s::timestamptz AS indexing_deleted_at,
                              parent_cluster_set_id, display_name, status,
                              progress, phase, derivation_type, vector_basis,
                              message_weight, answer_weight, algorithm,
                              parameters, source_snapshot, llm_provider,
                              llm_provider_configuration_id,
                              llm_provider_display_name, llm_model, llm_parameters,
                              llm_sample_strategy,
                              error_code, error_message, diagnostics,
                              started_at, completed_at, cancel_requested_at,
                              deleted_at, created_at, updated_at,
                              0::bigint AS cluster_count,
                              0::bigint AS active_cluster_count,
                              0::bigint AS active_message_pair_count
                    """,
                    (
                        cluster_set_id,
                        project_id,
                        payload.indexing_run_id,
                        run["dataset_version_id"],
                        parent_id,
                        display_name,
                        derivation_type,
                        vector_basis,
                        message_weight,
                        answer_weight,
                        config.name,
                        Jsonb(config.parameters),
                        Jsonb(source_snapshot),
                        llm_provider,
                        llm_provider_configuration_id,
                        llm_provider_display_name,
                        llm_model,
                        Jsonb({"enabled": llm_enabled}),
                        Jsonb(llm_sample_strategy),
                        actor_user_id,
                        run["dataset_display_name"],
                        run["indexing_deleted_at"],
                    ),
                ).fetchone()
                if row is None:
                    raise RuntimeError("Cluster-Set insert returned no row")
                self._record_cluster_set_event(
                    connection,
                    project_id=project_id,
                    cluster_set_id=cluster_set_id,
                    actor_user_id=actor_user_id,
                    event_type="created",
                    metadata={
                        "indexing_run_id": str(payload.indexing_run_id),
                        "vector_basis": vector_basis,
                        "algorithm": config.name,
                        "derivation_type": derivation_type,
                        "parent_cluster_set_id": (
                            str(parent_id) if parent_id is not None else None
                        ),
                    },
                )
                self._audit.record_event(
                    connection,
                    actor_user_id=actor_user_id,
                    action="cluster_set.create",
                    target_type="cluster_set",
                    target_id=cluster_set_id,
                    metadata={
                        "project_id": str(project_id),
                        "indexing_run_id": str(payload.indexing_run_id),
                        "llm_provider": llm_provider,
                        "llm_provider_configuration_id": (
                            str(llm_provider_configuration_id)
                            if llm_provider_configuration_id is not None
                            else None
                        ),
                    },
                )
        return _cluster_set_from_row(dict(row))

    def enqueue_cluster_set(self, cluster_set_id: UUID) -> None:
        try:
            self._job_runner.submit(
                lambda: self.execute_queued_cluster_set(cluster_set_id)
            )
        except ClusterSetQueueFull:
            with open_database_connection(self._settings) as connection:
                with connection.transaction():
                    connection.execute(
                        """
                        UPDATE cluster_sets
                        SET status = 'failed',
                            phase = 'failed',
                            error_code = 'UNEXPECTED_ERROR',
                            error_message = 'ClusterSetQueueFull',
                            completed_at = now(), updated_at = now(),
                            diagnostics = diagnostics || %s
                        WHERE id = %s AND status = 'queued' AND deleted_at IS NULL
                        """,
                        (
                            Jsonb({"failure_type": "ClusterSetQueueFull"}),
                            cluster_set_id,
                        ),
                    )
            raise

    def start_cluster_set_summary_regeneration(
        self,
        project_id: UUID,
        cluster_set_id: UUID,
        payload: ClusterSetSummaryInput,
        *,
        actor_user_id: UUID,
    ) -> ClusterSet:
        llm_model = _llm_model(payload.llm_model)
        legacy_llm_provider = _llm_provider(payload.llm_provider)
        if llm_model is None or (
            payload.llm_provider_id is None and legacy_llm_provider is None
        ):
            raise ClusterError(
                "LLM provider and model must be set together",
                code="LLM_PROVIDER_UNAVAILABLE",
                status_code=422,
                field_errors={
                    "llm_provider": "LLM provider and model must be set together",
                    "llm_model": "LLM provider and model must be set together",
                },
            )
        try:
            provider_config = self._provider_service.ensure_text_generation_model(
                payload.llm_provider_id
                if payload.llm_provider_id is not None
                else str(legacy_llm_provider),
                llm_model,
            )
        except ProviderError as exc:
            provider_message = str(exc).strip() or "LLM provider is unavailable"
            raise ClusterError(
                provider_message,
                code="LLM_PROVIDER_UNAVAILABLE",
                status_code=503,
                retryable=True,
                field_errors={"llm_provider": provider_message[:500]},
            ) from exc
        if (
            provider_config.provider == "openai"
            and payload.llm_cloud_use_confirmed is not True
        ):
            raise ClusterError(
                "OpenAI LLM summaries require explicit cloud confirmation",
                code="LLM_CLOUD_CONFIRMATION_REQUIRED",
                status_code=422,
                field_errors={
                    "llm_cloud_use_confirmed": "OpenAI cloud confirmation is required"
                },
            )
        sample_strategy = _summary_sample_strategy(
            ClusterSetInput(
                indexing_run_id=UUID(int=0),
                llm_provider_id=payload.llm_provider_id,
                llm_provider=payload.llm_provider,
                llm_model=payload.llm_model,
                llm_sample_count=payload.llm_sample_count,
                llm_sample_all=payload.llm_sample_all,
            )
        )
        with open_database_connection(self._settings) as connection:
            with connection.transaction():
                current = connection.execute(
                    """
                    SELECT cs.id, cs.status, COUNT(c.id) AS cluster_count
                    FROM cluster_sets cs
                    LEFT JOIN clusters c
                      ON c.cluster_set_id = cs.id AND c.project_id = cs.project_id
                    WHERE cs.id = %s
                      AND cs.project_id = %s
                      AND cs.deleted_at IS NULL
                    GROUP BY cs.id
                    """,
                    (cluster_set_id, project_id),
                ).fetchone()
                if current is None:
                    raise ClusterError(
                        "Cluster-Set not found",
                        code="CLUSTER_SET_NOT_FOUND",
                        status_code=404,
                    )
                if current["status"] != "completed":
                    raise ClusterError(
                        "Cluster-Set is not completed",
                        code="CLUSTER_SET_NOT_COMPLETE",
                        status_code=409,
                        retryable=True,
                        suggested_action="wait",
                    )
                if int(str(current["cluster_count"])) < 1:
                    raise ClusterError(
                        "Cluster-Set contains no clusters",
                        code="CLUSTER_SET_NOT_COMPLETE",
                        status_code=409,
                        retryable=True,
                        suggested_action="wait",
                    )
                updated = connection.execute(
                    """
                    UPDATE cluster_sets
                    SET status = 'queued',
                        progress = %s,
                        phase = 'queued_summary',
                        llm_provider = %s,
                        llm_provider_configuration_id = %s,
                        llm_provider_display_name = %s,
                        llm_model = %s,
                        llm_parameters = %s,
                        llm_sample_strategy = %s,
                        error_code = NULL,
                        error_message = NULL,
                        cancel_requested_at = NULL,
                        updated_at = now(),
                        diagnostics = diagnostics || %s
                    WHERE id = %s
                      AND project_id = %s
                      AND status = 'completed'
                      AND deleted_at IS NULL
                    RETURNING id
                    """,
                    (
                        CLUSTER_SET_SUMMARY_PROGRESS,
                        provider_config.provider,
                        provider_config.id,
                        provider_config.display_name,
                        llm_model,
                        Jsonb({"enabled": True, "regeneration": True}),
                        Jsonb(sample_strategy),
                        Jsonb({"summary_regeneration_queued": True}),
                        cluster_set_id,
                        project_id,
                    ),
                ).fetchone()
                if updated is None:
                    raise ClusterError(
                        "Cluster-Set is not completed",
                        code="CLUSTER_SET_NOT_COMPLETE",
                        status_code=409,
                        retryable=True,
                        suggested_action="wait",
                    )
                self._record_cluster_set_event(
                    connection,
                    project_id=project_id,
                    cluster_set_id=cluster_set_id,
                    actor_user_id=actor_user_id,
                    event_type="summary_regeneration_requested",
                    metadata={
                        "llm_provider": provider_config.provider,
                        "llm_provider_configuration_id": str(provider_config.id),
                        "llm_model": llm_model,
                        "sample_strategy": sample_strategy,
                    },
                )
                self._audit.record_event(
                    connection,
                    actor_user_id=actor_user_id,
                    action="cluster_set.summary_regenerate",
                    target_type="cluster_set",
                    target_id=cluster_set_id,
                    metadata={
                        "project_id": str(project_id),
                        "llm_provider": provider_config.provider,
                        "llm_provider_configuration_id": str(provider_config.id),
                    },
                )
                row = self._fetch_cluster_set_row(
                    connection, project_id, cluster_set_id
                )
        if row is None:
            raise RuntimeError("Cluster-Set disappeared after summary regeneration")
        return _cluster_set_from_row(dict(row))

    def enqueue_cluster_set_summary_regeneration(self, cluster_set_id: UUID) -> None:
        try:
            self._job_runner.submit(
                lambda: self.execute_queued_cluster_set_summary_regeneration(
                    cluster_set_id
                )
            )
        except ClusterSetQueueFull:
            with open_database_connection(self._settings) as connection:
                with connection.transaction():
                    connection.execute(
                        """
                        UPDATE cluster_sets
                        SET status = 'completed',
                            progress = 100,
                            phase = 'completed',
                            error_code = 'CLUSTER_SUMMARY_FAILED',
                            error_message = 'ClusterSetQueueFull',
                            completed_at = COALESCE(completed_at, now()),
                            updated_at = now(),
                            diagnostics = diagnostics || %s
                        WHERE id = %s
                          AND status = 'queued'
                          AND phase = 'queued_summary'
                          AND deleted_at IS NULL
                        """,
                        (
                            Jsonb({"failure_type": "ClusterSetQueueFull"}),
                            cluster_set_id,
                        ),
                    )
            raise

    def list_cluster_sets(self, project_id: UUID) -> list[ClusterSet]:
        with open_database_connection(self._settings) as connection:
            rows = connection.execute(
                """
                SELECT cs.id, cs.project_id, cs.indexing_run_id,
                       cs.dataset_version_id,
                       d.display_name AS dataset_display_name,
                       r.deleted_at AS indexing_deleted_at,
                       cs.parent_cluster_set_id, cs.display_name, cs.status,
                       cs.progress, cs.phase, cs.derivation_type,
                       cs.vector_basis, cs.message_weight, cs.answer_weight,
                       cs.algorithm, cs.parameters, cs.source_snapshot,
                       cs.llm_provider, cs.llm_provider_configuration_id,
                       cs.llm_provider_display_name, cs.llm_model,
                       cs.llm_parameters, cs.llm_sample_strategy,
                       cs.error_code, cs.error_message,
                       cs.diagnostics, cs.started_at, cs.completed_at,
                       cs.cancel_requested_at, cs.deleted_at, cs.created_at,
                       cs.updated_at,
                       COUNT(DISTINCT c.id) AS cluster_count,
                       COUNT(DISTINCT c.id) FILTER (
                           WHERE COALESCE(c.manual_status, c.auto_status) <> 'rejected'
                       ) AS active_cluster_count,
                       COUNT(DISTINCT cm.message_pair_id) FILTER (
                           WHERE COALESCE(c.manual_status, c.auto_status) <> 'rejected'
                       ) AS active_message_pair_count
                FROM cluster_sets cs
                JOIN analysis_runs r
                  ON r.id = cs.indexing_run_id AND r.project_id = cs.project_id
                JOIN dataset_versions d
                  ON d.id = cs.dataset_version_id AND d.project_id = cs.project_id
                LEFT JOIN clusters c
                  ON c.cluster_set_id = cs.id AND c.project_id = cs.project_id
                LEFT JOIN cluster_memberships cm
                  ON cm.cluster_id = c.id
                 AND cm.project_id = c.project_id
                 AND cm.cluster_set_id = c.cluster_set_id
                WHERE cs.project_id = %s
                  AND (
                      cs.deleted_at IS NULL
                      OR EXISTS (
                          SELECT 1
                          FROM cluster_sets child
                          WHERE child.project_id = cs.project_id
                            AND child.parent_cluster_set_id = cs.id
                            AND child.deleted_at IS NULL
                      )
                  )
                GROUP BY cs.id, d.display_name, r.deleted_at
                ORDER BY cs.updated_at DESC, cs.created_at DESC
                """,
                (project_id,),
            ).fetchall()
        return [_cluster_set_from_row(dict(row)) for row in rows]

    def has_active_cluster_set(self) -> bool:
        with open_database_connection(self._settings) as connection:
            row = connection.execute(
                """
                SELECT id
                FROM cluster_sets
                WHERE deleted_at IS NULL
                  AND status IN ('queued', 'running', 'cancelling')
                LIMIT 1
                """
            ).fetchone()
        return row is not None

    def get_cluster_set(
        self, project_id: UUID, cluster_set_id: UUID
    ) -> ClusterSet | None:
        with open_database_connection(self._settings) as connection:
            row = self._fetch_cluster_set_row(connection, project_id, cluster_set_id)
        return _cluster_set_from_row(dict(row)) if row is not None else None

    def rename_cluster_set(
        self,
        project_id: UUID,
        cluster_set_id: UUID,
        display_name: str,
        *,
        actor_user_id: UUID,
    ) -> ClusterSet:
        name = _display_name(display_name, fallback="Cluster-Set")
        with open_database_connection(self._settings) as connection:
            with connection.transaction():
                updated = connection.execute(
                    """
                    UPDATE cluster_sets
                    SET display_name = %s, updated_at = now()
                    WHERE id = %s AND project_id = %s AND deleted_at IS NULL
                    RETURNING id
                    """,
                    (name, cluster_set_id, project_id),
                ).fetchone()
                if updated is None:
                    raise ClusterError(
                        "Cluster-Set not found",
                        code="CLUSTER_SET_NOT_FOUND",
                        status_code=404,
                    )
                self._record_cluster_set_event(
                    connection,
                    project_id=project_id,
                    cluster_set_id=cluster_set_id,
                    actor_user_id=actor_user_id,
                    event_type="renamed",
                    metadata={"display_name": name},
                )
        fresh = self.get_cluster_set(project_id, cluster_set_id)
        if fresh is None:
            raise RuntimeError("Cluster-Set disappeared after rename")
        return fresh

    def duplicate_cluster_set(
        self, project_id: UUID, cluster_set_id: UUID, *, actor_user_id: UUID
    ) -> ClusterSet:
        new_cluster_set_id = uuid4()
        with open_database_connection(self._settings) as connection:
            with connection.transaction():
                source = connection.execute(
                    """
                    SELECT cs.id, cs.indexing_run_id, cs.dataset_version_id,
                           cs.parent_cluster_set_id, cs.display_name,
                           cs.status, cs.progress, cs.phase,
                           cs.derivation_type, cs.vector_basis,
                           cs.message_weight, cs.answer_weight,
                           cs.algorithm, cs.parameters, cs.source_snapshot,
                           cs.llm_provider, cs.llm_provider_configuration_id,
                           cs.llm_provider_display_name, cs.llm_model,
                           cs.llm_parameters, cs.llm_sample_strategy,
                           cs.error_code, cs.error_message, cs.diagnostics,
                           cs.started_at, cs.completed_at, cs.cancel_requested_at,
                           r.status AS indexing_status,
                           r.deleted_at AS indexing_deleted_at,
                           d.deleted_at AS dataset_deleted_at
                    FROM cluster_sets cs
                    JOIN analysis_runs r
                      ON r.id = cs.indexing_run_id
                     AND r.project_id = cs.project_id
                    JOIN dataset_versions d
                      ON d.id = cs.dataset_version_id
                     AND d.project_id = cs.project_id
                    WHERE cs.id = %s
                      AND cs.project_id = %s
                      AND cs.deleted_at IS NULL
                    """,
                    (cluster_set_id, project_id),
                ).fetchone()
                if (
                    source is None
                    or source["status"] != "completed"
                    or source["indexing_status"] != "completed"
                    or source["indexing_deleted_at"] is not None
                    or source["dataset_deleted_at"] is not None
                ):
                    raise ClusterError(
                        "Cluster-Set cannot be duplicated",
                        code="CLUSTER_SET_DUPLICATE_UNAVAILABLE",
                        status_code=409,
                        retryable=True,
                        suggested_action="reload",
                    )
                connection.execute(
                    """
                    INSERT INTO cluster_sets (
                        id, project_id, indexing_run_id, dataset_version_id,
                        parent_cluster_set_id, display_name, status, progress,
                        phase, derivation_type, vector_basis, message_weight,
                        answer_weight, algorithm, parameters, source_snapshot,
                        llm_provider, llm_provider_configuration_id,
                        llm_provider_display_name, llm_model, llm_parameters,
                        llm_sample_strategy, error_code, error_message,
                        diagnostics, started_at, completed_at, cancel_requested_at,
                        created_by_user_id
                    )
                    VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s
                    )
                    """,
                    (
                        new_cluster_set_id,
                        project_id,
                        source["indexing_run_id"],
                        source["dataset_version_id"],
                        source["parent_cluster_set_id"],
                        _duplicate_display_name(source["display_name"]),
                        source["status"],
                        source["progress"],
                        source["phase"],
                        source["derivation_type"],
                        source["vector_basis"],
                        source["message_weight"],
                        source["answer_weight"],
                        source["algorithm"],
                        Jsonb(_json_object(source["parameters"])),
                        Jsonb(_json_object(source["source_snapshot"])),
                        source["llm_provider"],
                        source["llm_provider_configuration_id"],
                        source["llm_provider_display_name"],
                        source["llm_model"],
                        Jsonb(_json_object(source["llm_parameters"])),
                        Jsonb(_json_object(source["llm_sample_strategy"])),
                        source["error_code"],
                        source["error_message"],
                        Jsonb(_json_object(source["diagnostics"])),
                        source["started_at"],
                        source["completed_at"],
                        source["cancel_requested_at"],
                        actor_user_id,
                    ),
                )
                source_clusters = connection.execute(
                    """
                    SELECT id, analysis_run_id, dataset_version_id, auto_title,
                           manual_title, auto_category, manual_category,
                           auto_status, manual_status, score, is_outlier,
                           algorithm, metadata, auto_summary_question,
                           auto_summary_answer
                    FROM clusters
                    WHERE project_id = %s
                      AND cluster_set_id = %s
                    ORDER BY created_at, id
                    """,
                    (project_id, cluster_set_id),
                ).fetchall()
                cluster_id_map: dict[UUID, UUID] = {}
                for cluster_row in source_clusters:
                    source_cluster_id = cast(UUID, cluster_row["id"])
                    new_cluster_id = uuid4()
                    cluster_id_map[source_cluster_id] = new_cluster_id
                    connection.execute(
                        """
                        INSERT INTO clusters (
                            id, project_id, analysis_run_id, dataset_version_id,
                            cluster_set_id, auto_title, manual_title,
                            auto_category, manual_category, auto_status,
                            manual_status, score, is_outlier, algorithm, metadata,
                            auto_summary_question, auto_summary_answer
                        )
                        VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s
                        )
                        """,
                        (
                            new_cluster_id,
                            project_id,
                            cluster_row["analysis_run_id"],
                            cluster_row["dataset_version_id"],
                            new_cluster_set_id,
                            cluster_row["auto_title"],
                            cluster_row["manual_title"],
                            cluster_row["auto_category"],
                            cluster_row["manual_category"],
                            cluster_row["auto_status"],
                            cluster_row["manual_status"],
                            cluster_row["score"],
                            cluster_row["is_outlier"],
                            cluster_row["algorithm"],
                            Jsonb(_json_object(cluster_row["metadata"])),
                            cluster_row["auto_summary_question"],
                            cluster_row["auto_summary_answer"],
                        ),
                    )
                if cluster_id_map:
                    source_memberships = connection.execute(
                        """
                        SELECT id, cluster_id, analysis_run_id, message_pair_id,
                               membership_score, is_outlier, assignment_type,
                               metadata
                        FROM cluster_memberships
                        WHERE project_id = %s
                          AND cluster_set_id = %s
                        ORDER BY created_at, id
                        """,
                        (project_id, cluster_set_id),
                    ).fetchall()
                    for membership_row in source_memberships:
                        source_cluster_id = cast(UUID, membership_row["cluster_id"])
                        membership_new_cluster_id = cluster_id_map.get(
                            source_cluster_id
                        )
                        if membership_new_cluster_id is None:
                            continue
                        connection.execute(
                            """
                            INSERT INTO cluster_memberships (
                                id, project_id, cluster_id, analysis_run_id,
                                message_pair_id, membership_score, is_outlier,
                                assignment_type, cluster_set_id, metadata
                            )
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """,
                            (
                                uuid4(),
                                project_id,
                                membership_new_cluster_id,
                                membership_row["analysis_run_id"],
                                membership_row["message_pair_id"],
                                membership_row["membership_score"],
                                membership_row["is_outlier"],
                                membership_row["assignment_type"],
                                new_cluster_set_id,
                                Jsonb(_json_object(membership_row["metadata"])),
                            ),
                        )
                self._record_cluster_set_event(
                    connection,
                    project_id=project_id,
                    cluster_set_id=new_cluster_set_id,
                    actor_user_id=actor_user_id,
                    event_type="duplicated",
                    metadata={"source_cluster_set_id": str(cluster_set_id)},
                )
                self._audit.record_event(
                    connection,
                    actor_user_id=actor_user_id,
                    action="cluster_set.duplicate",
                    target_type="cluster_set",
                    target_id=new_cluster_set_id,
                    metadata={
                        "project_id": str(project_id),
                        "source_cluster_set_id": str(cluster_set_id),
                    },
                )
                row = self._fetch_cluster_set_row(
                    connection, project_id, new_cluster_set_id
                )
        if row is None:
            raise RuntimeError("Cluster-Set disappeared after duplicate")
        return _cluster_set_from_row(dict(row))

    def cancel_cluster_set(
        self, project_id: UUID, cluster_set_id: UUID, *, actor_user_id: UUID
    ) -> ClusterSet:
        with open_database_connection(self._settings) as connection:
            with connection.transaction():
                current = connection.execute(
                    """
                    SELECT status, phase
                    FROM cluster_sets
                    WHERE id = %s AND project_id = %s AND deleted_at IS NULL
                    """,
                    (cluster_set_id, project_id),
                ).fetchone()
                if current is None:
                    raise ClusterError(
                        "Cluster-Set not found",
                        code="CLUSTER_SET_NOT_FOUND",
                        status_code=404,
                    )
                status_value = str(current["status"])
                phase_value = str(current["phase"])
                if status_value in TERMINAL_CLUSTER_SET_STATUSES:
                    raise ClusterError(
                        "Cluster-Set can no longer be cancelled",
                        code="CLUSTER_SET_CANCEL_NOT_AVAILABLE",
                        status_code=409,
                        suggested_action="reload",
                    )
                is_queued_summary = (
                    status_value == "queued" and phase_value == "queued_summary"
                )
                next_status = (
                    "completed"
                    if is_queued_summary
                    else ("cancelled" if status_value == "queued" else "cancelling")
                )
                next_phase = (
                    "completed"
                    if is_queued_summary
                    else ("cancelled" if next_status == "cancelled" else "cancelling")
                )
                connection.execute(
                    """
                    UPDATE cluster_sets
                    SET status = %s,
                        phase = %s,
                        progress = CASE
                            WHEN %s THEN 100
                            ELSE progress
                        END,
                        cancel_requested_at = COALESCE(cancel_requested_at, now()),
                        completed_at = CASE
                            WHEN %s THEN COALESCE(completed_at, now())
                            WHEN %s = 'cancelled' THEN COALESCE(completed_at, now())
                            ELSE completed_at
                        END,
                        updated_at = now(),
                        diagnostics = CASE
                            WHEN %s THEN diagnostics || %s
                            ELSE diagnostics
                        END
                    WHERE id = %s AND project_id = %s AND deleted_at IS NULL
                    """,
                    (
                        next_status,
                        next_phase,
                        is_queued_summary,
                        is_queued_summary,
                        next_status,
                        is_queued_summary,
                        Jsonb({"summary_regeneration_cancelled": True}),
                        cluster_set_id,
                        project_id,
                    ),
                )
                self._record_cluster_set_event(
                    connection,
                    project_id=project_id,
                    cluster_set_id=cluster_set_id,
                    actor_user_id=actor_user_id,
                    event_type="cancel_requested",
                    metadata={"status": next_status, "phase": next_phase},
                )
        fresh = self.get_cluster_set(project_id, cluster_set_id)
        if fresh is None:
            raise RuntimeError("Cluster-Set disappeared after cancel")
        return fresh

    def delete_cluster_set(
        self, project_id: UUID, cluster_set_id: UUID, *, actor_user_id: UUID
    ) -> None:
        with open_database_connection(self._settings) as connection:
            with connection.transaction():
                row = connection.execute(
                    """
                    UPDATE cluster_sets
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
                    (actor_user_id, cluster_set_id, project_id),
                ).fetchone()
                if row is None:
                    raise ClusterError(
                        "Cluster-Set not found",
                        code="CLUSTER_SET_NOT_FOUND",
                        status_code=404,
                    )
                self._record_cluster_set_event(
                    connection,
                    project_id=project_id,
                    cluster_set_id=cluster_set_id,
                    actor_user_id=actor_user_id,
                    event_type="deleted",
                    metadata={},
                )

    def batch_delete_cluster_sets(
        self,
        project_id: UUID,
        cluster_set_ids: list[UUID],
        *,
        actor_user_id: UUID,
    ) -> list[UUID]:
        selected_ids = list(dict.fromkeys(cluster_set_ids))
        if not selected_ids:
            raise ClusterError(
                "Cluster-Set batch delete requires a non-empty selection",
                code="CLUSTER_SET_BATCH_DELETE_FAILED",
                status_code=422,
                retryable=True,
                suggested_action="reload",
                field_errors={
                    "cluster_set_ids": (
                        "Cluster-Set batch delete requires a non-empty selection"
                    )
                },
            )
        with open_database_connection(self._settings) as connection:
            with connection.transaction():
                rows = connection.execute(
                    """
                    SELECT id
                    FROM cluster_sets
                    WHERE project_id = %s
                      AND deleted_at IS NULL
                      AND id = ANY(%s)
                    FOR UPDATE
                    """,
                    (project_id, selected_ids),
                ).fetchall()
                available_ids = {UUID(str(row["id"])) for row in rows}
                if available_ids != set(selected_ids):
                    raise ClusterError(
                        "Cluster-Set batch delete cannot delete every selected set",
                        code="CLUSTER_SET_BATCH_DELETE_FAILED",
                        status_code=409,
                        retryable=True,
                        suggested_action="reload",
                    )
                deleted_rows = connection.execute(
                    """
                    UPDATE cluster_sets
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
                    WHERE project_id = %s
                      AND deleted_at IS NULL
                      AND id = ANY(%s)
                    RETURNING id
                    """,
                    (actor_user_id, project_id, selected_ids),
                ).fetchall()
                deleted_ids = [UUID(str(row["id"])) for row in deleted_rows]
                if set(deleted_ids) != set(selected_ids):
                    raise ClusterError(
                        "Cluster-Set batch delete did not delete every selected set",
                        code="CLUSTER_SET_BATCH_DELETE_FAILED",
                        status_code=409,
                        retryable=True,
                        suggested_action="reload",
                    )
                for deleted_id in selected_ids:
                    self._record_cluster_set_event(
                        connection,
                        project_id=project_id,
                        cluster_set_id=deleted_id,
                        actor_user_id=actor_user_id,
                        event_type="deleted",
                        metadata={"batch": True, "selection_count": len(selected_ids)},
                    )
                self._audit.record_event(
                    connection,
                    actor_user_id=actor_user_id,
                    action="cluster_set.batch_delete",
                    target_type="project",
                    target_id=project_id,
                    metadata={
                        "project_id": str(project_id),
                        "cluster_set_count": len(selected_ids),
                    },
                )
        return selected_ids

    def list_cluster_set_events(
        self, project_id: UUID, cluster_set_id: UUID
    ) -> list[ClusterSetEvent]:
        with open_database_connection(self._settings) as connection:
            exists = connection.execute(
                """
                SELECT id
                FROM cluster_sets
                WHERE id = %s AND project_id = %s
                """,
                (cluster_set_id, project_id),
            ).fetchone()
            if exists is None:
                raise ClusterError(
                    "Cluster-Set not found",
                    code="CLUSTER_SET_NOT_FOUND",
                    status_code=404,
                )
            rows = connection.execute(
                """
                SELECT id, project_id, cluster_set_id, event_type, metadata,
                       created_at
                FROM cluster_set_events
                WHERE project_id = %s AND cluster_set_id = %s
                ORDER BY created_at ASC
                """,
                (project_id, cluster_set_id),
            ).fetchall()
        return [_cluster_set_event_from_row(dict(row)) for row in rows]

    def list_clusters_for_set(
        self, project_id: UUID, cluster_set_id: UUID
    ) -> list[Cluster]:
        with open_database_connection(self._settings) as connection:
            cluster_set = connection.execute(
                """
                SELECT id, status
                FROM cluster_sets
                WHERE id = %s
                  AND project_id = %s
                  AND deleted_at IS NULL
                """,
                (cluster_set_id, project_id),
            ).fetchone()
            if cluster_set is None:
                raise ClusterError(
                    "Cluster-Set not found",
                    code="CLUSTER_SET_NOT_FOUND",
                    status_code=404,
                )
            if cluster_set["status"] != "completed":
                raise ClusterError(
                    "Cluster-Set is not completed",
                    code="CLUSTER_SET_NOT_COMPLETE",
                    status_code=409,
                    retryable=True,
                    suggested_action="wait",
                )
            rows = connection.execute(
                """
                SELECT c.id, c.project_id, c.analysis_run_id,
                       c.dataset_version_id, c.cluster_set_id,
                       c.auto_title, c.manual_title, c.auto_category,
                       c.manual_category, c.auto_status, c.manual_status,
                       c.auto_summary_question, c.auto_summary_answer,
                       c.score, c.is_outlier, c.algorithm, c.metadata,
                       c.created_at, c.updated_at, COUNT(cm.id) AS member_count
                FROM clusters c
                JOIN cluster_sets cs
                  ON cs.id = c.cluster_set_id
                 AND cs.project_id = c.project_id
                 AND cs.deleted_at IS NULL
                LEFT JOIN cluster_memberships cm ON cm.cluster_id = c.id
                WHERE c.project_id = %s AND c.cluster_set_id = %s
                GROUP BY c.id
                ORDER BY c.is_outlier ASC, c.score DESC, c.created_at ASC
                """,
                (project_id, cluster_set_id),
            ).fetchall()
        return [_cluster_from_row(dict(row)) for row in rows]

    def generate_for_run(
        self, project_id: UUID, run_id: UUID, *, actor_user_id: UUID
    ) -> list[Cluster]:
        with open_database_connection(self._settings) as connection:
            with connection.transaction():
                run = connection.execute(
                    """
                    SELECT id, project_id, dataset_version_id, status,
                           parameters, provider, model
                    FROM analysis_runs
                    WHERE id = %s AND project_id = %s
                    """,
                    (run_id, project_id),
                ).fetchone()
                if run is None:
                    raise ClusterError("analysis run not found")
                if run["status"] != "completed":
                    raise ClusterError(
                        "analysis run must be completed before clustering"
                    )
                existing = connection.execute(
                    "SELECT id FROM clusters WHERE project_id = %s AND analysis_run_id = %s LIMIT 1",
                    (project_id, run_id),
                ).fetchone()
                if existing is None:
                    config = validate_algorithm_settings(
                        {"algorithm": "hdbscan", "min_cluster_size": 2}
                    )
                    record_limit = (
                        AGGLOMERATIVE_MAX_RECORDS
                        if config.name == "agglomerative"
                        else HDBSCAN_MAX_RECORDS
                    )
                    input_summary = connection.execute(
                        """
                        SELECT COUNT(mp.id) AS record_count,
                               COUNT(e.id) AS embedding_count,
                               MIN(e.dimensions) AS minimum_dimensions,
                               MAX(e.dimensions) AS maximum_dimensions
                        FROM message_pairs mp
                        LEFT JOIN embeddings e
                          ON e.project_id = mp.project_id
                         AND e.analysis_run_id = %s
                         AND e.dataset_version_id = mp.dataset_version_id
                         AND e.source_object_type = 'message_pair'
                         AND e.source_object_id = mp.id
                         AND e.text_variant = 'message'
                        WHERE mp.project_id = %s AND mp.dataset_version_id = %s
                        """,
                        (run_id, project_id, run["dataset_version_id"]),
                    ).fetchone()
                    if input_summary is None:
                        raise ClusterError(
                            "analysis run embedding summary is unavailable"
                        )
                    expected_dimensions = validate_cluster_input_budget(
                        config,
                        record_count=int(str(input_summary["record_count"])),
                        embedding_count=int(str(input_summary["embedding_count"])),
                        minimum_dimensions=(
                            int(str(input_summary["minimum_dimensions"]))
                            if input_summary["minimum_dimensions"] is not None
                            else None
                        ),
                        maximum_dimensions=(
                            int(str(input_summary["maximum_dimensions"]))
                            if input_summary["maximum_dimensions"] is not None
                            else None
                        ),
                    )
                    pair_ids, vectors = self._load_native_embedding_matrix(
                        connection,
                        project_id=project_id,
                        run_id=run_id,
                        dataset_version_id=UUID(str(run["dataset_version_id"])),
                        record_limit=record_limit,
                        expected_record_count=int(str(input_summary["record_count"])),
                        expected_dimensions=expected_dimensions,
                    )
                    self._validate_and_insert_clusters(
                        connection,
                        project_id=project_id,
                        run_id=run_id,
                        dataset_version_id=UUID(str(run["dataset_version_id"])),
                        provider=str(run["provider"]),
                        model=str(run["model"]),
                        config=config,
                        pair_ids=pair_ids,
                        vectors=vectors,
                        expected_dimensions=expected_dimensions,
                    )
                    self._audit.record_event(
                        connection,
                        actor_user_id=actor_user_id,
                        action="clusters.generate",
                        target_type="analysis_run",
                        target_id=run_id,
                        metadata={
                            "project_id": str(project_id),
                            "pairs": len(pair_ids),
                            "algorithm": config.name,
                        },
                    )
        return self.list_clusters(project_id, run_id)

    def list_clusters(self, project_id: UUID, run_id: UUID) -> list[Cluster]:
        with open_database_connection(self._settings) as connection:
            rows = connection.execute(
                """
                SELECT c.id, c.project_id, c.analysis_run_id, c.dataset_version_id,
                       c.auto_title, c.manual_title, c.auto_category,
                       c.manual_category, c.auto_status, c.manual_status,
                       c.score, c.is_outlier, c.algorithm, c.metadata,
                       c.created_at, c.updated_at, COUNT(cm.id) AS member_count
                FROM clusters c
                LEFT JOIN cluster_memberships cm ON cm.cluster_id = c.id
                WHERE c.project_id = %s AND c.analysis_run_id = %s
                GROUP BY c.id
                ORDER BY c.is_outlier ASC, c.score DESC, c.created_at ASC
                """,
                (project_id, run_id),
            ).fetchall()
        return [_cluster_from_row(dict(row)) for row in rows]

    def update_cluster(
        self,
        project_id: UUID,
        cluster_id: UUID,
        payload: ClusterManualUpdate,
        *,
        actor_user_id: UUID,
    ) -> Cluster:
        manual_title = _clean_optional(payload.manual_title)
        manual_category = _clean_optional(payload.manual_category)
        manual_status = _clean_optional(payload.manual_status)
        fields_to_update = payload.fields_to_update or frozenset(
            field_name
            for field_name, value in (
                ("manual_title", payload.manual_title),
                ("manual_category", payload.manual_category),
                ("manual_status", payload.manual_status),
            )
            if value is not None
        )
        if manual_status is not None and manual_status not in VALID_STATUSES:
            raise ClusterError(
                "manual_status is invalid",
                code="CLUSTER_MANUAL_UPDATE_INVALID",
                status_code=422,
                field_errors={"manual_status": "manual_status is invalid"},
            )
        with open_database_connection(self._settings) as connection:
            with connection.transaction():
                row = connection.execute(
                    """
                    UPDATE clusters c
                    SET manual_title = CASE WHEN %s THEN %s ELSE manual_title END,
                        manual_category = CASE WHEN %s THEN %s ELSE manual_category END,
                        manual_status = CASE WHEN %s THEN %s ELSE manual_status END,
                        updated_at = now()
                    WHERE c.id = %s
                      AND c.project_id = %s
                      AND (
                          c.cluster_set_id IS NULL
                          OR EXISTS (
                              SELECT 1
                              FROM cluster_sets cs
                              WHERE cs.id = c.cluster_set_id
                                AND cs.project_id = c.project_id
                                AND cs.deleted_at IS NULL
                          )
                      )
                    RETURNING analysis_run_id, cluster_set_id
                    """,
                    (
                        "manual_title" in fields_to_update,
                        manual_title,
                        "manual_category" in fields_to_update,
                        manual_category,
                        "manual_status" in fields_to_update,
                        manual_status,
                        cluster_id,
                        project_id,
                    ),
                ).fetchone()
                if row is None:
                    raise ClusterError(
                        "cluster not found",
                        code="CLUSTER_SET_NOT_FOUND",
                        status_code=404,
                        retryable=True,
                        suggested_action="reload",
                    )
                self._audit.record_event(
                    connection,
                    actor_user_id=actor_user_id,
                    action="cluster.update_manual",
                    target_type="cluster",
                    target_id=cluster_id,
                    metadata={
                        "project_id": str(project_id),
                        "updated_fields": sorted(fields_to_update),
                    },
                )
                cluster_set_id = (
                    UUID(str(row["cluster_set_id"]))
                    if row["cluster_set_id"] is not None
                    else None
                )
                if cluster_set_id is not None:
                    connection.execute(
                        """
                        UPDATE cluster_sets
                        SET updated_at = now()
                        WHERE id = %s
                          AND project_id = %s
                          AND deleted_at IS NULL
                        """,
                        (cluster_set_id, project_id),
                    )
                    self._record_cluster_set_event(
                        connection,
                        project_id=project_id,
                        cluster_set_id=cluster_set_id,
                        actor_user_id=actor_user_id,
                        event_type="cluster_manual_updated",
                        metadata={
                            "cluster_id": str(cluster_id),
                            "updated_fields": sorted(fields_to_update),
                            "manual_status": manual_status,
                        },
                    )
                run_id = UUID(str(row["analysis_run_id"]))
        clusters = (
            self.list_clusters_for_set(project_id, cluster_set_id)
            if cluster_set_id is not None
            else self.list_clusters(project_id, run_id)
        )
        for cluster in clusters:
            if cluster.id == cluster_id:
                return cluster
        raise RuntimeError("cluster disappeared after update")

    def list_sources(
        self,
        project_id: UUID,
        cluster_id: UUID,
        *,
        limit: int = DEFAULT_CLUSTER_SOURCE_PAGE_SIZE,
        offset: int = 0,
    ) -> ClusterSourcePage:
        if (
            limit < 1
            or limit > MAX_CLUSTER_SOURCE_PAGE_SIZE
            or offset < 0
            or offset > MAX_CLUSTER_SOURCE_OFFSET
        ):
            raise ClusterError(
                "cluster source page parameters are invalid",
                code="CLUSTER_SOURCE_PAGE_INVALID",
                status_code=422,
                retryable=True,
                suggested_action="correct-input",
                field_errors={
                    "limit": (
                        f"limit must be between 1 and {MAX_CLUSTER_SOURCE_PAGE_SIZE}"
                    ),
                    "offset": (
                        f"offset must be between 0 and {MAX_CLUSTER_SOURCE_OFFSET}"
                    ),
                },
            )
        with open_database_connection(self._settings) as connection:
            cluster = connection.execute(
                """
                SELECT c.id, c.cluster_set_id, cs.status AS cluster_set_status
                FROM clusters c
                LEFT JOIN cluster_sets cs
                  ON cs.id = c.cluster_set_id
                 AND cs.project_id = c.project_id
                WHERE c.id = %s
                  AND c.project_id = %s
                  AND (
                      c.cluster_set_id IS NULL
                      OR (cs.id IS NOT NULL AND cs.deleted_at IS NULL)
                  )
                """,
                (cluster_id, project_id),
            ).fetchone()
            if cluster is None:
                raise ClusterError(
                    "cluster source target not found",
                    code="CLUSTER_SOURCE_NOT_FOUND",
                    status_code=404,
                    retryable=True,
                    suggested_action="reload",
                )
            if (
                cluster["cluster_set_id"] is not None
                and str(cluster["cluster_set_status"]) != "completed"
            ):
                raise ClusterError(
                    "Cluster-Set is not completed",
                    code="CLUSTER_SET_NOT_COMPLETE",
                    status_code=409,
                    retryable=True,
                    suggested_action="wait",
                )
            rows = connection.execute(
                """
                SELECT cm.cluster_id, cm.message_pair_id, mp.ticket_id,
                       mp.message_group_id, mp.message, mp.answer,
                       cm.membership_score, cm.is_outlier, cm.assignment_type
                FROM cluster_memberships cm
                JOIN clusters c ON c.id = cm.cluster_id AND c.project_id = %s
                JOIN message_pairs mp
                  ON mp.id = cm.message_pair_id
                 AND mp.project_id = cm.project_id
                WHERE cm.project_id = %s AND cm.cluster_id = %s
                ORDER BY cm.is_outlier ASC, cm.membership_score DESC, mp.ordinal ASC
                LIMIT %s OFFSET %s
                """,
                (project_id, project_id, cluster_id, limit + 1, offset),
            ).fetchall()
        has_more = len(rows) > limit
        page_rows = rows[:limit]
        sources = [_source_from_row(dict(row)) for row in page_rows]
        return ClusterSourcePage(
            sources=sources,
            limit=limit,
            offset=offset,
            next_offset=offset + len(sources) if has_more else None,
            has_more=has_more,
        )

    def execute_queued_cluster_set(self, cluster_set_id: UUID) -> None:
        with open_database_connection(self._settings) as connection:
            with connection.transaction():
                cluster_set = connection.execute(
                    """
                    UPDATE cluster_sets cs
                    SET status = 'running',
                        progress = %s,
                        phase = 'loading',
                        started_at = now(),
                        updated_at = now()
                    FROM analysis_runs r
                    WHERE cs.id = %s
                      AND cs.status = 'queued'
                      AND cs.phase = 'queued'
                      AND cs.deleted_at IS NULL
                      AND r.id = cs.indexing_run_id
                      AND r.project_id = cs.project_id
                    RETURNING cs.id, cs.project_id, cs.indexing_run_id,
                              cs.dataset_version_id, cs.vector_basis,
                              cs.message_weight, cs.answer_weight,
                              cs.algorithm, cs.parameters, cs.source_snapshot,
                              cs.llm_provider, cs.llm_provider_configuration_id,
                              cs.llm_provider_display_name, cs.llm_model,
                              cs.llm_sample_strategy, r.provider, r.model
                    """,
                    (CLUSTER_SET_START_PROGRESS, cluster_set_id),
                ).fetchone()
                if cluster_set is None:
                    return
        try:
            job_started_at = perf_counter()
            loaded_at = job_started_at
            clustered_at = job_started_at
            persisted_at = job_started_at
            config = validate_algorithm_settings(
                {
                    "algorithm": str(cluster_set["algorithm"]),
                    **_json_object(cluster_set["parameters"]),
                }
            )
            project_id = UUID(str(cluster_set["project_id"]))
            indexing_run_id = UUID(str(cluster_set["indexing_run_id"]))
            dataset_version_id = UUID(str(cluster_set["dataset_version_id"]))
            vector_basis = str(cluster_set["vector_basis"])
            message_weight = float(str(cluster_set["message_weight"]))
            answer_weight = float(str(cluster_set["answer_weight"]))
            source_snapshot = _json_object(cluster_set["source_snapshot"])
            source_pair_ids = self._snapshot_pair_ids(source_snapshot)
            is_per_parent_refinement = (
                self._snapshot_refinement_mode(source_snapshot) == "per_parent"
            )
            source_cluster_ids = self._snapshot_source_cluster_ids(source_snapshot)
            record_limit = (
                AGGLOMERATIVE_MAX_RECORDS
                if config.name == "agglomerative"
                else HDBSCAN_MAX_RECORDS
            )
            batch_groups: list[BatchRefinementGroup] = []
            if is_per_parent_refinement:
                parent_cluster_set_id = source_snapshot.get("parent_cluster_set_id")
                if not isinstance(parent_cluster_set_id, str):
                    raise ClusterError(
                        "per-parent refinement parent is unavailable",
                        code="CLUSTER_BATCH_REFINEMENT_EMPTY_GROUP",
                        status_code=422,
                    )
                with open_database_connection(self._settings) as connection:
                    batch_groups = self._per_parent_refinement_groups(
                        connection,
                        project_id=project_id,
                        parent_cluster_set_id=UUID(parent_cluster_set_id),
                        dataset_version_id=dataset_version_id,
                        source_cluster_ids=source_cluster_ids,
                    )

            basis_budget: ClusterSetBasisBudget | None = None
            if is_per_parent_refinement:
                self._publish_cluster_set_progress(
                    cluster_set_id, CLUSTER_SET_LOAD_PROGRESS, "loading"
                )
            else:
                with open_database_connection(self._settings) as connection:
                    with connection.transaction():
                        self._raise_if_cluster_set_cancelled(connection, cluster_set_id)
                        input_summary = self._cluster_set_input_summary(
                            connection,
                            project_id=project_id,
                            indexing_run_id=indexing_run_id,
                            dataset_version_id=dataset_version_id,
                            source_pair_ids=source_pair_ids,
                        )
                        basis_budget = self._validate_cluster_set_basis_budget(
                            config,
                            vector_basis=vector_basis,
                            input_summary=input_summary,
                        )
                        self._publish_cluster_set_progress(
                            cluster_set_id, CLUSTER_SET_LOAD_PROGRESS, "loading"
                        )
                        pair_ids, vectors, mismatch_scores = (
                            self._load_cluster_set_embedding_matrix(
                                connection,
                                project_id=project_id,
                                indexing_run_id=indexing_run_id,
                                dataset_version_id=dataset_version_id,
                                vector_basis=vector_basis,
                                message_weight=message_weight,
                                answer_weight=answer_weight,
                                source_pair_ids=source_pair_ids,
                                record_limit=record_limit,
                                expected_record_count=int(
                                    str(input_summary["record_count"])
                                ),
                                expected_dimensions=basis_budget.output_dimensions,
                                message_expected_dimensions=(
                                    basis_budget.message_dimensions
                                ),
                                answer_expected_dimensions=(
                                    basis_budget.answer_dimensions
                                ),
                            )
                        )
                        self._raise_if_cluster_set_cancelled(connection, cluster_set_id)

            loaded_at = perf_counter()
            clustering_diagnostics: dict[str, object] = {}
            origin_by_pair_id: dict[object, ClusterOrigin] | None = None
            if is_per_parent_refinement:
                all_pair_ids: list[object] = []
                all_labels: list[int] = []
                all_probabilities: list[float] = []
                all_mismatch_scores: dict[object, float] = {}
                origin_by_pair_id = {}
                for group_index, group in enumerate(batch_groups):
                    with open_database_connection(self._settings) as connection:
                        with connection.transaction():
                            input_summary = self._cluster_set_input_summary(
                                connection,
                                project_id=project_id,
                                indexing_run_id=indexing_run_id,
                                dataset_version_id=dataset_version_id,
                                source_pair_ids=group.pair_ids,
                            )
                            basis_budget = self._validate_cluster_set_basis_budget(
                                config,
                                vector_basis=vector_basis,
                                input_summary=input_summary,
                            )
                            group_pair_ids, group_vectors, group_mismatch_scores = (
                                self._load_cluster_set_embedding_matrix(
                                    connection,
                                    project_id=project_id,
                                    indexing_run_id=indexing_run_id,
                                    dataset_version_id=dataset_version_id,
                                    vector_basis=vector_basis,
                                    message_weight=message_weight,
                                    answer_weight=answer_weight,
                                    source_pair_ids=group.pair_ids,
                                    record_limit=record_limit,
                                    expected_record_count=int(
                                        str(input_summary["record_count"])
                                    ),
                                    expected_dimensions=basis_budget.output_dimensions,
                                    message_expected_dimensions=(
                                        basis_budget.message_dimensions
                                    ),
                                    answer_expected_dimensions=(
                                        basis_budget.answer_dimensions
                                    ),
                                )
                            )
                    self._publish_cluster_set_progress(
                        cluster_set_id,
                        CLUSTER_SET_CLUSTERING_PROGRESS,
                        f"clustering_group_{group_index + 1}",
                    )
                    try:
                        group_labels, group_probabilities = self._cluster_vectors(
                            config, group_vectors
                        )
                    except ClusterError as exc:
                        raise ClusterError(
                            str(exc),
                            code="CLUSTER_BATCH_REFINEMENT_GROUP_INVALID",
                            status_code=422,
                            retryable=True,
                            suggested_action="adjust-clustering-parameters",
                        ) from exc
                    for pair_id, local_label in zip(
                        group_pair_ids, group_labels, strict=True
                    ):
                        origin_by_pair_id[pair_id] = ClusterOrigin(
                            source_parent_cluster_id=group.cluster_id,
                            source_parent_cluster_title=group.title,
                            source_parent_cluster_label=group.label,
                            source_parent_cluster_is_outlier=group.is_outlier,
                            batch_group_index=group_index,
                            local_cluster_label=int(local_label),
                        )
                    all_pair_ids.extend(group_pair_ids)
                    all_labels.extend(
                        [
                            (-1_000_000 - group_index)
                            if int(label) == -1
                            else group_index * 100_000 + int(label)
                            for label in group_labels
                        ]
                    )
                    all_probabilities.extend(group_probabilities)
                    all_mismatch_scores.update(group_mismatch_scores)
                pair_ids = all_pair_ids
                labels = all_labels
                probabilities = all_probabilities
                mismatch_scores = all_mismatch_scores
                clustered_at = perf_counter()
            elif config.name == "hdbscan":
                if config.parameters.get("reduction_method") == "none":
                    reduced_vectors = vectors
                else:
                    self._publish_cluster_set_progress(
                        cluster_set_id, CLUSTER_SET_REDUCTION_PROGRESS, "reducing"
                    )
                    reduced_vectors = self._reduce_hdbscan_vectors(config, vectors)
                self._publish_cluster_set_progress(
                    cluster_set_id, CLUSTER_SET_CLUSTERING_PROGRESS, "clustering"
                )
                normalized_labels, probabilities, clustering_diagnostics = (
                    self._fit_hdbscan_vectors(config, reduced_vectors)
                )
                labels = _apply_outlier_threshold(
                    normalized_labels,
                    probabilities,
                    cast(float | None, config.parameters.get("outlier_threshold")),
                )
                clustered_at = perf_counter()
            else:
                self._publish_cluster_set_progress(
                    cluster_set_id, CLUSTER_SET_CLUSTERING_PROGRESS, "clustering"
                )
                labels, probabilities = self._cluster_vectors(config, vectors)
                clustered_at = perf_counter()
            if basis_budget is None:
                raise ClusterError(
                    "Cluster-Set source contains no usable parent groups",
                    code="CLUSTER_REFINEMENT_EMPTY_SOURCE",
                    status_code=422,
                )
            self._publish_cluster_set_progress(
                cluster_set_id, CLUSTER_SET_PERSIST_PROGRESS, "persisting"
            )
            with open_database_connection(self._settings) as connection:
                with connection.transaction():
                    self._raise_if_cluster_set_cancelled(connection, cluster_set_id)
                    self._insert_cluster_set_clusters(
                        connection,
                        project_id=project_id,
                        cluster_set_id=cluster_set_id,
                        indexing_run_id=indexing_run_id,
                        dataset_version_id=dataset_version_id,
                        embedding_provider=str(cluster_set["provider"]),
                        embedding_model=str(cluster_set["model"]),
                        config=config,
                        pair_ids=pair_ids,
                        labels=labels,
                        probabilities=probabilities,
                        mismatch_scores=mismatch_scores,
                        expected_dimensions=basis_budget.output_dimensions,
                        vector_basis=vector_basis,
                        message_weight=message_weight,
                        answer_weight=answer_weight,
                        origin_by_pair_id=origin_by_pair_id,
                    )
                    self._record_cluster_set_event(
                        connection,
                        project_id=project_id,
                        cluster_set_id=cluster_set_id,
                        actor_user_id=None,
                        event_type="clusters_created",
                        metadata={
                            "cluster_count": len(set(int(label) for label in labels))
                        },
                    )

            persisted_at = perf_counter()
            summary_error: Exception | None = None
            if (
                cluster_set["llm_provider"] is not None
                and cluster_set["llm_model"] is not None
            ):
                try:
                    self._publish_cluster_set_progress(
                        cluster_set_id,
                        CLUSTER_SET_SUMMARY_PROGRESS,
                        "summarizing",
                    )
                    llm_provider_configuration_id = cluster_set[
                        "llm_provider_configuration_id"
                    ]
                    if llm_provider_configuration_id is None:
                        raise ClusterError(
                            "LLM provider configuration is no longer available",
                            code="LLM_PROVIDER_UNAVAILABLE",
                            status_code=503,
                            retryable=True,
                        )
                    self._generate_cluster_summaries(
                        project_id=project_id,
                        cluster_set_id=cluster_set_id,
                        llm_provider=UUID(str(llm_provider_configuration_id)),
                        llm_provider_type=str(cluster_set["llm_provider"]),
                        llm_provider_display_name=(
                            str(cluster_set["llm_provider_display_name"])
                            if cluster_set["llm_provider_display_name"] is not None
                            else None
                        ),
                        llm_model=str(cluster_set["llm_model"]),
                        sample_strategy=_json_object(
                            cluster_set["llm_sample_strategy"]
                        ),
                    )
                except Exception as exc:
                    summary_error = exc

            timings_seconds = {
                "load": round(loaded_at - job_started_at, 3),
                "cluster": round(clustered_at - loaded_at, 3),
                "persist": round(persisted_at - clustered_at, 3),
                "total": round(perf_counter() - job_started_at, 3),
            }
            with open_database_connection(self._settings) as connection:
                with connection.transaction():
                    self._raise_if_cluster_set_cancelled(connection, cluster_set_id)
                    if summary_error is None:
                        connection.execute(
                            """
                            UPDATE cluster_sets
                            SET status = 'completed',
                                progress = 100,
                                phase = 'completed',
                                completed_at = now(),
                                updated_at = now(),
                                diagnostics = diagnostics || %s
                            WHERE id = %s AND status = 'running'
                            """,
                            (
                                Jsonb(
                                    {
                                        "completed": True,
                                        "timings_seconds": timings_seconds,
                                        "clustering": clustering_diagnostics,
                                    }
                                ),
                                cluster_set_id,
                            ),
                        )
                    else:
                        code, message, retryable = _safe_cluster_failure(summary_error)
                        if code == "UNEXPECTED_ERROR":
                            code = "CLUSTER_SUMMARY_FAILED"
                            message = "Cluster summary generation failed"
                        connection.execute(
                            """
                            UPDATE cluster_sets
                            SET status = 'completed',
                                progress = 100,
                                phase = 'completed',
                                error_code = %s,
                                error_message = %s,
                                completed_at = now(),
                                updated_at = now(),
                                diagnostics = diagnostics || %s
                            WHERE id = %s AND status = 'running'
                            """,
                            (
                                code,
                                message,
                                Jsonb(
                                    {
                                        "summary_failed": True,
                                        "summary_failure_retryable": retryable,
                                        "summary_failure_type": summary_error.__class__.__name__,
                                        "timings_seconds": timings_seconds,
                                        "clustering": clustering_diagnostics,
                                    }
                                ),
                                cluster_set_id,
                            ),
                        )
        except ClusterSetCancelled:
            with open_database_connection(self._settings) as connection:
                with connection.transaction():
                    connection.execute(
                        """
                        UPDATE cluster_sets
                        SET status = 'cancelled',
                            phase = 'cancelled',
                            completed_at = now(),
                            updated_at = now(),
                            diagnostics = diagnostics || %s
                        WHERE id = %s AND status IN ('running', 'cancelling')
                        """,
                        (
                            Jsonb({"cancelled": True}),
                            cluster_set_id,
                        ),
                    )
        except Exception as exc:
            code, message, retryable = _safe_cluster_failure(exc)
            with open_database_connection(self._settings) as connection:
                with connection.transaction():
                    connection.execute(
                        """
                        UPDATE cluster_sets
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
                                    "failure_type": exc.__class__.__name__,
                                    "retryable": retryable,
                                }
                            ),
                            cluster_set_id,
                        ),
                    )

    def execute_queued_cluster_set_summary_regeneration(
        self, cluster_set_id: UUID
    ) -> None:
        with open_database_connection(self._settings) as connection:
            with connection.transaction():
                cluster_set = connection.execute(
                    """
                    UPDATE cluster_sets
                    SET status = 'running',
                        progress = %s,
                        phase = 'summarizing',
                        started_at = COALESCE(started_at, now()),
                        updated_at = now()
                    WHERE id = %s
                      AND status = 'queued'
                      AND phase = 'queued_summary'
                      AND deleted_at IS NULL
                    RETURNING id, project_id, llm_provider,
                              llm_provider_configuration_id,
                              llm_provider_display_name, llm_model,
                              llm_sample_strategy
                    """,
                    (CLUSTER_SET_SUMMARY_PROGRESS, cluster_set_id),
                ).fetchone()
                if cluster_set is None:
                    return
        try:
            project_id = UUID(str(cluster_set["project_id"]))
            llm_provider_configuration_id = cluster_set["llm_provider_configuration_id"]
            if (
                cluster_set["llm_provider"] is None
                or cluster_set["llm_model"] is None
                or llm_provider_configuration_id is None
            ):
                raise ClusterError(
                    "LLM provider configuration is no longer available",
                    code="LLM_PROVIDER_UNAVAILABLE",
                    status_code=503,
                    retryable=True,
                )
            self._generate_cluster_summaries(
                project_id=project_id,
                cluster_set_id=cluster_set_id,
                llm_provider=UUID(str(llm_provider_configuration_id)),
                llm_provider_type=str(cluster_set["llm_provider"]),
                llm_provider_display_name=(
                    str(cluster_set["llm_provider_display_name"])
                    if cluster_set["llm_provider_display_name"] is not None
                    else None
                ),
                llm_model=str(cluster_set["llm_model"]),
                sample_strategy=_json_object(cluster_set["llm_sample_strategy"]),
            )
            with open_database_connection(self._settings) as connection:
                with connection.transaction():
                    self._raise_if_cluster_set_cancelled(connection, cluster_set_id)
                    connection.execute(
                        """
                        UPDATE cluster_sets
                        SET status = 'completed',
                            progress = 100,
                            phase = 'completed',
                            error_code = NULL,
                            error_message = NULL,
                            updated_at = now(),
                            diagnostics = diagnostics || %s
                        WHERE id = %s AND status = 'running'
                        """,
                        (
                            Jsonb({"summary_regenerated": True}),
                            cluster_set_id,
                        ),
                    )
        except ClusterSetCancelled:
            with open_database_connection(self._settings) as connection:
                with connection.transaction():
                    connection.execute(
                        """
                        UPDATE cluster_sets
                        SET status = 'completed',
                            progress = 100,
                            phase = 'completed',
                            updated_at = now(),
                            diagnostics = diagnostics || %s
                        WHERE id = %s AND status IN ('running', 'cancelling')
                        """,
                        (
                            Jsonb({"summary_regeneration_cancelled": True}),
                            cluster_set_id,
                        ),
                    )
        except Exception as exc:
            code, message, retryable = _safe_cluster_failure(exc)
            if code == "UNEXPECTED_ERROR":
                code = "CLUSTER_SUMMARY_FAILED"
                message = "Cluster summary generation failed"
            with open_database_connection(self._settings) as connection:
                with connection.transaction():
                    connection.execute(
                        """
                        UPDATE cluster_sets
                        SET status = 'completed',
                            progress = 100,
                            phase = 'completed',
                            error_code = %s,
                            error_message = %s,
                            updated_at = now(),
                            diagnostics = diagnostics || %s
                        WHERE id = %s AND deleted_at IS NULL
                        """,
                        (
                            code,
                            message,
                            Jsonb(
                                {
                                    "summary_regeneration_failed": True,
                                    "summary_failure_retryable": retryable,
                                    "summary_failure_type": exc.__class__.__name__,
                                }
                            ),
                            cluster_set_id,
                        ),
                    )

    def _fetch_cluster_set_row(
        self, connection: Any, project_id: UUID, cluster_set_id: UUID
    ) -> dict[str, object] | None:
        return connection.execute(
            """
            SELECT cs.id, cs.project_id, cs.indexing_run_id,
                   cs.dataset_version_id,
                   d.display_name AS dataset_display_name,
                   r.deleted_at AS indexing_deleted_at,
                   cs.parent_cluster_set_id, cs.display_name, cs.status,
                   cs.progress, cs.phase, cs.derivation_type,
                   cs.vector_basis, cs.message_weight, cs.answer_weight,
                   cs.algorithm, cs.parameters, cs.source_snapshot,
                   cs.llm_provider, cs.llm_provider_configuration_id,
                   cs.llm_provider_display_name, cs.llm_model,
                   cs.llm_parameters, cs.llm_sample_strategy,
                   cs.error_code, cs.error_message,
                   cs.diagnostics, cs.started_at, cs.completed_at,
                   cs.cancel_requested_at, cs.deleted_at, cs.created_at,
                   cs.updated_at,
                   COUNT(DISTINCT c.id) AS cluster_count,
                   COUNT(DISTINCT c.id) FILTER (
                       WHERE COALESCE(c.manual_status, c.auto_status) <> 'rejected'
                   ) AS active_cluster_count,
                   COUNT(DISTINCT cm.message_pair_id) FILTER (
                       WHERE COALESCE(c.manual_status, c.auto_status) <> 'rejected'
                   ) AS active_message_pair_count
            FROM cluster_sets cs
            JOIN analysis_runs r
              ON r.id = cs.indexing_run_id AND r.project_id = cs.project_id
            JOIN dataset_versions d
              ON d.id = cs.dataset_version_id AND d.project_id = cs.project_id
            LEFT JOIN clusters c
              ON c.cluster_set_id = cs.id AND c.project_id = cs.project_id
            LEFT JOIN cluster_memberships cm
              ON cm.cluster_id = c.id
             AND cm.project_id = c.project_id
             AND cm.cluster_set_id = c.cluster_set_id
            WHERE cs.id = %s AND cs.project_id = %s AND cs.deleted_at IS NULL
            GROUP BY cs.id, d.display_name, r.deleted_at
            """,
            (cluster_set_id, project_id),
        ).fetchone()

    def _record_cluster_set_event(
        self,
        connection: Any,
        *,
        project_id: UUID,
        cluster_set_id: UUID,
        actor_user_id: UUID | None,
        event_type: str,
        metadata: dict[str, Any],
    ) -> None:
        connection.execute(
            """
            INSERT INTO cluster_set_events (
                id, project_id, cluster_set_id, event_type, actor_user_id,
                metadata
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                uuid4(),
                project_id,
                cluster_set_id,
                event_type,
                actor_user_id,
                Jsonb(metadata),
            ),
        )

    def _resolve_source_pair_ids(
        self,
        connection: Any,
        *,
        project_id: UUID,
        dataset_version_id: UUID,
        parent_cluster_set_id: UUID | None,
        source_cluster_ids: list[UUID],
        source_pair_ids: list[UUID],
    ) -> list[UUID] | None:
        selected: set[UUID] = set()
        if source_cluster_ids:
            if parent_cluster_set_id is None:
                raise ClusterError(
                    "source clusters require a parent Cluster-Set",
                    code="CLUSTER_REFINEMENT_EMPTY_SOURCE",
                    status_code=422,
                    field_errors={
                        "source_cluster_ids": (
                            "source clusters require a parent Cluster-Set"
                        )
                    },
                )
            requested_cluster_ids = set(source_cluster_ids)
            rows = connection.execute(
                """
                SELECT DISTINCT c.id AS cluster_id, cm.message_pair_id
                FROM clusters c
                JOIN cluster_memberships cm
                  ON cm.cluster_id = c.id
                 AND cm.project_id = c.project_id
                 AND cm.cluster_set_id = c.cluster_set_id
                JOIN message_pairs mp
                  ON mp.id = cm.message_pair_id
                 AND mp.project_id = cm.project_id
                WHERE c.project_id = %s
                  AND c.cluster_set_id = %s
                  AND mp.dataset_version_id = %s
                  AND c.id = ANY(%s)
                  AND COALESCE(c.manual_status, c.auto_status) <> 'rejected'
                """,
                (
                    project_id,
                    parent_cluster_set_id,
                    dataset_version_id,
                    source_cluster_ids,
                ),
            ).fetchall()
            returned_cluster_ids = {UUID(str(row["cluster_id"])) for row in rows}
            if returned_cluster_ids != requested_cluster_ids:
                raise ClusterError(
                    "source clusters contain rows outside the parent Cluster-Set",
                    code="CLUSTER_REFINEMENT_EMPTY_SOURCE",
                    status_code=422,
                    field_errors={
                        "source_cluster_ids": (
                            "source clusters must belong to the parent Cluster-Set"
                        )
                    },
                )
            selected.update(UUID(str(row["message_pair_id"])) for row in rows)
        if source_pair_ids:
            requested_pair_ids = set(source_pair_ids)
            if parent_cluster_set_id is None:
                rows = connection.execute(
                    """
                    SELECT id
                    FROM message_pairs
                    WHERE project_id = %s
                      AND dataset_version_id = %s
                      AND id = ANY(%s)
                    """,
                    (project_id, dataset_version_id, source_pair_ids),
                ).fetchall()
                returned_pair_ids = {UUID(str(row["id"])) for row in rows}
            else:
                rows = connection.execute(
                    """
                    SELECT DISTINCT cm.message_pair_id
                    FROM cluster_memberships cm
                    JOIN message_pairs mp
                      ON mp.id = cm.message_pair_id
                     AND mp.project_id = cm.project_id
                    JOIN clusters c
                      ON c.id = cm.cluster_id
                     AND c.project_id = cm.project_id
                     AND c.cluster_set_id = cm.cluster_set_id
                    WHERE cm.project_id = %s
                      AND cm.cluster_set_id = %s
                      AND mp.dataset_version_id = %s
                      AND cm.message_pair_id = ANY(%s)
                      AND COALESCE(c.manual_status, c.auto_status) <> 'rejected'
                    """,
                    (
                        project_id,
                        parent_cluster_set_id,
                        dataset_version_id,
                        source_pair_ids,
                    ),
                ).fetchall()
                returned_pair_ids = {UUID(str(row["message_pair_id"])) for row in rows}
            if returned_pair_ids != requested_pair_ids:
                raise ClusterError(
                    "refinement source contains rows outside the parent Cluster-Set",
                    code="CLUSTER_REFINEMENT_EMPTY_SOURCE",
                    status_code=422,
                    field_errors={
                        "source_pair_ids": (
                            "source pairs must belong to the parent Cluster-Set"
                        )
                    },
                )
            selected.update(returned_pair_ids)
        if source_cluster_ids or source_pair_ids:
            if not selected:
                raise ClusterError(
                    "refinement source contains no usable rows",
                    code="CLUSTER_REFINEMENT_EMPTY_SOURCE",
                    status_code=422,
                )
            return sorted(selected, key=str)
        return None

    def _source_snapshot(
        self,
        connection: Any,
        *,
        project_id: UUID,
        dataset_version_id: UUID,
        parent_cluster_set_id: UUID | None,
        source_cluster_ids: list[UUID],
        selected_pair_ids: list[UUID] | None,
        refinement_mode: str = "common",
    ) -> dict[str, Any]:
        if selected_pair_ids is not None:
            return {
                "type": "selected_pairs",
                "refinement_mode": refinement_mode,
                "parent_cluster_set_id": (
                    str(parent_cluster_set_id)
                    if parent_cluster_set_id is not None
                    else None
                ),
                "source_cluster_ids": [str(item) for item in source_cluster_ids],
                "source_pair_ids": [str(item) for item in selected_pair_ids],
                "source_pair_count": len(selected_pair_ids),
            }
        row = connection.execute(
            """
            SELECT COUNT(id) AS record_count
            FROM message_pairs
            WHERE project_id = %s AND dataset_version_id = %s
            """,
            (project_id, dataset_version_id),
        ).fetchone()
        record_count = int(str(row["record_count"])) if row is not None else 0
        if record_count < 1:
            raise ClusterError(
                "refinement source contains no usable rows",
                code="CLUSTER_REFINEMENT_EMPTY_SOURCE",
                status_code=422,
            )
        return {
            "type": "all_dataset_pairs",
            "dataset_version_id": str(dataset_version_id),
            "source_pair_count": record_count,
        }

    def _snapshot_pair_ids(self, source_snapshot: dict[str, Any]) -> list[UUID] | None:
        if source_snapshot.get("type") != "selected_pairs":
            return None
        raw_ids = source_snapshot.get("source_pair_ids")
        if not isinstance(raw_ids, list):
            raise ClusterError(
                "Cluster-Set source snapshot is invalid",
                code="CLUSTER_SET_LINEAGE_UNAVAILABLE",
                status_code=503,
            )
        try:
            return [UUID(str(item)) for item in raw_ids]
        except (TypeError, ValueError) as exc:
            raise ClusterError(
                "Cluster-Set source snapshot is invalid",
                code="CLUSTER_SET_LINEAGE_UNAVAILABLE",
                status_code=503,
            ) from exc

    def _snapshot_refinement_mode(self, source_snapshot: dict[str, Any]) -> str:
        value = source_snapshot.get("refinement_mode", "common")
        if not isinstance(value, str):
            return "common"
        return value.strip().lower().replace("-", "_")

    def _snapshot_source_cluster_ids(
        self, source_snapshot: dict[str, Any]
    ) -> list[UUID]:
        raw_ids = source_snapshot.get("source_cluster_ids")
        if not isinstance(raw_ids, list):
            return []
        try:
            return [UUID(str(item)) for item in raw_ids]
        except (TypeError, ValueError) as exc:
            raise ClusterError(
                "Cluster-Set source snapshot is invalid",
                code="CLUSTER_SET_LINEAGE_UNAVAILABLE",
                status_code=503,
            ) from exc

    def _per_parent_refinement_groups(
        self,
        connection: Any,
        *,
        project_id: UUID,
        parent_cluster_set_id: UUID,
        dataset_version_id: UUID,
        source_cluster_ids: list[UUID],
    ) -> list[BatchRefinementGroup]:
        if not source_cluster_ids:
            raise ClusterError(
                "per-parent refinement requires selected parent clusters",
                code="CLUSTER_BATCH_REFINEMENT_EMPTY_GROUP",
                status_code=422,
                field_errors={
                    "source_cluster_ids": (
                        "per-parent refinement requires selected parent clusters"
                    )
                },
            )
        if len(source_cluster_ids) > MAX_PER_PARENT_REFINEMENT_GROUPS:
            raise ClusterError(
                "per-parent refinement selects too many parent clusters",
                code="CLUSTER_BATCH_REFINEMENT_EMPTY_GROUP",
                status_code=422,
                retryable=True,
                suggested_action="select-sources",
                field_errors={
                    "source_cluster_ids": (
                        "per-parent refinement selects too many parent clusters"
                    )
                },
            )
        rows = connection.execute(
            """
            SELECT c.id AS cluster_id,
                   COALESCE(c.manual_title, c.auto_title) AS title,
                   c.metadata,
                   c.is_outlier,
                   mp.id AS message_pair_id
            FROM clusters c
            LEFT JOIN cluster_memberships cm
              ON cm.cluster_id = c.id
             AND cm.project_id = c.project_id
             AND cm.cluster_set_id = c.cluster_set_id
            LEFT JOIN message_pairs mp
              ON mp.id = cm.message_pair_id
             AND mp.project_id = cm.project_id
            WHERE c.project_id = %s
              AND c.cluster_set_id = %s
              AND c.id = ANY(%s)
              AND COALESCE(c.manual_status, c.auto_status) <> 'rejected'
              AND (mp.id IS NULL OR mp.dataset_version_id = %s)
            ORDER BY array_position(%s::uuid[], c.id), mp.ordinal ASC
            """,
            (
                project_id,
                parent_cluster_set_id,
                source_cluster_ids,
                dataset_version_id,
                source_cluster_ids,
            ),
        ).fetchall()
        by_cluster: dict[UUID, BatchRefinementGroup] = {}
        pairs_by_cluster: dict[UUID, list[UUID]] = {}
        for row in rows:
            cluster_id = UUID(str(row["cluster_id"]))
            metadata = row["metadata"]
            label_value: int | None = None
            if isinstance(metadata, dict):
                raw_label = metadata.get("label")
                if isinstance(raw_label, int):
                    label_value = raw_label
            if cluster_id not in by_cluster:
                title = str(row["title"])[:MAX_CLUSTER_ORIGIN_TITLE_LENGTH]
                by_cluster[cluster_id] = BatchRefinementGroup(
                    cluster_id=cluster_id,
                    title=title,
                    label=label_value,
                    is_outlier=bool(row["is_outlier"]),
                    pair_ids=[],
                )
                pairs_by_cluster[cluster_id] = []
            pair_id = row["message_pair_id"]
            if pair_id is not None:
                pairs_by_cluster[cluster_id].append(UUID(str(pair_id)))
        if set(by_cluster) != set(source_cluster_ids):
            raise ClusterError(
                "per-parent refinement contains unavailable parent clusters",
                code="CLUSTER_BATCH_REFINEMENT_EMPTY_GROUP",
                status_code=422,
                field_errors={
                    "source_cluster_ids": (
                        "selected parent clusters must belong to the parent Cluster-Set"
                    )
                },
            )
        groups: list[BatchRefinementGroup] = []
        for cluster_id in source_cluster_ids:
            group = by_cluster[cluster_id]
            pair_ids = list(dict.fromkeys(pairs_by_cluster[cluster_id]))
            if not pair_ids:
                raise ClusterError(
                    "per-parent refinement group contains no usable rows",
                    code="CLUSTER_BATCH_REFINEMENT_EMPTY_GROUP",
                    status_code=422,
                    field_errors={
                        "source_cluster_ids": (
                            "selected parent cluster contains no usable rows"
                        )
                    },
                )
            groups.append(
                BatchRefinementGroup(
                    cluster_id=group.cluster_id,
                    title=group.title,
                    label=group.label,
                    is_outlier=group.is_outlier,
                    pair_ids=pair_ids,
                )
            )
        return groups

    def _cluster_set_input_summary(
        self,
        connection: Any,
        *,
        project_id: UUID,
        indexing_run_id: UUID,
        dataset_version_id: UUID,
        source_pair_ids: list[UUID] | None,
    ) -> dict[str, object]:
        params: list[object] = [
            indexing_run_id,
            indexing_run_id,
            project_id,
            dataset_version_id,
        ]
        query = """
            SELECT COUNT(mp.id) AS record_count,
                   COUNT(em.id) AS message_embedding_count,
                   COUNT(ea.id) AS answer_embedding_count,
                   MIN(em.dimensions) AS message_minimum_dimensions,
                   MAX(em.dimensions) AS message_maximum_dimensions,
                   MIN(ea.dimensions) AS answer_minimum_dimensions,
                   MAX(ea.dimensions) AS answer_maximum_dimensions
            FROM message_pairs mp
            LEFT JOIN embeddings em
              ON em.project_id = mp.project_id
             AND em.analysis_run_id = %s
             AND em.dataset_version_id = mp.dataset_version_id
             AND em.source_object_type = 'message_pair'
             AND em.source_object_id = mp.id
             AND em.text_variant = 'message'
            LEFT JOIN embeddings ea
              ON ea.project_id = mp.project_id
             AND ea.analysis_run_id = %s
             AND ea.dataset_version_id = mp.dataset_version_id
             AND ea.source_object_type = 'message_pair'
             AND ea.source_object_id = mp.id
             AND ea.text_variant = 'answer'
            WHERE mp.project_id = %s AND mp.dataset_version_id = %s
            """
        if source_pair_ids is not None:
            query = """
            SELECT COUNT(mp.id) AS record_count,
                   COUNT(em.id) AS message_embedding_count,
                   COUNT(ea.id) AS answer_embedding_count,
                   MIN(em.dimensions) AS message_minimum_dimensions,
                   MAX(em.dimensions) AS message_maximum_dimensions,
                   MIN(ea.dimensions) AS answer_minimum_dimensions,
                   MAX(ea.dimensions) AS answer_maximum_dimensions
            FROM message_pairs mp
            LEFT JOIN embeddings em
              ON em.project_id = mp.project_id
             AND em.analysis_run_id = %s
             AND em.dataset_version_id = mp.dataset_version_id
             AND em.source_object_type = 'message_pair'
             AND em.source_object_id = mp.id
             AND em.text_variant = 'message'
            LEFT JOIN embeddings ea
              ON ea.project_id = mp.project_id
             AND ea.analysis_run_id = %s
             AND ea.dataset_version_id = mp.dataset_version_id
             AND ea.source_object_type = 'message_pair'
             AND ea.source_object_id = mp.id
             AND ea.text_variant = 'answer'
            WHERE mp.project_id = %s
              AND mp.dataset_version_id = %s
              AND mp.id = ANY(%s)
            """
            params.append(source_pair_ids)
        row = connection.execute(query, tuple(params)).fetchone()
        if row is None:
            raise ClusterError(
                "Cluster-Set embedding summary is unavailable",
                code="CLUSTER_VECTOR_BASIS_UNAVAILABLE",
                status_code=422,
            )
        return dict(row)

    def _validate_cluster_set_basis_budget(
        self,
        config: AlgorithmConfiguration,
        *,
        vector_basis: str,
        input_summary: dict[str, object],
    ) -> ClusterSetBasisBudget:
        record_count = int(str(input_summary["record_count"]))
        message_count = int(str(input_summary["message_embedding_count"]))
        answer_count = int(str(input_summary["answer_embedding_count"]))
        message_dimensions: int | None = None
        answer_dimensions: int | None = None
        if vector_basis == "message":
            embedding_count = message_count
            minimum_dimensions = input_summary["message_minimum_dimensions"]
            maximum_dimensions = input_summary["message_maximum_dimensions"]
            if minimum_dimensions is not None and maximum_dimensions is not None:
                message_dimensions = int(str(minimum_dimensions))
        elif vector_basis == "answer":
            embedding_count = answer_count
            minimum_dimensions = input_summary["answer_minimum_dimensions"]
            maximum_dimensions = input_summary["answer_maximum_dimensions"]
            if minimum_dimensions is not None and maximum_dimensions is not None:
                answer_dimensions = int(str(minimum_dimensions))
        else:
            if message_count != record_count or answer_count != record_count:
                raise ClusterError(
                    "combined vector basis has missing embeddings",
                    code="CLUSTER_VECTOR_BASIS_UNAVAILABLE",
                    status_code=422,
                )
            message_min = input_summary["message_minimum_dimensions"]
            message_max = input_summary["message_maximum_dimensions"]
            answer_min = input_summary["answer_minimum_dimensions"]
            answer_max = input_summary["answer_maximum_dimensions"]
            if (
                message_min is None
                or message_max is None
                or answer_min is None
                or answer_max is None
                or int(str(message_min)) != int(str(message_max))
                or int(str(answer_min)) != int(str(answer_max))
            ):
                raise ClusterError(
                    "combined vector basis has inconsistent embedding dimensions",
                    code="CLUSTER_VECTOR_BASIS_UNAVAILABLE",
                    status_code=422,
                )
            message_dimensions = int(str(message_min))
            answer_dimensions = int(str(answer_min))
            embedding_count = record_count
            minimum_dimensions = message_dimensions + answer_dimensions
            maximum_dimensions = minimum_dimensions
        try:
            output_dimensions = validate_cluster_input_budget(
                config,
                record_count=record_count,
                embedding_count=embedding_count,
                minimum_dimensions=(
                    int(str(minimum_dimensions))
                    if minimum_dimensions is not None
                    else None
                ),
                maximum_dimensions=(
                    int(str(maximum_dimensions))
                    if maximum_dimensions is not None
                    else None
                ),
            )
            return ClusterSetBasisBudget(
                output_dimensions=output_dimensions,
                message_dimensions=message_dimensions,
                answer_dimensions=answer_dimensions,
            )
        except ClusterError as exc:
            if "working set" in str(exc) or "supports at most" in str(exc):
                raise ClusterError(
                    str(exc),
                    code="CLUSTER_BUDGET_EXCEEDED",
                    status_code=422,
                ) from exc
            raise ClusterError(
                str(exc),
                code="CLUSTER_VECTOR_BASIS_UNAVAILABLE",
                status_code=422,
            ) from exc

    def _publish_cluster_set_progress(
        self, cluster_set_id: UUID, progress: int, phase: str
    ) -> None:
        with open_database_connection(self._settings) as connection:
            with connection.transaction():
                connection.execute(
                    """
                    UPDATE cluster_sets
                    SET progress = %s, phase = %s, updated_at = now()
                    WHERE id = %s
                      AND status = 'running'
                      AND progress < %s
                    """,
                    (progress, phase, cluster_set_id, progress),
                )

    def _raise_if_cluster_set_cancelled(
        self, connection: Any, cluster_set_id: UUID
    ) -> None:
        row = connection.execute(
            """
            SELECT status
            FROM cluster_sets
            WHERE id = %s
            """,
            (cluster_set_id,),
        ).fetchone()
        if row is not None and row["status"] in {"cancelling", "cancelled"}:
            raise ClusterSetCancelled()

    def _load_native_embedding_matrix(
        self,
        connection: Any,
        *,
        project_id: UUID,
        run_id: UUID,
        dataset_version_id: UUID,
        record_limit: int,
        expected_record_count: int,
        expected_dimensions: int,
    ) -> tuple[list[object], np.ndarray[Any, np.dtype[np.float32]]]:
        pair_ids: list[object] = []
        seen_pair_ids: set[object] = set()
        vectors = np.empty(
            (expected_record_count, expected_dimensions),
            dtype=np.float32,
            order="C",
        )
        loaded = 0
        with connection.cursor(
            name=f"cluster_vectors_{run_id.hex}",
            binary=True,
        ) as cursor:
            cursor.execute(
                """
                SELECT mp.id AS message_pair_id, e.embedding, e.dimensions
                FROM message_pairs mp
                LEFT JOIN embeddings e
                  ON e.project_id = mp.project_id
                 AND e.analysis_run_id = %s
                 AND e.dataset_version_id = mp.dataset_version_id
                 AND e.source_object_type = 'message_pair'
                 AND e.source_object_id = mp.id
                 AND e.text_variant = 'message'
                WHERE mp.project_id = %s AND mp.dataset_version_id = %s
                ORDER BY mp.ordinal ASC
                LIMIT %s
                """,
                (
                    run_id,
                    project_id,
                    dataset_version_id,
                    record_limit + 1,
                ),
            )
            while rows := cursor.fetchmany(NATIVE_VECTOR_FETCH_BATCH_SIZE):
                for row in rows:
                    if loaded >= expected_record_count:
                        raise ClusterError(
                            "analysis run embedding summary changed during clustering"
                        )
                    embedding = row["embedding"]
                    if embedding is None:
                        raise ClusterError(
                            "analysis run has missing message embeddings"
                        )
                    if not isinstance(embedding, Vector):
                        raise ClusterError("run contains a non-native embedding vector")
                    pair_id = row["message_pair_id"]
                    if pair_id in seen_pair_ids:
                        raise ClusterError(
                            "analysis run has duplicate message embeddings"
                        )
                    seen_pair_ids.add(pair_id)
                    try:
                        declared_dimensions = int(str(row["dimensions"]))
                    except (TypeError, ValueError) as exc:
                        raise ClusterError(
                            "embedding dimensionality metadata is invalid"
                        ) from exc
                    if (
                        declared_dimensions < 1
                        or declared_dimensions > MAX_CLUSTER_DIMENSIONS
                    ):
                        raise ClusterError(
                            "embedding dimensionality is outside safe limits"
                        )
                    native_vector = embedding.to_numpy()
                    if (
                        native_vector.ndim != 1
                        or native_vector.shape[0] != declared_dimensions
                    ):
                        raise ClusterError(
                            "embedding dimensionality does not match metadata"
                        )
                    if declared_dimensions != expected_dimensions:
                        raise ClusterError(
                            "analysis run has inconsistent embedding dimensions"
                        )
                    if not np.isfinite(native_vector).all():
                        raise ClusterError("run contains a non-finite embedding vector")
                    pair_ids.append(pair_id)
                    vectors[loaded] = native_vector
                    loaded += 1
        if loaded != expected_record_count:
            raise ClusterError(
                "analysis run embedding summary changed during clustering"
            )
        return pair_ids, vectors

    def _load_cluster_set_embedding_matrix(
        self,
        connection: Any,
        *,
        project_id: UUID,
        indexing_run_id: UUID,
        dataset_version_id: UUID,
        vector_basis: str,
        message_weight: float,
        answer_weight: float,
        source_pair_ids: list[UUID] | None,
        record_limit: int,
        expected_record_count: int,
        expected_dimensions: int,
        message_expected_dimensions: int | None,
        answer_expected_dimensions: int | None,
    ) -> tuple[
        list[object], np.ndarray[Any, np.dtype[np.float32]], dict[object, float]
    ]:
        pair_ids: list[object] = []
        seen_pair_ids: set[object] = set()
        mismatch_scores: dict[object, float] = {}
        vectors = np.empty(
            (expected_record_count, expected_dimensions),
            dtype=np.float32,
            order="C",
        )
        params: list[object] = [
            indexing_run_id,
            indexing_run_id,
            project_id,
            dataset_version_id,
            record_limit + 1,
        ]
        query = """
                SELECT mp.id AS message_pair_id,
                       em.embedding AS message_embedding,
                       em.dimensions AS message_dimensions,
                       ea.embedding AS answer_embedding,
                       ea.dimensions AS answer_dimensions
                FROM message_pairs mp
                LEFT JOIN embeddings em
                  ON em.project_id = mp.project_id
                 AND em.analysis_run_id = %s
                 AND em.dataset_version_id = mp.dataset_version_id
                 AND em.source_object_type = 'message_pair'
                 AND em.source_object_id = mp.id
                 AND em.text_variant = 'message'
                LEFT JOIN embeddings ea
                  ON ea.project_id = mp.project_id
                 AND ea.analysis_run_id = %s
                 AND ea.dataset_version_id = mp.dataset_version_id
                 AND ea.source_object_type = 'message_pair'
                 AND ea.source_object_id = mp.id
                 AND ea.text_variant = 'answer'
                WHERE mp.project_id = %s AND mp.dataset_version_id = %s
                ORDER BY mp.ordinal ASC
                LIMIT %s
                """
        if source_pair_ids is not None:
            query = """
                SELECT mp.id AS message_pair_id,
                       em.embedding AS message_embedding,
                       em.dimensions AS message_dimensions,
                       ea.embedding AS answer_embedding,
                       ea.dimensions AS answer_dimensions
                FROM message_pairs mp
                LEFT JOIN embeddings em
                  ON em.project_id = mp.project_id
                 AND em.analysis_run_id = %s
                 AND em.dataset_version_id = mp.dataset_version_id
                 AND em.source_object_type = 'message_pair'
                 AND em.source_object_id = mp.id
                 AND em.text_variant = 'message'
                LEFT JOIN embeddings ea
                  ON ea.project_id = mp.project_id
                 AND ea.analysis_run_id = %s
                 AND ea.dataset_version_id = mp.dataset_version_id
                 AND ea.source_object_type = 'message_pair'
                 AND ea.source_object_id = mp.id
                 AND ea.text_variant = 'answer'
                WHERE mp.project_id = %s
                  AND mp.dataset_version_id = %s
                  AND mp.id = ANY(%s)
                ORDER BY mp.ordinal ASC
                LIMIT %s
                """
            params.insert(4, source_pair_ids)
        loaded = 0
        with connection.cursor(
            name=f"cluster_set_vectors_{indexing_run_id.hex}",
            binary=True,
        ) as cursor:
            cursor.execute(query, tuple(params))
            while rows := cursor.fetchmany(NATIVE_VECTOR_FETCH_BATCH_SIZE):
                for row in rows:
                    if loaded >= expected_record_count:
                        raise ClusterError(
                            "Cluster-Set embedding summary changed during clustering",
                            code="CLUSTER_VECTOR_BASIS_UNAVAILABLE",
                            status_code=422,
                        )
                    pair_id = row["message_pair_id"]
                    if pair_id in seen_pair_ids:
                        raise ClusterError(
                            "Cluster-Set has duplicate embeddings",
                            code="CLUSTER_VECTOR_BASIS_UNAVAILABLE",
                            status_code=422,
                        )
                    seen_pair_ids.add(pair_id)
                    message_vector = self._native_vector_from_row(
                        row,
                        "message",
                        expected_dimensions=message_expected_dimensions,
                        required=vector_basis in {"message", "combined"},
                    )
                    answer_vector = self._native_vector_from_row(
                        row,
                        "answer",
                        expected_dimensions=answer_expected_dimensions,
                        required=vector_basis in {"answer", "combined"},
                    )
                    if (
                        message_vector is not None
                        and answer_vector is not None
                        and message_vector.shape == answer_vector.shape
                    ):
                        mismatch_scores[pair_id] = self._cosine_distance(
                            message_vector, answer_vector
                        )
                    if vector_basis == "message":
                        if message_vector is None:
                            raise ClusterError(
                                "message vector basis has missing embeddings",
                                code="CLUSTER_VECTOR_BASIS_UNAVAILABLE",
                                status_code=422,
                            )
                        vector = self._normalized_vector(message_vector)
                    elif vector_basis == "answer":
                        if answer_vector is None:
                            raise ClusterError(
                                "answer vector basis has missing embeddings",
                                code="CLUSTER_VECTOR_BASIS_UNAVAILABLE",
                                status_code=422,
                            )
                        vector = self._normalized_vector(answer_vector)
                    else:
                        if message_vector is None or answer_vector is None:
                            raise ClusterError(
                                "combined vector basis has missing embeddings",
                                code="CLUSTER_VECTOR_BASIS_UNAVAILABLE",
                                status_code=422,
                            )
                        vector = np.concatenate(
                            (
                                self._normalized_vector(message_vector)
                                * message_weight,
                                self._normalized_vector(answer_vector) * answer_weight,
                            )
                        )
                    if not np.isfinite(vector).all():
                        raise ClusterError(
                            "Cluster-Set contains a non-finite vector",
                            code="CLUSTER_VECTOR_BASIS_UNAVAILABLE",
                            status_code=422,
                        )
                    pair_ids.append(pair_id)
                    vectors[loaded] = vector.astype(np.float32, copy=False)
                    loaded += 1
        if loaded != expected_record_count:
            raise ClusterError(
                "Cluster-Set embedding summary changed during clustering",
                code="CLUSTER_VECTOR_BASIS_UNAVAILABLE",
                status_code=422,
            )
        return pair_ids, vectors, mismatch_scores

    def _native_vector_from_row(
        self,
        row: dict[str, object],
        prefix: str,
        *,
        expected_dimensions: int | None,
        required: bool,
    ) -> np.ndarray[Any, np.dtype[np.float32]] | None:
        embedding = row[f"{prefix}_embedding"]
        dimensions = row[f"{prefix}_dimensions"]
        if embedding is None:
            if required:
                raise ClusterError(
                    f"{prefix} vector basis has missing embeddings",
                    code="CLUSTER_VECTOR_BASIS_UNAVAILABLE",
                    status_code=422,
                )
            return None
        if not isinstance(embedding, Vector):
            raise ClusterError(
                "Cluster-Set contains a non-native embedding vector",
                code="CLUSTER_VECTOR_BASIS_UNAVAILABLE",
                status_code=422,
            )
        try:
            declared_dimensions = int(str(dimensions))
        except (TypeError, ValueError) as exc:
            raise ClusterError(
                "embedding dimensionality metadata is invalid",
                code="CLUSTER_VECTOR_BASIS_UNAVAILABLE",
                status_code=422,
            ) from exc
        if (
            expected_dimensions is not None
            and declared_dimensions != expected_dimensions
        ):
            raise ClusterError(
                "Cluster-Set has inconsistent embedding dimensions",
                code="CLUSTER_VECTOR_BASIS_UNAVAILABLE",
                status_code=422,
            )
        native_vector = embedding.to_numpy()
        if native_vector.ndim != 1:
            raise ClusterError(
                "embedding dimensionality does not match metadata",
                code="CLUSTER_VECTOR_BASIS_UNAVAILABLE",
                status_code=422,
            )
        if (
            expected_dimensions is not None
            and native_vector.shape[0] != expected_dimensions
        ):
            raise ClusterError(
                "embedding dimensionality does not match metadata",
                code="CLUSTER_VECTOR_BASIS_UNAVAILABLE",
                status_code=422,
            )
        if native_vector.shape[0] != declared_dimensions:
            raise ClusterError(
                "embedding dimensionality does not match metadata",
                code="CLUSTER_VECTOR_BASIS_UNAVAILABLE",
                status_code=422,
            )
        if not np.isfinite(native_vector).all():
            raise ClusterError(
                "Cluster-Set contains a non-finite embedding vector",
                code="CLUSTER_VECTOR_BASIS_UNAVAILABLE",
                status_code=422,
            )
        return native_vector.astype(np.float32, copy=False)

    def _normalized_vector(
        self, vector: np.ndarray[Any, np.dtype[np.float32]]
    ) -> np.ndarray[Any, np.dtype[np.float32]]:
        norm = float(np.linalg.norm(vector))
        if not math.isfinite(norm):
            raise ClusterError(
                "Cluster-Set contains a non-finite embedding vector",
                code="CLUSTER_VECTOR_BASIS_UNAVAILABLE",
                status_code=422,
            )
        if norm == 0:
            return vector
        return (vector / norm).astype(np.float32, copy=False)

    def _cosine_distance(
        self,
        left: np.ndarray[Any, np.dtype[np.float32]],
        right: np.ndarray[Any, np.dtype[np.float32]],
    ) -> float:
        left_norm = float(np.linalg.norm(left))
        right_norm = float(np.linalg.norm(right))
        if left_norm == 0 and right_norm == 0:
            return 0.0
        if left_norm == 0 or right_norm == 0:
            return 1.0
        similarity = float(np.dot(left, right) / (left_norm * right_norm))
        if not math.isfinite(similarity):
            return 1.0
        return max(0.0, min(2.0, 1.0 - similarity))

    def _reduce_hdbscan_vectors(
        self,
        config: AlgorithmConfiguration,
        vectors: np.ndarray[Any, np.dtype[np.float32]],
    ) -> np.ndarray[Any, np.dtype[np.float32]]:
        method = str(config.parameters.get("reduction_method") or "none")
        if method == "none" or len(vectors) <= 2:
            return vectors
        requested_dimensions = cast(int, config.parameters["reduction_dimensions"])
        target_dimensions = min(
            requested_dimensions, vectors.shape[1], len(vectors) - 1
        )
        if target_dimensions < 2 or target_dimensions >= vectors.shape[1]:
            return vectors
        if method == "pca":
            reduced = PCA(
                n_components=target_dimensions,
                random_state=42,
            ).fit_transform(vectors)
            return np.ascontiguousarray(reduced, dtype=np.float32)
        if method == "umap":
            return self._reduce_hdbscan_vectors_with_umap(
                config, vectors, target_dimensions=target_dimensions
            )
        raise ClusterError(
            "reduction method is unavailable",
            code="CLUSTER_REDUCTION_UNAVAILABLE",
            status_code=422,
            retryable=True,
            field_errors={"reduction_method": "reduction method is unavailable"},
        )

    def _reduce_hdbscan_vectors_with_umap(
        self,
        config: AlgorithmConfiguration,
        vectors: np.ndarray[Any, np.dtype[np.float32]],
        *,
        target_dimensions: int,
    ) -> np.ndarray[Any, np.dtype[np.float32]]:
        backend = str(config.parameters.get("execution_backend") or "auto")
        if backend in {"auto", "cuml"}:
            try:
                umap_class = getattr(importlib.import_module("cuml.manifold"), "UMAP")
                reducer = umap_class(
                    n_components=target_dimensions,
                    n_neighbors=min(
                        cast(int, config.parameters["umap_n_neighbors"]),
                        len(vectors) - 1,
                    ),
                    min_dist=cast(float, config.parameters["umap_min_dist"]),
                    metric="cosine",
                    random_state=42,
                    output_type="numpy",
                )
                return np.ascontiguousarray(
                    reducer.fit_transform(vectors),
                    dtype=np.float32,
                )
            except Exception as exc:
                if backend == "cuml":
                    raise ClusterError(
                        "cuML UMAP is unavailable",
                        code="CLUSTER_ACCELERATOR_UNAVAILABLE",
                        status_code=422,
                        retryable=True,
                        field_errors={
                            "execution_backend": (
                                "cuML UMAP is unavailable in this runtime"
                            )
                        },
                    ) from exc
                LOGGER.info("cuML UMAP unavailable, falling back to CPU UMAP")
        try:
            umap_module = importlib.import_module("umap")
            umap_class = getattr(umap_module, "UMAP")
        except (ImportError, AttributeError) as exc:
            raise ClusterError(
                "umap-learn is not installed",
                code="CLUSTER_REDUCTION_UNAVAILABLE",
                status_code=422,
                retryable=True,
                field_errors={
                    "reduction_method": (
                        "UMAP requires the optional umap-learn dependency"
                    )
                },
            ) from exc
        reducer = umap_class(
            n_components=target_dimensions,
            n_neighbors=min(
                cast(int, config.parameters["umap_n_neighbors"]),
                len(vectors) - 1,
            ),
            min_dist=cast(float, config.parameters["umap_min_dist"]),
            metric="cosine",
            random_state=42,
        )
        return np.ascontiguousarray(reducer.fit_transform(vectors), dtype=np.float32)

    def _fit_cpu_hdbscan(
        self,
        config: AlgorithmConfiguration,
        vectors: np.ndarray[Any, np.dtype[np.float32]],
    ) -> tuple[list[int], list[float]]:
        estimator = HDBSCAN(
            min_cluster_size=cast(int, config.parameters["min_cluster_size"]),
            min_samples=config.parameters["min_samples"],  # type: ignore[arg-type]
            cluster_selection_epsilon=cast(
                float, config.parameters["cluster_selection_epsilon"]
            ),
            n_jobs=HDBSCAN_N_JOBS,
            copy=False,
        )
        labels = estimator.fit_predict(vectors)
        probabilities = [float(value) for value in estimator.probabilities_]
        return [int(label) for label in labels], probabilities

    def _fit_cuml_hdbscan(
        self,
        config: AlgorithmConfiguration,
        vectors: np.ndarray[Any, np.dtype[np.float32]],
    ) -> tuple[list[int], list[float]]:
        try:
            hdbscan_class = getattr(importlib.import_module("cuml.cluster"), "HDBSCAN")
            estimator = hdbscan_class(
                min_cluster_size=cast(int, config.parameters["min_cluster_size"]),
                min_samples=config.parameters["min_samples"],
                cluster_selection_epsilon=cast(
                    float, config.parameters["cluster_selection_epsilon"]
                ),
                output_type="numpy",
            )
            labels = estimator.fit_predict(vectors)
            probabilities_attr = getattr(estimator, "probabilities_", None)
        except Exception as exc:
            raise ClusterError(
                "cuML HDBSCAN is unavailable",
                code="CLUSTER_ACCELERATOR_UNAVAILABLE",
                status_code=422,
                retryable=True,
                field_errors={
                    "execution_backend": "cuML HDBSCAN is unavailable in this runtime"
                },
            ) from exc
        normalized_labels = [int(label) for label in np.asarray(labels).tolist()]
        if probabilities_attr is None:
            probabilities = [1.0] * len(normalized_labels)
        else:
            probabilities = [
                float(value) for value in np.asarray(probabilities_attr).tolist()
            ]
        return normalized_labels, probabilities

    def _fit_hdbscan_vectors(
        self,
        config: AlgorithmConfiguration,
        vectors: np.ndarray[Any, np.dtype[np.float32]],
    ) -> tuple[list[int], list[float], dict[str, object]]:
        backend = str(config.parameters.get("execution_backend") or "auto")
        diagnostics: dict[str, object] = {
            "algorithm": "hdbscan",
            "reduction_method": str(
                config.parameters.get("reduction_method") or "none"
            ),
            "effective_dimensions": int(vectors.shape[1]),
            "execution_backend_requested": backend,
            "execution_backend_effective": backend,
            "execution_backend_fallback": False,
        }
        if backend == "cuml":
            labels, probabilities = self._fit_cuml_hdbscan(config, vectors)
            diagnostics["execution_backend_effective"] = "cuml"
            return labels, probabilities, diagnostics
        if backend == "auto":
            try:
                labels, probabilities = self._fit_cuml_hdbscan(config, vectors)
                diagnostics["execution_backend_effective"] = "cuml"
                return labels, probabilities, diagnostics
            except ClusterError:
                diagnostics["execution_backend_effective"] = "cpu"
                diagnostics["execution_backend_fallback"] = True
                LOGGER.info("cuML HDBSCAN unavailable, falling back to CPU HDBSCAN")
                labels, probabilities = self._fit_cpu_hdbscan(config, vectors)
                return labels, probabilities, diagnostics
        labels, probabilities = self._fit_cpu_hdbscan(config, vectors)
        diagnostics["execution_backend_effective"] = "cpu"
        return labels, probabilities, diagnostics

    def _cluster_vectors(
        self,
        config: AlgorithmConfiguration,
        vectors: np.ndarray[Any, np.dtype[np.float32]],
    ) -> tuple[list[int], list[float]]:
        outlier_threshold = cast(
            float | None, config.parameters.get("outlier_threshold")
        )
        if config.name == "hdbscan":
            reduced_vectors = self._reduce_hdbscan_vectors(config, vectors)
            normalized_labels, probabilities, _diagnostics = self._fit_hdbscan_vectors(
                config, reduced_vectors
            )
            return (
                _apply_outlier_threshold(
                    normalized_labels, probabilities, outlier_threshold
                ),
                probabilities,
            )

        n_clusters = config.parameters["n_clusters"]
        if isinstance(n_clusters, int) and n_clusters > len(vectors):
            raise ClusterError("n_clusters cannot exceed the number of records")
        if len(vectors) == 1:
            return [0], [1.0]
        with config_context(
            working_memory=AGGLOMERATIVE_NEIGHBOR_WORKING_BYTES // (1024 * 1024)
        ):
            connectivity = kneighbors_graph(
                vectors,
                n_neighbors=min(AGGLOMERATIVE_NEIGHBOR_COUNT, len(vectors) - 1),
                include_self=False,
            )
        component_count = connected_components(
            connectivity,
            directed=False,
            return_labels=False,
        )
        if component_count != 1:
            raise ClusterError(
                "agglomerative neighbor graph has "
                f"{component_count} disconnected components; "
                "select HDBSCAN or adjust the dataset"
            )
        estimator = AgglomerativeClustering(
            n_clusters=n_clusters,  # type: ignore[arg-type]
            distance_threshold=config.parameters["distance_threshold"],  # type: ignore[arg-type]
            linkage=str(config.parameters["linkage"]),
            connectivity=connectivity,
        )
        labels = estimator.fit_predict(vectors)
        normalized_labels = [int(label) for label in labels]
        probabilities = [1.0] * len(vectors)
        return (
            _apply_outlier_threshold(
                normalized_labels, probabilities, outlier_threshold
            ),
            probabilities,
        )

    def _insert_cluster_set_clusters(
        self,
        connection: Any,
        *,
        project_id: UUID,
        cluster_set_id: UUID,
        indexing_run_id: UUID,
        dataset_version_id: UUID,
        embedding_provider: str,
        embedding_model: str,
        config: AlgorithmConfiguration,
        pair_ids: list[object],
        labels: list[int],
        probabilities: list[float],
        mismatch_scores: dict[object, float],
        expected_dimensions: int,
        vector_basis: str,
        message_weight: float,
        answer_weight: float,
        origin_by_pair_id: dict[object, ClusterOrigin] | None = None,
    ) -> None:
        grouped: dict[tuple[int | None, int], list[tuple[object, float]]] = {}
        for pair_id, label, probability in zip(
            pair_ids, labels, probabilities, strict=True
        ):
            origin = origin_by_pair_id.get(pair_id) if origin_by_pair_id else None
            grouped.setdefault(
                (origin.batch_group_index if origin is not None else None, int(label)),
                [],
            ).append((pair_id, probability))

        for group_key in sorted(grouped):
            _group_index, label = group_key
            members = grouped[group_key]
            first_origin = (
                origin_by_pair_id.get(members[0][0]) if origin_by_pair_id else None
            )
            local_label = first_origin.local_cluster_label if first_origin else label
            is_outlier = local_label == -1
            cluster_id = uuid4()
            title = (
                f"{first_origin.source_parent_cluster_title} · Outliers"
                if is_outlier and first_origin is not None
                else (
                    f"{first_origin.source_parent_cluster_title} · Cluster {local_label + 1}"
                    if first_origin is not None
                    else ("Outliers" if is_outlier else f"Cluster {label + 1}")
                )
            )
            status = "outlier" if is_outlier else "unreviewed"
            score = sum(item[1] for item in members) / len(members)
            qa_scores = [
                mismatch_scores[pair_id]
                for pair_id, _ in members
                if pair_id in mismatch_scores
            ]
            qa_metadata: dict[str, float] = {}
            if qa_scores:
                qa_metadata = {
                    "average": sum(qa_scores) / len(qa_scores),
                    "maximum": max(qa_scores),
                }
            connection.execute(
                """
                INSERT INTO clusters (
                    id, project_id, analysis_run_id, dataset_version_id,
                    cluster_set_id, auto_title, auto_category, auto_status,
                    score, is_outlier, algorithm, metadata
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    cluster_id,
                    project_id,
                    indexing_run_id,
                    dataset_version_id,
                    cluster_set_id,
                    title,
                    "outlier" if is_outlier else config.name,
                    status,
                    score,
                    is_outlier,
                    config.name,
                    Jsonb(
                        {
                            "label": label,
                            "parameters": config.parameters,
                            "provider": embedding_provider,
                            "model": embedding_model,
                            "dimensions": expected_dimensions,
                            "vector_basis": vector_basis,
                            "message_weight": message_weight,
                            "answer_weight": answer_weight,
                            "qa_mismatch": qa_metadata,
                            "non_quadratic": True,
                            **(
                                {"refinement": first_origin.as_metadata()}
                                if first_origin is not None
                                else {}
                            ),
                        }
                    ),
                ),
            )
            for pair_id, membership_score in members:
                connection.execute(
                    """
                    INSERT INTO cluster_memberships (
                        id, project_id, cluster_id, analysis_run_id,
                        cluster_set_id, message_pair_id, membership_score,
                        is_outlier, assignment_type, metadata
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'automatic', %s)
                    """,
                    (
                        uuid4(),
                        project_id,
                        cluster_id,
                        indexing_run_id,
                        cluster_set_id,
                        pair_id,
                        membership_score,
                        is_outlier,
                        Jsonb(
                            {"question_answer_mismatch": mismatch_scores.get(pair_id)}
                        ),
                    ),
                )

    def _generate_cluster_summaries(
        self,
        *,
        project_id: UUID,
        cluster_set_id: UUID,
        llm_provider: UUID | str,
        llm_provider_type: str,
        llm_provider_display_name: str | None,
        llm_model: str,
        sample_strategy: dict[str, Any],
    ) -> None:
        with open_database_connection(self._settings) as connection:
            rows = connection.execute(
                """
                SELECT c.id AS cluster_id, c.is_outlier, cm.message_pair_id,
                       mp.message, mp.answer
                FROM clusters c
                JOIN cluster_memberships cm
                  ON cm.cluster_id = c.id
                 AND cm.project_id = c.project_id
                 AND cm.cluster_set_id = c.cluster_set_id
                JOIN message_pairs mp ON mp.id = cm.message_pair_id
                WHERE c.project_id = %s AND c.cluster_set_id = %s
                ORDER BY c.created_at ASC, cm.membership_score DESC, mp.ordinal ASC
                """,
                (project_id, cluster_set_id),
            ).fetchall()
        grouped: dict[UUID, dict[str, Any]] = {}
        for row in rows:
            cluster_id = UUID(str(row["cluster_id"]))
            item = grouped.setdefault(
                cluster_id,
                {"is_outlier": bool(row["is_outlier"]), "examples": []},
            )
            cast(list[dict[str, str]], item["examples"]).append(
                {"message": str(row["message"]), "answer": str(row["answer"])}
            )
        summarizable = [
            (cluster_id, item)
            for cluster_id, item in grouped.items()
            if not bool(item["is_outlier"]) and item["examples"]
        ]
        if not summarizable:
            return
        _validate_summary_call_budget(len(summarizable))
        provider_fallback_reason: str | None = None
        for index, (cluster_id, item) in enumerate(summarizable, start=1):
            with open_database_connection(self._settings) as connection:
                with connection.transaction():
                    self._raise_if_cluster_set_cancelled(connection, cluster_set_id)
            examples = cast(list[dict[str, str]], item["examples"])
            sampled = self._sample_summary_examples(
                examples,
                sample_strategy=sample_strategy,
                cluster_id=cluster_id,
            )
            prompt = self._cluster_summary_prompt(sampled)
            if provider_fallback_reason is None:
                summary, summary_mode, fallback_reason = (
                    self._cluster_summary_from_provider_or_examples(
                        llm_provider=llm_provider,
                        llm_model=llm_model,
                        prompt=prompt,
                        examples=sampled,
                    )
                )
                if fallback_reason is not None and fallback_reason.startswith(
                    "provider_error:"
                ):
                    provider_fallback_reason = fallback_reason
            else:
                fallback_reason = (
                    f"provider_skipped_after_failure:{provider_fallback_reason}"
                )
                summary = self._fallback_cluster_summary_from_examples(
                    sampled,
                    fallback_reason=fallback_reason,
                )
                summary_mode = "fallback"
                fallback_reason = fallback_reason[:160]
            with open_database_connection(self._settings) as connection:
                with connection.transaction():
                    self._raise_if_cluster_set_cancelled(connection, cluster_set_id)
                    connection.execute(
                        """
                        UPDATE clusters
                        SET auto_title = %s,
                            auto_category = %s,
                            auto_summary_question = %s,
                            auto_summary_answer = %s,
                            metadata = metadata || %s,
                            updated_at = now()
                        WHERE id = %s AND project_id = %s AND cluster_set_id = %s
                        """,
                        (
                            summary["title"],
                            summary.get("category"),
                            summary["question"],
                            summary["answer"],
                            Jsonb(
                                {
                                    "llm_summary": {
                                        "provider": llm_provider_type,
                                        "provider_configuration_id": (
                                            str(llm_provider)
                                            if isinstance(llm_provider, UUID)
                                            else None
                                        ),
                                        "provider_display_name": (
                                            llm_provider_display_name
                                        ),
                                        "model": llm_model,
                                        "sample_count": len(sampled),
                                        "mode": summary_mode,
                                        "fallback_reason": fallback_reason,
                                        "rationale": summary.get("rationale"),
                                    }
                                }
                            ),
                            cluster_id,
                            project_id,
                            cluster_set_id,
                        ),
                    )
            progress = min(
                99,
                CLUSTER_SET_SUMMARY_PROGRESS
                + (14 * index // max(len(summarizable), 1)),
            )
            self._publish_cluster_set_progress(cluster_set_id, progress, "summarizing")

    def _cluster_summary_from_provider_or_examples(
        self,
        *,
        llm_provider: UUID | str,
        llm_model: str,
        prompt: str,
        examples: list[dict[str, str]],
    ) -> tuple[dict[str, str | None], str, str | None]:
        try:
            response_text = self._provider_service.generate_text(
                llm_provider, llm_model, prompt
            )
            return self._parse_cluster_summary_response(response_text), "llm", None
        except ProviderError as exc:
            fallback_reason = f"provider_error:{exc.__class__.__name__}"
        except ClusterError as exc:
            if exc.code != "CLUSTER_SUMMARY_FAILED":
                raise
            fallback_reason = f"parse_error:{exc}"
        LOGGER.warning(
            "cluster summary fallback used for provider=%s model=%s reason=%s",
            llm_provider,
            llm_model,
            fallback_reason,
        )
        return (
            self._fallback_cluster_summary_from_examples(
                examples,
                fallback_reason=fallback_reason,
            ),
            "fallback",
            fallback_reason[:160],
        )

    def _fallback_cluster_summary_from_examples(
        self,
        examples: list[dict[str, str]],
        *,
        fallback_reason: str,
    ) -> dict[str, str | None]:
        first = examples[0] if examples else {"message": "", "answer": ""}
        message = self._compact_summary_sentence(first.get("message", ""))
        answer = self._compact_summary_sentence(first.get("answer", ""))
        title_source = message or answer or "Cluster Summary"
        title = self._summary_title_from_text(title_source)
        question = message or "Welche Supportanfrage beschreibt dieser Cluster?"
        if not question.endswith("?"):
            question = f"Wie ist diese Anfrage zu bearbeiten: {question}"
        support_answer = (
            answer
            or "Die passende Supportantwort muss anhand der Quellen geprüft werden."
        )
        return {
            "title": title,
            "category": None,
            "question": question[:MAX_SUMMARY_FIELD_CHARACTERS],
            "answer": support_answer[:MAX_SUMMARY_FIELD_CHARACTERS],
            "rationale": (
                "Extraktive Fallback-Summary aus den Cluster-Beispielen, weil die "
                f"LLM-Antwort nicht nutzbar war ({fallback_reason[:120]})."
            )[:MAX_SUMMARY_FIELD_CHARACTERS],
        }

    def _summary_title_from_text(self, value: str) -> str:
        cleaned = self._compact_summary_sentence(value)
        if not cleaned:
            return "Cluster Summary"
        title = re.sub(
            r"^(wie|was|warum|wann|wo|welche|welcher|welches)\s+",
            "",
            cleaned,
            flags=re.IGNORECASE,
        )
        title = title.strip(" ?!.,;:")
        if not title:
            title = cleaned.strip(" ?!.,;:")
        if len(title) > 80:
            title = title[:77].rstrip() + "..."
        return title or "Cluster Summary"

    def _compact_summary_sentence(self, value: str) -> str:
        cleaned = " ".join(value.split())
        if not cleaned:
            return ""
        sentence_match = re.match(r"^(.{1,240}?[.!?])(?:\s|$)", cleaned)
        if sentence_match is not None:
            return sentence_match.group(1).strip()
        return cleaned[:240].strip()

    def _sample_summary_examples(
        self,
        examples: list[dict[str, str]],
        *,
        sample_strategy: dict[str, Any],
        cluster_id: UUID,
    ) -> list[dict[str, str]]:
        requested = sample_strategy.get("requested", 10)
        if requested == "all":
            sample_count = len(examples)
        elif isinstance(requested, int) and not isinstance(requested, bool):
            sample_count = min(requested, len(examples))
        else:
            raise ClusterError(
                "summary sample count is invalid",
                code="CLUSTER_SUMMARY_SAMPLE_COUNT_INVALID",
                status_code=422,
            )
        if sample_count < 1:
            raise ClusterError(
                "summary sample count is invalid",
                code="CLUSTER_SUMMARY_SAMPLE_COUNT_INVALID",
                status_code=422,
            )
        seed = sample_strategy.get("seed", 0)
        seed_int = (
            int(seed) if isinstance(seed, int) and not isinstance(seed, bool) else 0
        )
        # Deterministic sampling seed is persisted provenance, not security.
        rng = Random(seed_int ^ (cluster_id.int & ((1 << 63) - 1)))  # nosec B311
        if sample_count >= len(examples):
            return list(examples)
        return rng.sample(examples, sample_count)

    def _cluster_summary_prompt(self, examples: list[dict[str, str]]) -> str:
        lines = [
            "Aufgabe: Fasse diese Support-Beispiele zu genau einer FAQ-ähnlichen Cluster-Summary zusammen.",
            "Antworte ausschließlich mit einem einzelnen JSON-Objekt.",
            "Erlaubte Felder: title, category, question, answer, rationale.",
            "Pflicht: title, question und answer müssen nicht-leere Strings sein.",
            "category und rationale dürfen String oder null sein.",
            "Keine Markdown-Fences. Kein Fließtext. Keine Erklärungen außerhalb des JSON-Objekts.",
            "title: kurz und unterscheidbar, maximal 80 Zeichen.",
            "question: eine kanonische Kundenfrage, kein Listenformat.",
            "answer: eine kanonische Support-Antwort, konkret und knapp.",
            "rationale: ein kurzer Grund für die Zuordnung oder null.",
            "Wenn Beispiele widersprüchlich sind, bilde den gemeinsamen Kern und erwähne Unsicherheit nur in rationale.",
            "Support-Beispiele:",
        ]
        for index, example in enumerate(examples, start=1):
            lines.append(
                f"#{index} Nachricht: {self._summary_prompt_field(example['message'])}"
            )
            lines.append(
                f"#{index} Antwort: {self._summary_prompt_field(example['answer'])}"
            )
        prompt = "\n".join(lines)
        if len(prompt) > MAX_SUMMARY_PROMPT_CHARACTERS:
            raise ClusterError(
                "Cluster summary budget exceeded",
                code="CLUSTER_BUDGET_EXCEEDED",
                status_code=422,
                field_errors={
                    "llm_sample_count": "summary examples exceed the allowed budget"
                },
            )
        return prompt

    def _summary_prompt_field(self, value: str) -> str:
        cleaned = " ".join(value.split())
        if len(cleaned) <= MAX_SUMMARY_EXAMPLE_FIELD_CHARACTERS:
            return cleaned
        return cleaned[:MAX_SUMMARY_EXAMPLE_FIELD_CHARACTERS].rstrip() + " …"

    def _parse_cluster_summary_response(self, text: str) -> dict[str, str | None]:
        payload = self._summary_json_payload(text)
        payload_object = self._summary_payload_object(payload)
        return {
            "title": self._summary_field(
                self._summary_payload_value(payload_object, "title"),
                "title",
                required=True,
            ),
            "category": self._summary_field(
                self._summary_payload_value(payload_object, "category"),
                "category",
                required=False,
            ),
            "question": self._summary_field(
                self._summary_payload_value(payload_object, "question"),
                "question",
                required=True,
            ),
            "answer": self._summary_field(
                self._summary_payload_value(payload_object, "answer"),
                "answer",
                required=True,
            ),
            "rationale": self._summary_field(
                self._summary_payload_value(payload_object, "rationale"),
                "rationale",
                required=False,
            ),
        }

    def _summary_json_payload(self, text: str) -> object:
        candidate = self._normalize_summary_response_text(
            self._strip_markdown_json_fence(text.strip())
        )
        payload = self._try_load_summary_json(candidate)
        if payload is None:
            payload = self._try_load_summary_python_literal(candidate)
        if payload is None:
            payload = self._extract_summary_json_payload(candidate)
        return payload

    def _try_load_summary_json(self, candidate: str) -> object | None:
        try:
            return json.loads(candidate, strict=False)
        except json.JSONDecodeError:
            return None

    def _try_load_summary_python_literal(self, candidate: str) -> object | None:
        try:
            return ast.literal_eval(candidate)
        except (SyntaxError, ValueError):
            return None

    def _summary_payload_object(self, payload: object) -> dict[str, object]:
        candidates = list(self._summary_payload_candidates(payload))
        if candidates:
            return max(
                candidates,
                key=lambda item: self._summary_payload_score(item),
            )
        raise ClusterError(
            "Cluster summary response has no summary object",
            code="CLUSTER_SUMMARY_FAILED",
            status_code=422,
            retryable=True,
        )

    def _summary_payload_candidates(
        self, payload: object, *, depth: int = 0
    ) -> list[dict[str, object]]:
        if depth > 3:
            return []
        if isinstance(payload, dict):
            typed_payload = cast(dict[str, object], payload)
            candidates: list[dict[str, object]] = [typed_payload]
            for key, value in typed_payload.items():
                if (
                    self._normalize_summary_key(str(key))
                    in SUMMARY_RESPONSE_WRAPPER_KEYS
                ):
                    candidates.extend(
                        self._summary_payload_candidates(value, depth=depth + 1)
                    )
            return candidates
        if isinstance(payload, list):
            candidates = []
            for item in payload:
                candidates.extend(
                    self._summary_payload_candidates(item, depth=depth + 1)
                )
            return candidates
        if isinstance(payload, str):
            nested = self._summary_payload_from_text(payload)
            if nested is not None:
                return self._summary_payload_candidates(nested, depth=depth + 1)
        return []

    def _summary_payload_score(self, payload: dict[str, object]) -> int:
        score = 0
        for summary_field in SUMMARY_REQUIRED_FIELDS:
            value = self._summary_payload_value(payload, summary_field)
            if (
                isinstance(value, str)
                and value.strip()
                and not self._is_summary_placeholder_value(value)
            ):
                score += 2
            elif value is not None:
                score += 1
        for optional_field in ("category", "rationale"):
            value = self._summary_payload_value(payload, optional_field)
            if value is None or isinstance(value, str):
                score += 1
        return score

    def _summary_payload_value(
        self, payload: dict[str, object], field: str
    ) -> object | None:
        for alias in SUMMARY_FIELD_ALIASES[field]:
            if alias in payload:
                return payload[alias]
        normalized = {
            self._normalize_summary_key(str(key)): value
            for key, value in payload.items()
        }
        for alias in SUMMARY_FIELD_ALIASES[field]:
            value = normalized.get(self._normalize_summary_key(alias))
            if value is not None:
                return value
        return None

    def _normalize_summary_key(self, value: str) -> str:
        return (
            value.strip()
            .casefold()
            .replace("-", "_")
            .replace(" ", "_")
            .replace("__", "_")
        )

    def _is_summary_placeholder_value(self, value: str) -> bool:
        return value.strip().casefold() in SUMMARY_PLACEHOLDER_VALUES

    def _extract_summary_json_payload(self, candidate: str) -> object:
        decoder = json.JSONDecoder(strict=False)
        valid_payloads: list[object] = []
        for index, char in enumerate(candidate):
            if char not in "{[":
                continue
            decoded = self._try_decode_summary_json(decoder, candidate[index:])
            if decoded is not None:
                payload, _end = decoded
                valid_payloads.append(payload)
                continue
            literal_payload = self._try_load_summary_python_literal(candidate[index:])
            if literal_payload is not None:
                valid_payloads.append(literal_payload)
        if valid_payloads:
            return max(
                valid_payloads,
                key=lambda item: max(
                    (
                        self._summary_payload_score(candidate_payload)
                        for candidate_payload in self._summary_payload_candidates(item)
                    ),
                    default=0,
                ),
            )
        labeled_payload = self._summary_labeled_text_payload(candidate)
        if labeled_payload is not None:
            return labeled_payload
        raise ClusterError(
            "Cluster summary response contains no parseable JSON object",
            code="CLUSTER_SUMMARY_FAILED",
            status_code=422,
            retryable=True,
        )

    def _summary_payload_from_text(self, value: str) -> object | None:
        candidate = self._normalize_summary_response_text(
            self._strip_markdown_json_fence(value.strip())
        )
        payload = self._try_load_summary_json(candidate)
        if payload is not None:
            return payload
        payload = self._try_load_summary_python_literal(candidate)
        if payload is not None:
            return payload
        try:
            return self._extract_summary_json_payload(candidate)
        except ClusterError:
            return self._summary_labeled_text_payload(candidate)

    def _summary_labeled_text_payload(self, candidate: str) -> dict[str, object] | None:
        field_by_label = {
            self._normalize_summary_key(alias): field
            for field, aliases in SUMMARY_FIELD_ALIASES.items()
            for alias in aliases
        }
        values: dict[str, list[str]] = {}
        current_field: str | None = None
        for raw_line in candidate.splitlines():
            line = raw_line.strip()
            if not line:
                current_field = None
                continue
            match = re.match(
                r"^(?:[-*]\s*)?(?P<label>[\wÄÖÜäöüß -]{2,64})\s*[:：]\s*(?P<value>.*)$",
                line,
            )
            if match is not None:
                field = field_by_label.get(
                    self._normalize_summary_key(match.group("label"))
                )
                if field is not None:
                    current_field = field
                    values.setdefault(field, [])
                    value = match.group("value").strip()
                    if value:
                        values[field].append(value)
                    continue
            if current_field is not None:
                values[current_field].append(line)
        payload: dict[str, object] = {
            field: "\n".join(parts).strip()
            for field, parts in values.items()
            if "\n".join(parts).strip()
        }
        if all(field in payload for field in SUMMARY_REQUIRED_FIELDS):
            return payload
        return None

    def _normalize_summary_response_text(self, value: str) -> str:
        return (
            value.replace("\ufeff", "")
            .replace("\u00a0", " ")
            .replace("“", '"')
            .replace("”", '"')
            .replace("„", '"')
            .replace("‟", '"')
            .replace("’", "'")
            .replace("‘", "'")
        )

    def _strip_markdown_json_fence(self, candidate: str) -> str:
        if not candidate.startswith("```"):
            return candidate
        lines = candidate.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        return "\n".join(lines).strip()

    def _try_decode_summary_json(
        self,
        decoder: json.JSONDecoder,
        candidate: str,
    ) -> tuple[object, int] | None:
        try:
            return decoder.raw_decode(candidate)
        except json.JSONDecodeError:
            return None

    def _summary_field(
        self, value: object, field: str, *, required: bool
    ) -> str | None:
        if value is None and not required:
            return None
        if not isinstance(value, str) or not value.strip():
            raise ClusterError(
                f"Cluster summary field {field} is invalid",
                code="CLUSTER_SUMMARY_FAILED",
                status_code=422,
                retryable=True,
            )
        cleaned = value.strip()
        if required and self._is_summary_placeholder_value(cleaned):
            raise ClusterError(
                f"Cluster summary field {field} is invalid",
                code="CLUSTER_SUMMARY_FAILED",
                status_code=422,
                retryable=True,
            )
        return cleaned[:MAX_SUMMARY_FIELD_CHARACTERS]

    def _validate_and_insert_clusters(
        self,
        connection: Any,
        *,
        project_id: UUID,
        run_id: UUID,
        dataset_version_id: UUID,
        provider: str,
        model: str,
        config: AlgorithmConfiguration,
        pair_ids: list[object],
        vectors: np.ndarray[Any, np.dtype[np.float32]],
        expected_dimensions: int,
    ) -> None:
        labels, probabilities = self._cluster_vectors(config, vectors)

        grouped: dict[int, list[tuple[object, float]]] = {}
        for pair_id, label, probability in zip(
            pair_ids, labels, probabilities, strict=True
        ):
            grouped.setdefault(int(label), []).append((pair_id, probability))

        for label in sorted(grouped):
            members = grouped[label]
            is_outlier = label == -1
            cluster_id = uuid4()
            title = "Outliers" if is_outlier else f"Cluster {label + 1}"
            status = "outlier" if is_outlier else "unreviewed"
            score = sum(item[1] for item in members) / len(members)
            connection.execute(
                """
                INSERT INTO clusters (
                    id, project_id, analysis_run_id, dataset_version_id,
                    auto_title, auto_category, auto_status, score,
                    is_outlier, algorithm, metadata
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    cluster_id,
                    project_id,
                    run_id,
                    dataset_version_id,
                    title,
                    "outlier" if is_outlier else config.name,
                    status,
                    score,
                    is_outlier,
                    config.name,
                    Jsonb(
                        {
                            "label": label,
                            "parameters": config.parameters,
                            "provider": provider,
                            "model": model,
                            "dimensions": expected_dimensions,
                            "non_quadratic": True,
                        }
                    ),
                ),
            )
            for pair_id, membership_score in members:
                connection.execute(
                    """
                    INSERT INTO cluster_memberships (
                        id, project_id, cluster_id, analysis_run_id,
                        message_pair_id, membership_score, is_outlier,
                        assignment_type
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, 'automatic')
                    """,
                    (
                        uuid4(),
                        project_id,
                        cluster_id,
                        run_id,
                        pair_id,
                        membership_score,
                        is_outlier,
                    ),
                )
