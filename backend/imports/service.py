"""Project-scoped import parsing and persistence."""

from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from psycopg.types.json import Jsonb

from backend.audit import AuditService
from backend.config import DatabaseSettings
from backend.db.connection import open_database_connection

REQUIRED_FIELDS = ("ticketid", "messagegroupid", "message", "answer")
MAX_IMPORT_BYTES = 5 * 1024 * 1024


class ImportError(ValueError):
    """Raised when an import request is invalid."""


@dataclass(frozen=True)
class ValidRecord:
    source_location: str
    ticketid: str
    messagegroupid: str
    message: str
    answer: str


@dataclass(frozen=True)
class ImportLogEntry:
    source_location: str
    reason: str
    context: dict[str, Any]


@dataclass(frozen=True)
class ImportLog:
    id: UUID
    project_id: UUID
    source_type: str
    source_name: str
    status: str
    failure_reason: str | None
    total_records: int
    valid_records: int
    skipped_records: int
    dataset_version_id: UUID | None
    started_at: datetime
    completed_at: datetime


@dataclass(frozen=True)
class DatasetVersion:
    id: UUID
    project_id: UUID
    version_number: int
    import_log_id: UUID
    record_count: int
    source_type: str
    source_name: str
    created_at: datetime


@dataclass(frozen=True)
class ImportResult:
    log: ImportLog
    dataset_version: DatasetVersion | None
    skipped_entries: list[ImportLogEntry]


def _clean_required(value: object, field: str) -> str:
    if value is None:
        raise ImportError(f"{field} is required")
    cleaned = str(value).strip()
    if not cleaned:
        raise ImportError(f"{field} must not be empty")
    return cleaned


def _entry_from_row(row: dict[str, object]) -> ImportLogEntry:
    context = row["context"]
    return ImportLogEntry(
        source_location=str(row["source_location"]),
        reason=str(row["reason"]),
        context=dict(context) if isinstance(context, dict) else {},
    )


def _log_from_row(row: dict[str, object]) -> ImportLog:
    dataset_version_id = row["dataset_version_id"]
    return ImportLog(
        id=UUID(str(row["id"])),
        project_id=UUID(str(row["project_id"])),
        source_type=str(row["source_type"]),
        source_name=str(row["source_name"]),
        status=str(row["status"]),
        failure_reason=(
            str(row["failure_reason"]) if row["failure_reason"] is not None else None
        ),
        total_records=int(str(row["total_records"])),
        valid_records=int(str(row["valid_records"])),
        skipped_records=int(str(row["skipped_records"])),
        dataset_version_id=(
            UUID(str(dataset_version_id)) if dataset_version_id is not None else None
        ),
        started_at=row["started_at"],  # type: ignore[arg-type]
        completed_at=row["completed_at"],  # type: ignore[arg-type]
    )


def _dataset_from_row(row: dict[str, object]) -> DatasetVersion:
    return DatasetVersion(
        id=UUID(str(row["id"])),
        project_id=UUID(str(row["project_id"])),
        version_number=int(str(row["version_number"])),
        import_log_id=UUID(str(row["import_log_id"])),
        record_count=int(str(row["record_count"])),
        source_type=str(row["source_type"]),
        source_name=str(row["source_name"]),
        created_at=row["created_at"],  # type: ignore[arg-type]
    )


class ImportService:
    def __init__(self, settings: DatabaseSettings | None = None) -> None:
        self._settings = settings
        self._audit = AuditService()

    def import_content(
        self,
        project_id: UUID,
        *,
        source_type: str,
        source_name: str,
        content: str,
        actor_user_id: UUID,
    ) -> ImportResult:
        clean_source_type = source_type.strip().lower()
        clean_source_name = source_name.strip() or "unnamed import"
        if clean_source_type not in {"csv", "json"}:
            raise ImportError("source_type must be csv or json")
        if len(content.encode("utf-8")) > MAX_IMPORT_BYTES:
            raise ImportError("import file is too large")

        parsed = self._parse(clean_source_type, content)
        log_id = uuid4()
        dataset_version_id = uuid4() if parsed["valid_records"] else None

        with open_database_connection(self._settings) as connection:
            with connection.transaction():
                project = connection.execute(
                    "SELECT id FROM projects WHERE id = %s AND deleted_at IS NULL",
                    (project_id,),
                ).fetchone()
                if project is None:
                    raise ImportError("project not found")

                version_number = 0
                dataset_row = None
                if dataset_version_id is not None:
                    max_row = connection.execute(
                        """
                        SELECT COALESCE(MAX(version_number), 0) + 1 AS next_version
                        FROM dataset_versions
                        WHERE project_id = %s
                        """,
                        (project_id,),
                    ).fetchone()
                    version_number = int(
                        str(max_row["next_version"]) if max_row else "1"
                    )

                log_row = connection.execute(
                    """
                    INSERT INTO import_logs (
                        id, project_id, source_type, source_name, status,
                        failure_reason, total_records, valid_records,
                        skipped_records, dataset_version_id, created_by_user_id
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id, project_id, source_type, source_name, status,
                              failure_reason, total_records, valid_records,
                              skipped_records, dataset_version_id, started_at,
                              completed_at
                    """,
                    (
                        log_id,
                        project_id,
                        clean_source_type,
                        clean_source_name,
                        parsed["status"],
                        parsed["failure_reason"],
                        parsed["total_records"],
                        len(parsed["valid_records"]),
                        len(parsed["skipped_entries"]),
                        None,
                        actor_user_id,
                    ),
                ).fetchone()

                for entry in parsed["skipped_entries"]:
                    connection.execute(
                        """
                        INSERT INTO import_log_entries (
                            id, import_log_id, source_location, reason, context
                        )
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (
                            uuid4(),
                            log_id,
                            entry.source_location,
                            entry.reason,
                            Jsonb(entry.context),
                        ),
                    )

                if dataset_version_id is not None:
                    dataset_row = connection.execute(
                        """
                        INSERT INTO dataset_versions (
                            id, project_id, version_number, import_log_id,
                            record_count, source_type, source_name,
                            created_by_user_id
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING id, project_id, version_number, import_log_id,
                                  record_count, source_type, source_name, created_at
                        """,
                        (
                            dataset_version_id,
                            project_id,
                            version_number,
                            log_id,
                            len(parsed["valid_records"]),
                            clean_source_type,
                            clean_source_name,
                            actor_user_id,
                        ),
                    ).fetchone()
                    for ordinal, record in enumerate(parsed["valid_records"], start=1):
                        connection.execute(
                            """
                            INSERT INTO message_pairs (
                                id, project_id, dataset_version_id, ordinal,
                                ticketid, messagegroupid, message, answer
                            )
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                            """,
                            (
                                uuid4(),
                                project_id,
                                dataset_version_id,
                                ordinal,
                                record.ticketid,
                                record.messagegroupid,
                                record.message,
                                record.answer,
                            ),
                        )
                    log_row = connection.execute(
                        """
                        UPDATE import_logs
                        SET dataset_version_id = %s
                        WHERE id = %s
                        RETURNING id, project_id, source_type, source_name, status,
                                  failure_reason, total_records, valid_records,
                                  skipped_records, dataset_version_id, started_at,
                                  completed_at
                        """,
                        (dataset_version_id, log_id),
                    ).fetchone()

                self._audit.record_event(
                    connection,
                    actor_user_id=actor_user_id,
                    action="import.create",
                    target_type="import_log",
                    target_id=log_id,
                    metadata={
                        "source_type": clean_source_type,
                        "status": parsed["status"],
                    },
                )

        if log_row is None:
            raise RuntimeError("import log insert returned no row")
        return ImportResult(
            log=_log_from_row(dict(log_row)),
            dataset_version=(
                _dataset_from_row(dict(dataset_row))
                if dataset_row is not None
                else None
            ),
            skipped_entries=parsed["skipped_entries"],
        )

    def list_logs(self, project_id: UUID) -> list[ImportLog]:
        with open_database_connection(self._settings) as connection:
            rows = connection.execute(
                """
                SELECT id, project_id, source_type, source_name, status,
                       failure_reason, total_records, valid_records,
                       skipped_records, dataset_version_id, started_at, completed_at
                FROM import_logs
                WHERE project_id = %s
                ORDER BY started_at DESC
                """,
                (project_id,),
            ).fetchall()
        return [_log_from_row(dict(row)) for row in rows]

    def get_log_entries(
        self, project_id: UUID, import_log_id: UUID
    ) -> list[ImportLogEntry]:
        with open_database_connection(self._settings) as connection:
            rows = connection.execute(
                """
                SELECT e.source_location, e.reason, e.context
                FROM import_log_entries e
                JOIN import_logs l ON l.id = e.import_log_id
                WHERE l.project_id = %s AND l.id = %s
                ORDER BY e.created_at ASC
                """,
                (project_id, import_log_id),
            ).fetchall()
        return [_entry_from_row(dict(row)) for row in rows]

    def _parse(self, source_type: str, content: str) -> dict[str, Any]:
        try:
            if source_type == "csv":
                records, entries, total = self._parse_csv(content)
            else:
                records, entries, total = self._parse_json(content)
        except ImportError as exc:
            return {
                "valid_records": [],
                "skipped_entries": [],
                "total_records": 0,
                "status": "failed",
                "failure_reason": str(exc),
            }
        status = "completed" if records else "failed"
        failure_reason = None if records else "no valid records found"
        return {
            "valid_records": records,
            "skipped_entries": entries,
            "total_records": total,
            "status": status,
            "failure_reason": failure_reason,
        }

    def _parse_csv(
        self, content: str
    ) -> tuple[list[ValidRecord], list[ImportLogEntry], int]:
        try:
            reader = csv.DictReader(io.StringIO(content))
            fieldnames = set(reader.fieldnames or [])
        except csv.Error as exc:
            raise ImportError("malformed CSV") from exc
        missing = [field for field in REQUIRED_FIELDS if field not in fieldnames]
        if missing:
            raise ImportError(f"missing CSV headers: {', '.join(missing)}")
        rows = list(reader)
        return self._validate_rows(rows, location_prefix="row", location_offset=2)

    def _parse_json(
        self, content: str
    ) -> tuple[list[ValidRecord], list[ImportLogEntry], int]:
        try:
            payload = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ImportError("malformed JSON") from exc
        if not isinstance(payload, list):
            raise ImportError("JSON root must be a list")
        rows = [item if isinstance(item, dict) else {} for item in payload]
        return self._validate_rows(rows, location_prefix="object", location_offset=1)

    def _validate_rows(
        self,
        rows: list[dict[str, object]],
        *,
        location_prefix: str,
        location_offset: int,
    ) -> tuple[list[ValidRecord], list[ImportLogEntry], int]:
        valid: list[ValidRecord] = []
        skipped: list[ImportLogEntry] = []
        for index, row in enumerate(rows, start=location_offset):
            location = f"{location_prefix} {index}"
            try:
                valid.append(
                    ValidRecord(
                        source_location=location,
                        ticketid=_clean_required(row.get("ticketid"), "ticketid"),
                        messagegroupid=_clean_required(
                            row.get("messagegroupid"), "messagegroupid"
                        ),
                        message=_clean_required(row.get("message"), "message"),
                        answer=_clean_required(row.get("answer"), "answer"),
                    )
                )
            except ImportError as exc:
                skipped.append(
                    ImportLogEntry(
                        source_location=location,
                        reason=str(exc),
                        context={
                            "ticketid": str(row.get("ticketid", ""))[:120],
                            "messagegroupid": str(row.get("messagegroupid", ""))[:120],
                        },
                    )
                )
        return valid, skipped, len(rows)
