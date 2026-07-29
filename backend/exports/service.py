"""Candidate and source-assignment CSV exports with persisted history."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import datetime
from io import StringIO
from uuid import UUID, uuid4

from psycopg.types.json import Jsonb

from backend.audit import AuditService
from backend.candidates import Candidate, CandidateService, CandidateSource
from backend.config import DatabaseSettings
from backend.db.connection import open_database_connection

CANDIDATE_CSV_COLUMNS = [
    "candidate_id",
    "candidate_type",
    "status",
    "language",
    "category_path",
    "title",
    "canonical_question",
    "canonical_answer",
    "alternative_questions",
    "parameters",
    "external_data_dependencies",
    "quality_score",
    "faq_suitability_score",
    "dynamicity_score",
    "contradiction_score",
    "source_pair_count",
    "source_cluster_ids",
    "dataset_version_id",
    "analysis_run_id",
    "created_at",
    "updated_at",
    "contains_original_text",
    "notes",
]

SOURCE_ASSIGNMENT_CSV_COLUMNS = [
    "candidate_id",
    "cluster_id",
    "pair_id",
    "ticket_id",
    "message_group_id",
    "message_segment_id",
    "source_language",
    "customer_message",
    "support_answer",
    "normalized_customer_message",
    "normalized_support_answer",
    "assignment_type",
    "membership_score",
    "is_multi_intent",
    "intent_label",
    "dataset_version_id",
    "analysis_run_id",
]


class ExportError(ValueError):
    """Raised when an export cannot be produced."""


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
    output_filename: str
    output_path: str | None
    row_count: int
    created_at: datetime


@dataclass(frozen=True)
class ExportResult:
    log: ExportLog
    csv_content: str
    warning: str | None


def _json_cell(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _uuid_cell(value: UUID | None) -> str:
    return "" if value is None else str(value)


def _write_csv(columns: list[str], rows: list[dict[str, object]]) -> str:
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=columns, extrasaction="raise")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return output.getvalue()


def _log_from_row(row: dict[str, object]) -> ExportLog:
    dataset_version_id = row["dataset_version_id"]
    analysis_run_id = row["analysis_run_id"]
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
        output_filename=str(row["output_filename"]),
        output_path=str(row["output_path"]) if row["output_path"] is not None else None,
        row_count=int(str(row["row_count"])),
        created_at=row["created_at"],  # type: ignore[arg-type]
    )


class ExportService:
    def __init__(self, settings: DatabaseSettings | None = None) -> None:
        self._settings = settings
        self._candidates = CandidateService(settings)
        self._audit = AuditService()

    def export_candidates(
        self,
        project_id: UUID,
        *,
        include_original_text: bool,
        actor_user_id: UUID,
    ) -> ExportResult:
        candidates = self._candidates.list_candidates(project_id)
        actual_include_original_text = include_original_text or any(
            self._candidate_may_contain_source_text(candidate)
            for candidate in candidates
        )
        rows = [
            self._candidate_row(
                candidate, include_original_text=actual_include_original_text
            )
            for candidate in candidates
        ]
        csv_content = _write_csv(CANDIDATE_CSV_COLUMNS, rows)
        log = self._record_export(
            project_id,
            export_type="candidate_csv",
            include_original_text=actual_include_original_text,
            row_count=len(rows),
            dataset_version_id=self._single_uuid(
                [candidate.dataset_version_id for candidate in candidates]
            ),
            analysis_run_id=self._single_uuid(
                [candidate.analysis_run_id for candidate in candidates]
            ),
            actor_user_id=actor_user_id,
        )
        return ExportResult(
            log=log,
            csv_content=csv_content,
            warning=self._warning(actual_include_original_text),
        )

    def export_source_assignments(
        self,
        project_id: UUID,
        *,
        include_original_text: bool,
        actor_user_id: UUID,
    ) -> ExportResult:
        candidates = self._candidates.list_candidates(project_id)
        sources: list[CandidateSource] = []
        for candidate in candidates:
            sources.extend(self._candidates.list_sources(project_id, candidate.id))
        rows = [
            self._source_row(source, include_original_text=include_original_text)
            for source in sources
        ]
        csv_content = _write_csv(SOURCE_ASSIGNMENT_CSV_COLUMNS, rows)
        log = self._record_export(
            project_id,
            export_type="source_assignment_csv",
            include_original_text=include_original_text,
            row_count=len(rows),
            dataset_version_id=self._single_uuid(
                [source.dataset_version_id for source in sources]
            ),
            analysis_run_id=self._single_uuid(
                [source.analysis_run_id for source in sources]
            ),
            actor_user_id=actor_user_id,
        )
        return ExportResult(
            log=log,
            csv_content=csv_content,
            warning=self._warning(include_original_text),
        )

    def list_exports(self, project_id: UUID) -> list[ExportLog]:
        with open_database_connection(self._settings) as connection:
            rows = connection.execute(
                """
                SELECT id, project_id, export_type, include_original_text,
                       filters, selection, dataset_version_id, analysis_run_id,
                       output_filename, output_path, row_count, created_at
                FROM export_logs
                WHERE project_id = %s
                ORDER BY created_at DESC
                """,
                (project_id,),
            ).fetchall()
        return [_log_from_row(dict(row)) for row in rows]

    def _record_export(
        self,
        project_id: UUID,
        *,
        export_type: str,
        include_original_text: bool,
        row_count: int,
        dataset_version_id: UUID | None,
        analysis_run_id: UUID | None,
        actor_user_id: UUID,
    ) -> ExportLog:
        export_id = uuid4()
        output_filename = f"{export_type}-{export_id}.csv"
        with open_database_connection(self._settings) as connection:
            with connection.transaction():
                row = connection.execute(
                    """
                    INSERT INTO export_logs (
                        id, project_id, export_type, include_original_text,
                        filters, selection, dataset_version_id, analysis_run_id,
                        output_filename, output_path, row_count,
                        created_by_user_id
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NULL, %s, %s)
                    RETURNING id, project_id, export_type, include_original_text,
                              filters, selection, dataset_version_id,
                              analysis_run_id, output_filename, output_path,
                              row_count, created_at
                    """,
                    (
                        export_id,
                        project_id,
                        export_type,
                        include_original_text,
                        Jsonb({}),
                        Jsonb({}),
                        dataset_version_id,
                        analysis_run_id,
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
                        "export_type": export_type,
                        "include_original_text": include_original_text,
                        "row_count": row_count,
                    },
                )
        return _log_from_row(dict(row))

    @staticmethod
    def _candidate_row(
        candidate: Candidate, *, include_original_text: bool
    ) -> dict[str, object]:
        return {
            "candidate_id": str(candidate.id),
            "candidate_type": candidate.candidate_type,
            "status": candidate.effective_status,
            "language": candidate.language,
            "category_path": candidate.effective_category_path or "",
            "title": candidate.effective_title,
            "canonical_question": candidate.effective_canonical_question,
            "canonical_answer": candidate.effective_canonical_answer,
            "alternative_questions": _json_cell(
                candidate.effective_alternative_questions
            ),
            "parameters": _json_cell(candidate.effective_parameters),
            "external_data_dependencies": _json_cell(
                candidate.effective_external_data_dependencies
            ),
            "quality_score": candidate.quality_score,
            "faq_suitability_score": candidate.faq_suitability_score,
            "dynamicity_score": candidate.dynamicity_score,
            "contradiction_score": candidate.contradiction_score,
            "source_pair_count": candidate.source_pair_count,
            "source_cluster_ids": _json_cell(
                [str(cluster_id) for cluster_id in candidate.source_cluster_ids]
            ),
            "dataset_version_id": str(candidate.dataset_version_id),
            "analysis_run_id": _uuid_cell(candidate.analysis_run_id),
            "created_at": candidate.created_at.isoformat(),
            "updated_at": candidate.updated_at.isoformat(),
            "contains_original_text": str(include_original_text).lower(),
            "notes": candidate.notes or "",
        }

    @staticmethod
    def _candidate_may_contain_source_text(candidate: Candidate) -> bool:
        return candidate.source_cluster_id is not None

    @staticmethod
    def _source_row(
        source: CandidateSource, *, include_original_text: bool
    ) -> dict[str, object]:
        return {
            "candidate_id": str(source.candidate_id),
            "cluster_id": _uuid_cell(source.cluster_id),
            "pair_id": str(source.message_pair_id),
            "ticket_id": source.ticket_id,
            "message_group_id": source.message_group_id,
            "message_segment_id": source.message_segment_id or "",
            "source_language": source.source_language,
            "customer_message": source.message if include_original_text else "",
            "support_answer": source.answer if include_original_text else "",
            "normalized_customer_message": source.normalized_customer_message or "",
            "normalized_support_answer": source.normalized_support_answer or "",
            "assignment_type": source.assignment_type,
            "membership_score": source.membership_score,
            "is_multi_intent": str(source.is_multi_intent).lower(),
            "intent_label": source.intent_label or "",
            "dataset_version_id": str(source.dataset_version_id),
            "analysis_run_id": _uuid_cell(source.analysis_run_id),
        }

    @staticmethod
    def _single_uuid(values: list[UUID | None]) -> UUID | None:
        unique_values = {value for value in values if value is not None}
        return next(iter(unique_values)) if len(unique_values) == 1 else None

    @staticmethod
    def _warning(include_original_text: bool) -> str | None:
        if not include_original_text:
            return None
        return "Export enthaelt Originaltext und damit potentiell identifizierende Inhalte."
