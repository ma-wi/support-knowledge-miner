"""Validated clustering over persisted run embeddings and source traceability."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import math
from typing import Any, cast
from uuid import UUID, uuid4

import numpy as np
from pgvector import Vector
from psycopg.types.json import Jsonb
from scipy.sparse.csgraph import connected_components  # type: ignore[import-untyped]
from sklearn import config_context  # type: ignore[import-untyped]
from sklearn.cluster import AgglomerativeClustering, HDBSCAN  # type: ignore[import-untyped]
from sklearn.neighbors import kneighbors_graph  # type: ignore[import-untyped]

from backend.audit import AuditService
from backend.config import DatabaseSettings
from backend.db.connection import open_database_connection

VALID_STATUSES = {"unreviewed", "in_progress", "reviewed", "rejected", "outlier"}
AGGLOMERATIVE_MAX_RECORDS = 10_000
HDBSCAN_MAX_RECORDS = 100_000
MAX_CLUSTER_DIMENSIONS = 8_192
MAX_CLUSTER_WORKING_SET_BYTES = 512 * 1024 * 1024
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
AGGLOMERATIVE_NEIGHBOR_COUNT = 30
AGGLOMERATIVE_NEIGHBOR_WORKING_BYTES = 64 * 1024 * 1024
AGGLOMERATIVE_GRAPH_BYTES_PER_CELL = 256
AGGLOMERATIVE_DISTANCE_BYTES_PER_CELL_VALUE = 3 * NATIVE_MATRIX_BYTES_PER_VALUE
AGGLOMERATIVE_FIXED_BYTES_PER_RECORD = 512
SUPPORTED_ALGORITHMS = {"hdbscan", "agglomerative"}
AGGLOMERATIVE_LINKAGES = {"ward", "complete", "average", "single"}


class ClusterError(ValueError):
    """Raised when cluster input or state is invalid."""


@dataclass(frozen=True)
class AlgorithmConfiguration:
    name: str
    parameters: dict[str, int | float | str | None]

    def as_settings(self) -> dict[str, int | float | str | None]:
        return {"algorithm": self.name, **self.parameters}


@dataclass(frozen=True)
class ClusterManualUpdate:
    manual_title: str | None = None
    manual_category: str | None = None
    manual_status: str | None = None


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
        raise ClusterError(f"{field} must be an integer >= {minimum}")
    if maximum is not None and value > maximum:
        raise ClusterError(f"{field} must be an integer <= {maximum}")
    return value


def _number(
    settings: dict[str, Any], field: str, *, default: float, minimum: float
) -> float:
    value = settings.get(field, default)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ClusterError(f"{field} must be a number >= {minimum}")
    result = float(value)
    if not math.isfinite(result) or result < minimum:
        raise ClusterError(f"{field} must be a number >= {minimum}")
    return result


def validate_algorithm_settings(settings: dict[str, Any]) -> AlgorithmConfiguration:
    """Validate and normalize the accepted profile algorithm contract."""
    if not isinstance(settings, dict):
        raise ClusterError("algorithm_settings must be an object")
    algorithm = settings.get("algorithm")
    if not isinstance(algorithm, str) or algorithm not in SUPPORTED_ALGORITHMS:
        raise ClusterError("algorithm must be hdbscan or agglomerative")

    if algorithm == "hdbscan":
        allowed = {
            "algorithm",
            "min_cluster_size",
            "min_samples",
            "cluster_selection_epsilon",
        }
        unknown = set(settings) - allowed
        if unknown:
            raise ClusterError(f"unknown hdbscan setting: {sorted(unknown)[0]}")
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
            },
        )

    allowed = {
        "algorithm",
        "n_clusters",
        "distance_threshold",
        "linkage",
    }
    unknown = set(settings) - allowed
    if unknown:
        raise ClusterError(f"unknown agglomerative setting: {sorted(unknown)[0]}")
    n_clusters = _integer(settings, "n_clusters", default=2, minimum=1)
    distance_threshold_value = settings.get("distance_threshold")
    distance_threshold: float | None = None
    if distance_threshold_value is not None:
        distance_threshold = _number(
            settings, "distance_threshold", default=0.0, minimum=0.0
        )
        if "n_clusters" in settings:
            raise ClusterError(
                "n_clusters and distance_threshold cannot be used together"
            )
        n_clusters = None
    linkage = settings.get("linkage", "ward")
    if not isinstance(linkage, str) or linkage not in AGGLOMERATIVE_LINKAGES:
        raise ClusterError("linkage must be ward, complete, average, or single")
    return AlgorithmConfiguration(
        name=algorithm,
        parameters={
            "n_clusters": n_clusters,
            "distance_threshold": distance_threshold,
            "linkage": linkage,
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
    bytes_per_value = (
        AGGLOMERATIVE_BYTES_PER_VECTOR_VALUE
        if config.name == "agglomerative"
        else HDBSCAN_BYTES_PER_VECTOR_VALUE
    )
    estimated_bytes = record_count * dimensions * bytes_per_value
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
            f"{MAX_CLUSTER_WORKING_SET_BYTES}-byte (512 MiB) limit; "
            f"{recommendation}"
        )
    return dimensions


def _cluster_from_row(row: dict[str, object]) -> Cluster:
    metadata = row["metadata"]
    manual_title = row["manual_title"]
    manual_category = row["manual_category"]
    manual_status = row["manual_status"]
    auto_category = row["auto_category"]
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


class ClusterService:
    def __init__(self, settings: DatabaseSettings | None = None) -> None:
        self._settings = settings
        self._audit = AuditService()

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
        if manual_status is not None and manual_status not in VALID_STATUSES:
            raise ClusterError("manual_status is invalid")
        with open_database_connection(self._settings) as connection:
            with connection.transaction():
                row = connection.execute(
                    """
                    UPDATE clusters
                    SET manual_title = %s,
                        manual_category = %s,
                        manual_status = %s,
                        updated_at = now()
                    WHERE id = %s AND project_id = %s
                    RETURNING analysis_run_id
                    """,
                    (
                        manual_title,
                        manual_category,
                        manual_status,
                        cluster_id,
                        project_id,
                    ),
                ).fetchone()
                if row is None:
                    raise ClusterError("cluster not found")
                self._audit.record_event(
                    connection,
                    actor_user_id=actor_user_id,
                    action="cluster.update_manual",
                    target_type="cluster",
                    target_id=cluster_id,
                    metadata={"project_id": str(project_id)},
                )
                run_id = UUID(str(row["analysis_run_id"]))
        for cluster in self.list_clusters(project_id, run_id):
            if cluster.id == cluster_id:
                return cluster
        raise RuntimeError("cluster disappeared after update")

    def list_sources(self, project_id: UUID, cluster_id: UUID) -> list[ClusterSource]:
        with open_database_connection(self._settings) as connection:
            rows = connection.execute(
                """
                SELECT cm.cluster_id, cm.message_pair_id, mp.ticket_id,
                       mp.message_group_id, mp.message, mp.answer,
                       cm.membership_score, cm.is_outlier, cm.assignment_type
                FROM cluster_memberships cm
                JOIN clusters c ON c.id = cm.cluster_id AND c.project_id = %s
                JOIN message_pairs mp ON mp.id = cm.message_pair_id
                WHERE cm.project_id = %s AND cm.cluster_id = %s
                ORDER BY cm.is_outlier ASC, cm.membership_score DESC, mp.ordinal ASC
                """,
                (project_id, project_id, cluster_id),
            ).fetchall()
        return [_source_from_row(dict(row)) for row in rows]

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
        if config.name == "hdbscan":
            estimator = HDBSCAN(
                min_cluster_size=cast(int, config.parameters["min_cluster_size"]),
                min_samples=config.parameters["min_samples"],  # type: ignore[arg-type]
                cluster_selection_epsilon=cast(
                    float, config.parameters["cluster_selection_epsilon"]
                ),
                copy=False,
            )
            labels = estimator.fit_predict(vectors)
            probabilities = [float(value) for value in estimator.probabilities_]
        else:
            n_clusters = config.parameters["n_clusters"]
            if isinstance(n_clusters, int) and n_clusters > len(vectors):
                raise ClusterError("n_clusters cannot exceed the number of records")
            if len(vectors) == 1:
                labels = [0]
            else:
                with config_context(
                    working_memory=AGGLOMERATIVE_NEIGHBOR_WORKING_BYTES // (1024 * 1024)
                ):
                    connectivity = kneighbors_graph(
                        vectors,
                        n_neighbors=min(
                            AGGLOMERATIVE_NEIGHBOR_COUNT,
                            len(vectors) - 1,
                        ),
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
            probabilities = [1.0] * len(vectors)

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
