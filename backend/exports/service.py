"""Cluster Explorer CSV/JSON exports with persisted history."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from datetime import datetime
from io import StringIO
from uuid import UUID, uuid4

from psycopg.types.json import Jsonb

from backend.audit import AuditService
from backend.config import DatabaseSettings
from backend.db.connection import open_database_connection

EXPLORER_CSV_COLUMNS = [
    "project_id",
    "cluster_set_id",
    "cluster_id",
    "title",
    "category",
    "summary_question",
    "summary_answer",
    "status",
    "is_excluded",
    "is_outlier",
    "customer_question_count",
    "support_answer_count",
    "score",
    "mismatch_average",
    "mismatch_maximum",
    "vector_basis",
    "algorithm",
    "dataset_version_id",
    "indexing_run_id",
    "filters",
    "export_created_at",
]

SUPPORTED_EXPLORER_EXPORT_FORMATS = {"csv", "json"}
MAX_EXPLORER_EXPORT_SELECTION = 10_000
CSV_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r", "\n")


class ExportError(ValueError):
    """Raised when an export cannot be produced."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "EXPLORER_EXPORT_FAILED",
        status_code: int = 500,
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


@dataclass(frozen=True)
class ExplorerExportInput:
    cluster_set_id: UUID
    export_format: str = "csv"
    search_query: str | None = None
    category: str | None = None
    include_excluded: bool = False
    include_outliers: bool = True
    cluster_ids: list[UUID] = field(default_factory=list)


@dataclass(frozen=True)
class ExportLog:
    id: UUID
    project_id: UUID
    export_type: str
    include_original_text: bool
    filters: dict[str, object]
    selection: dict[str, object]
    dataset_version_id: UUID | None
    analysis_run_id: UUID | None
    cluster_set_id: UUID | None
    output_filename: str
    output_path: str | None
    row_count: int
    created_at: datetime


@dataclass(frozen=True)
class ExportResult:
    log: ExportLog
    content: str
    content_type: str
    warning: str | None


def _json_cell(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _uuid_cell(value: UUID | None) -> str:
    return "" if value is None else str(value)


def _csv_cell(value: object) -> object:
    if not isinstance(value, str):
        return value
    stripped = value.lstrip(" ")
    if stripped and stripped[0] in CSV_FORMULA_PREFIXES:
        return f"'{value}"
    return value


def _write_csv(columns: list[str], rows: list[dict[str, object]]) -> str:
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=columns, extrasaction="raise")
    writer.writeheader()
    for row in rows:
        writer.writerow({column: _csv_cell(row[column]) for column in columns})
    return output.getvalue()


def _log_from_row(row: dict[str, object]) -> ExportLog:
    dataset_version_id = row["dataset_version_id"]
    analysis_run_id = row["analysis_run_id"]
    cluster_set_id = row.get("cluster_set_id")
    return ExportLog(
        id=UUID(str(row["id"])),
        project_id=UUID(str(row["project_id"])),
        export_type=str(row["export_type"]),
        include_original_text=bool(row["include_original_text"]),
        filters=dict(row["filters"]) if isinstance(row["filters"], dict) else {},
        selection=(
            dict(row["selection"]) if isinstance(row["selection"], dict) else {}
        ),
        dataset_version_id=(
            UUID(str(dataset_version_id)) if dataset_version_id is not None else None
        ),
        analysis_run_id=UUID(str(analysis_run_id))
        if analysis_run_id is not None
        else None,
        cluster_set_id=UUID(str(cluster_set_id))
        if cluster_set_id is not None
        else None,
        output_filename=str(row["output_filename"]),
        output_path=str(row["output_path"]) if row["output_path"] is not None else None,
        row_count=int(str(row["row_count"])),
        created_at=row["created_at"],  # type: ignore[arg-type]
    )


def _effective_text(row: dict[str, object], manual: str, automatic: str) -> str:
    manual_value = row.get(manual)
    if isinstance(manual_value, str) and manual_value.strip():
        return manual_value.strip()
    automatic_value = row.get(automatic)
    if isinstance(automatic_value, str):
        return automatic_value
    return ""


def _effective_status(row: dict[str, object]) -> str:
    return _effective_text(row, "manual_status", "auto_status") or "unreviewed"


def _metadata(row: dict[str, object]) -> dict[str, object]:
    value = row.get("metadata")
    return dict(value) if isinstance(value, dict) else {}


def _mismatch_value(metadata: dict[str, object], key: str) -> float | None:
    mismatch = metadata.get("qa_mismatch")
    if not isinstance(mismatch, dict):
        return None
    value = mismatch.get(key)
    if not isinstance(value, (int, float)):
        return None
    return float(value)


def _row_matches_search(row: dict[str, object], search_query: str | None) -> bool:
    if not search_query:
        return True
    haystack = "\n".join(
        [
            _effective_text(row, "manual_title", "auto_title"),
            _effective_text(row, "manual_category", "auto_category"),
            str(row.get("auto_summary_question") or ""),
            str(row.get("auto_summary_answer") or ""),
            _effective_status(row),
        ]
    ).lower()
    return search_query.lower() in haystack


def _row_matches_category(row: dict[str, object], category: str | None) -> bool:
    if not category:
        return True
    return _effective_text(row, "manual_category", "auto_category") == category


def _row_is_excluded(row: dict[str, object]) -> bool:
    return _effective_status(row) == "rejected"


def _row_is_outlier(row: dict[str, object]) -> bool:
    return bool(row.get("is_outlier"))


def _safe_filter_payload(payload: ExplorerExportInput) -> dict[str, object]:
    return {
        "search_query": payload.search_query or "",
        "category": payload.category or "",
        "include_excluded": payload.include_excluded,
        "include_outliers": payload.include_outliers,
    }


def _safe_audit_filter_payload(payload: ExplorerExportInput) -> dict[str, object]:
    return {
        "has_search_query": bool(payload.search_query),
        "category": payload.category or "",
        "include_excluded": payload.include_excluded,
        "include_outliers": payload.include_outliers,
    }


class ExportService:
    def __init__(self, settings: DatabaseSettings | None = None) -> None:
        self._settings = settings
        self._audit = AuditService()

    def export_explorer(
        self,
        project_id: UUID,
        payload: ExplorerExportInput,
        *,
        actor_user_id: UUID,
    ) -> ExportResult:
        export_format = payload.export_format.lower().strip()
        if export_format not in SUPPORTED_EXPLORER_EXPORT_FORMATS:
            raise ExportError(
                "unsupported Explorer export format",
                code="EXPLORER_EXPORT_FORMAT_INVALID",
                status_code=422,
                suggested_action="choose-format",
                field_errors={"export_format": "Export format must be csv or json."},
            )
        if len(payload.cluster_ids) > MAX_EXPLORER_EXPORT_SELECTION:
            raise ExportError(
                "Explorer export selection is too large",
                code="EXPLORER_EXPORT_SELECTION_TOO_LARGE",
                status_code=422,
                suggested_action="reduce-scope",
                field_errors={"cluster_ids": "Too many selected clusters."},
            )

        cluster_set, rows = self._load_export_rows(project_id, payload)
        filtered_rows = self._filter_rows(rows, payload)
        if not filtered_rows:
            raise ExportError(
                "Explorer export has no rows",
                code="EXPLORER_EXPORT_EMPTY",
                status_code=422,
                retryable=True,
                suggested_action="adjust-filter",
            )

        export_type = f"explorer_{export_format}"
        log = self._record_export(
            project_id,
            export_type=export_type,
            output_extension=export_format,
            include_original_text=False,
            row_count=len(filtered_rows),
            dataset_version_id=UUID(str(cluster_set["dataset_version_id"])),
            analysis_run_id=UUID(str(cluster_set["indexing_run_id"])),
            cluster_set_id=payload.cluster_set_id,
            filters=_safe_filter_payload(payload),
            selection={
                "cluster_ids": [str(cluster_id) for cluster_id in payload.cluster_ids],
            },
            audit_filters=_safe_audit_filter_payload(payload),
            actor_user_id=actor_user_id,
        )

        payload_rows = [
            self._explorer_export_row(
                row,
                cluster_set=cluster_set,
                filters=log.filters,
                export_created_at=log.created_at,
            )
            for row in filtered_rows
        ]
        if export_format == "csv":
            content = _write_csv(EXPLORER_CSV_COLUMNS, payload_rows)
            content_type = "text/csv"
        else:
            content = json.dumps(
                {
                    "project_id": str(project_id),
                    "cluster_set_id": str(payload.cluster_set_id),
                    "filters": log.filters,
                    "selection": log.selection,
                    "export_created_at": log.created_at.isoformat(),
                    "rows": payload_rows,
                },
                ensure_ascii=False,
                sort_keys=True,
            )
            content_type = "application/json"
        return ExportResult(
            log=log,
            content=content,
            content_type=content_type,
            warning=None,
        )

    def list_exports(self, project_id: UUID) -> list[ExportLog]:
        with open_database_connection(self._settings) as connection:
            rows = connection.execute(
                """
                SELECT id, project_id, export_type, include_original_text,
                       filters, selection, dataset_version_id, analysis_run_id,
                       cluster_set_id, output_filename, output_path, row_count,
                       created_at
                FROM export_logs
                WHERE project_id = %s
                ORDER BY created_at DESC
                """,
                (project_id,),
            ).fetchall()
        return [_log_from_row(dict(row)) for row in rows]

    def _load_export_rows(
        self, project_id: UUID, payload: ExplorerExportInput
    ) -> tuple[dict[str, object], list[dict[str, object]]]:
        with open_database_connection(self._settings) as connection:
            cluster_set = connection.execute(
                """
                SELECT id, project_id, dataset_version_id, indexing_run_id, status,
                       vector_basis, algorithm
                FROM cluster_sets
                WHERE id = %s AND project_id = %s AND deleted_at IS NULL
                """,
                (payload.cluster_set_id, project_id),
            ).fetchone()
            if cluster_set is None:
                raise ExportError(
                    "Cluster-Set not found",
                    code="CLUSTER_SET_NOT_FOUND",
                    status_code=404,
                    suggested_action="reload",
                )
            if str(cluster_set["status"]) != "completed":
                raise ExportError(
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
                LEFT JOIN cluster_memberships cm
                  ON cm.cluster_id = c.id AND cm.project_id = c.project_id
                WHERE c.project_id = %s AND c.cluster_set_id = %s
                GROUP BY c.id
                ORDER BY c.is_outlier ASC, c.score DESC, c.created_at ASC
                """,
                (project_id, payload.cluster_set_id),
            ).fetchall()
        return dict(cluster_set), [dict(row) for row in rows]

    def _filter_rows(
        self, rows: list[dict[str, object]], payload: ExplorerExportInput
    ) -> list[dict[str, object]]:
        selected_ids = set(payload.cluster_ids)
        known_ids = {UUID(str(row["id"])) for row in rows}
        if selected_ids and not selected_ids.issubset(known_ids):
            raise ExportError(
                "Explorer export selection contains unknown clusters",
                code="CLUSTER_SET_NOT_FOUND",
                status_code=404,
                suggested_action="reload",
            )
        return [
            row
            for row in rows
            if (not selected_ids or UUID(str(row["id"])) in selected_ids)
            and (payload.include_excluded or not _row_is_excluded(row))
            and (payload.include_outliers or not _row_is_outlier(row))
            and _row_matches_category(row, payload.category)
            and _row_matches_search(row, payload.search_query)
        ]

    @staticmethod
    def _explorer_export_row(
        row: dict[str, object],
        *,
        cluster_set: dict[str, object],
        filters: dict[str, object],
        export_created_at: datetime,
    ) -> dict[str, object]:
        metadata = _metadata(row)
        member_count = int(str(row.get("member_count", 0)))
        status = _effective_status(row)
        return {
            "project_id": str(row["project_id"]),
            "cluster_set_id": str(row["cluster_set_id"]),
            "cluster_id": str(row["id"]),
            "title": _effective_text(row, "manual_title", "auto_title"),
            "category": _effective_text(row, "manual_category", "auto_category"),
            "summary_question": str(row.get("auto_summary_question") or ""),
            "summary_answer": str(row.get("auto_summary_answer") or ""),
            "status": status,
            "is_excluded": status == "rejected",
            "is_outlier": bool(row.get("is_outlier")),
            "customer_question_count": member_count,
            "support_answer_count": member_count,
            "score": float(str(row.get("score", 0.0))),
            "mismatch_average": _mismatch_value(metadata, "average"),
            "mismatch_maximum": _mismatch_value(metadata, "maximum"),
            "vector_basis": str(cluster_set["vector_basis"]),
            "algorithm": str(row.get("algorithm") or cluster_set["algorithm"]),
            "dataset_version_id": str(row["dataset_version_id"]),
            "indexing_run_id": str(row["analysis_run_id"]),
            "filters": _json_cell(filters),
            "export_created_at": export_created_at.isoformat(),
        }

    def _record_export(
        self,
        project_id: UUID,
        *,
        export_type: str,
        output_extension: str,
        include_original_text: bool,
        row_count: int,
        dataset_version_id: UUID | None,
        analysis_run_id: UUID | None,
        cluster_set_id: UUID | None,
        filters: dict[str, object],
        selection: dict[str, object],
        audit_filters: dict[str, object],
        actor_user_id: UUID,
    ) -> ExportLog:
        export_id = uuid4()
        output_filename = f"{export_type}-{export_id}.{output_extension}"
        with open_database_connection(self._settings) as connection:
            with connection.transaction():
                row = connection.execute(
                    """
                    INSERT INTO export_logs (
                        id, project_id, export_type, include_original_text,
                        filters, selection, dataset_version_id, analysis_run_id,
                        cluster_set_id, output_filename, output_path, row_count,
                        created_by_user_id
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NULL, %s, %s)
                    RETURNING id, project_id, export_type, include_original_text,
                              filters, selection, dataset_version_id,
                              analysis_run_id, cluster_set_id, output_filename,
                              output_path, row_count, created_at
                    """,
                    (
                        export_id,
                        project_id,
                        export_type,
                        include_original_text,
                        Jsonb(filters),
                        Jsonb(selection),
                        dataset_version_id,
                        analysis_run_id,
                        cluster_set_id,
                        output_filename,
                        row_count,
                        actor_user_id,
                    ),
                ).fetchone()
                if row is None:
                    raise ExportError("export metadata could not be persisted")
                self._audit.record_event(
                    connection,
                    actor_user_id=actor_user_id,
                    action="export.create",
                    target_type="export",
                    target_id=export_id,
                    metadata={
                        "project_id": str(project_id),
                        "cluster_set_id": _uuid_cell(cluster_set_id),
                        "export_type": export_type,
                        "include_original_text": include_original_text,
                        "row_count": row_count,
                        "filters": audit_filters,
                    },
                )
        return _log_from_row(dict(row))
