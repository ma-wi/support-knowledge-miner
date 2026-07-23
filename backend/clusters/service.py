"""Cluster persistence, deterministic scaffold clustering, and source traceability."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from psycopg.types.json import Jsonb

from backend.audit import AuditService
from backend.config import DatabaseSettings
from backend.db.connection import open_database_connection

VALID_STATUSES = {"unreviewed", "in_progress", "reviewed", "rejected", "outlier"}


class ClusterError(ValueError):
    """Raised when cluster input or state is invalid."""


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
    ticketid: str
    messagegroupid: str
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


def _cluster_key(message: str) -> str:
    cleaned = message.strip().lower()
    if not cleaned:
        return "empty"
    token = cleaned.split(maxsplit=1)[0]
    return token[:1] if token else "empty"


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
        ticketid=str(row["ticketid"]),
        messagegroupid=str(row["messagegroupid"]),
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
                    SELECT id, project_id, dataset_version_id, status
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
                    pairs = connection.execute(
                        """
                        SELECT id, ticketid, messagegroupid, message, answer
                        FROM message_pairs
                        WHERE project_id = %s AND dataset_version_id = %s
                        ORDER BY ordinal ASC
                        """,
                        (project_id, run["dataset_version_id"]),
                    ).fetchall()
                    self._insert_deterministic_clusters(
                        connection,
                        project_id=project_id,
                        run_id=run_id,
                        dataset_version_id=UUID(str(run["dataset_version_id"])),
                        pairs=[dict(pair) for pair in pairs],
                    )
                    self._audit.record_event(
                        connection,
                        actor_user_id=actor_user_id,
                        action="clusters.generate",
                        target_type="analysis_run",
                        target_id=run_id,
                        metadata={"project_id": str(project_id), "pairs": len(pairs)},
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
                SELECT cm.cluster_id, cm.message_pair_id, mp.ticketid,
                       mp.messagegroupid, mp.message, mp.answer,
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

    def _insert_deterministic_clusters(
        self,
        connection: Any,
        *,
        project_id: UUID,
        run_id: UUID,
        dataset_version_id: UUID,
        pairs: list[dict[str, object]],
    ) -> None:
        grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
        for pair in pairs:
            grouped[_cluster_key(str(pair["message"]))].append(pair)
        for key, members in grouped.items():
            is_outlier = len(members) == 1
            cluster_id = uuid4()
            title = f"Outlier {key.upper()}" if is_outlier else f"Cluster {key.upper()}"
            status = "outlier" if is_outlier else "unreviewed"
            score = 0.0 if is_outlier else min(1.0, len(members) / max(1, len(pairs)))
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
                    "outlier" if is_outlier else "deterministic-key",
                    status,
                    score,
                    is_outlier,
                    "linear-prefix-scaffold",
                    Jsonb({"key": key, "non_quadratic": True}),
                ),
            )
            for member in members:
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
                        member["id"],
                        score,
                        is_outlier,
                    ),
                )
