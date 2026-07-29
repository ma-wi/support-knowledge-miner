"""Project-scoped import parsing and persistence."""

from __future__ import annotations

import csv
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import ijson  # type: ignore[import-untyped]
from psycopg.types.json import Jsonb

from backend.audit import AuditService
from backend.config import DatabaseSettings
from backend.db.connection import open_database_connection

REQUIRED_FIELDS = ("ticket_id", "message_group_id", "message", "answer")
MAX_IMPORT_BYTES = 512 * 1024 * 1024
MAX_SKIPPED_DETAILS = 100
DATABASE_BATCH_SIZE = 1_000
DATABASE_BATCH_BYTES = 4 * 1024 * 1024
DATABASE_RECORD_OVERHEAD_BYTES = 256


class ImportError(ValueError):
    """Raised when an import request is invalid."""


@dataclass(frozen=True)
class ValidRecord:
    source_location: str
    ticket_id: str
    message_group_id: str
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
    skipped_entries_truncated: bool


@dataclass(frozen=True)
class ImportScan:
    status: str
    failure_reason: str | None
    total_records: int
    valid_records: int
    skipped_records: int
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

    def import_file(
        self,
        project_id: UUID,
        *,
        source_type: str,
        source_name: str,
        source_path: Path,
        actor_user_id: UUID,
    ) -> ImportResult:
        clean_source_type = source_type.strip().lower()
        clean_source_name = source_name.strip() or "unnamed import"
        if clean_source_type not in {"csv", "json"}:
            raise ImportError("source_type must be csv or json")

        parsed = self._scan_file(clean_source_type, source_path)
        log_id = uuid4()
        dataset_version_id = uuid4() if parsed.valid_records else None

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
                        parsed.status,
                        parsed.failure_reason,
                        parsed.total_records,
                        parsed.valid_records,
                        parsed.skipped_records,
                        None,
                        actor_user_id,
                    ),
                ).fetchone()

                if parsed.skipped_entries:
                    entry_values = [
                        (
                            uuid4(),
                            log_id,
                            entry.source_location,
                            entry.reason,
                            Jsonb(entry.context),
                        )
                        for entry in parsed.skipped_entries
                    ]
                    with connection.cursor() as cursor:
                        cursor.executemany(
                            """
                        INSERT INTO import_log_entries (
                            id, import_log_id, source_location, reason, context
                        )
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                            entry_values,
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
                            parsed.valid_records,
                            clean_source_type,
                            clean_source_name,
                            actor_user_id,
                        ),
                    ).fetchone()
                    ordinal = 0
                    for record_batch in self._iter_valid_record_batches(
                        clean_source_type, source_path
                    ):
                        message_values: list[tuple[object, ...]] = []
                        for record in record_batch:
                            ordinal += 1
                            message_values.append(
                                (
                                    uuid4(),
                                    project_id,
                                    dataset_version_id,
                                    ordinal,
                                    record.ticket_id,
                                    record.message_group_id,
                                    record.message,
                                    record.answer,
                                )
                            )
                        self._insert_message_batch(connection, message_values)
                    if ordinal != parsed.valid_records:
                        raise RuntimeError(
                            "Importdatei hat sich zwischen Validierung und "
                            "Persistierung verändert."
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
                        "status": parsed.status,
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
            skipped_entries=parsed.skipped_entries,
            skipped_entries_truncated=(
                parsed.skipped_records > len(parsed.skipped_entries)
            ),
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

    def _scan_file(self, source_type: str, source_path: Path) -> ImportScan:
        total = 0
        valid = 0
        skipped = 0
        entries: list[ImportLogEntry] = []
        try:
            for location, row in self._iter_rows(source_type, source_path):
                total += 1
                try:
                    self._record_from_row(row, location)
                    valid += 1
                except ImportError as exc:
                    skipped += 1
                    if len(entries) < MAX_SKIPPED_DETAILS:
                        entries.append(self._skipped_entry(location, row, exc))
        except ImportError as exc:
            return ImportScan(
                status="failed",
                failure_reason=str(exc),
                total_records=0,
                valid_records=0,
                skipped_records=0,
                skipped_entries=[],
            )
        return ImportScan(
            status="completed" if valid else "failed",
            failure_reason=None if valid else "Keine gültigen Datensätze gefunden.",
            total_records=total,
            valid_records=valid,
            skipped_records=skipped,
            skipped_entries=entries,
        )

    def _iter_rows(
        self, source_type: str, source_path: Path
    ) -> Iterator[tuple[str, dict[str, object]]]:
        if source_type == "csv":
            yield from self._iter_csv_rows(source_path)
            return
        yield from self._iter_json_rows(source_path)

    def _iter_csv_rows(
        self, source_path: Path
    ) -> Iterator[tuple[str, dict[str, object]]]:
        try:
            with source_path.open(
                "r", encoding="utf-8", errors="strict", newline=""
            ) as source:
                reader = csv.DictReader(source, strict=True)
                fieldnames = set(reader.fieldnames or [])
                missing = [
                    field for field in REQUIRED_FIELDS if field not in fieldnames
                ]
                if missing:
                    raise ImportError(f"CSV-Kopfzeilen fehlen: {', '.join(missing)}.")
                for index, row in enumerate(reader, start=2):
                    yield f"row {index}", dict(row)
        except UnicodeDecodeError as exc:
            raise ImportError("Datei ist nicht gültig UTF-8-codiert.") from exc
        except csv.Error as exc:
            raise ImportError("CSV ist fehlerhaft.") from exc

    def _iter_json_rows(
        self, source_path: Path
    ) -> Iterator[tuple[str, dict[str, object]]]:
        try:
            with source_path.open("rb") as source:
                first_non_whitespace = b""
                while not first_non_whitespace:
                    character = source.read(1)
                    if character == b"":
                        raise ImportError("JSON ist fehlerhaft.")
                    if character not in b" \t\r\n":
                        first_non_whitespace = character
                if first_non_whitespace != b"[":
                    source.seek(0)
                    try:
                        source.read(65_536).decode("utf-8", errors="strict")
                    except UnicodeDecodeError as exc:
                        raise ImportError(
                            "Datei ist nicht gültig UTF-8-codiert."
                        ) from exc
                    raise ImportError("JSON-Wurzel muss ein Array sein.")
                source.seek(0)
                for index, item in enumerate(
                    ijson.items(source, "item", use_float=True), start=1
                ):
                    row = item if isinstance(item, dict) else {}
                    yield f"object {index}", row
        except UnicodeDecodeError as exc:
            raise ImportError("Datei ist nicht gültig UTF-8-codiert.") from exc
        except (ijson.JSONError, OverflowError) as exc:
            error_message = str(exc).casefold()
            if "utf8" in error_message or "utf-8" in error_message:
                raise ImportError("Datei ist nicht gültig UTF-8-codiert.") from exc
            raise ImportError("JSON ist fehlerhaft.") from exc

    def _record_from_row(
        self, row: dict[str, object], source_location: str
    ) -> ValidRecord:
        return ValidRecord(
            source_location=source_location,
            ticket_id=_clean_required(row.get("ticket_id"), "ticket_id"),
            message_group_id=_clean_required(
                row.get("message_group_id"), "message_group_id"
            ),
            message=_clean_required(row.get("message"), "message"),
            answer=_clean_required(row.get("answer"), "answer"),
        )

    def _skipped_entry(
        self, location: str, row: dict[str, object], error: ImportError
    ) -> ImportLogEntry:
        return ImportLogEntry(
            source_location=location,
            reason=str(error),
            context={
                "ticket_id": str(row.get("ticket_id", ""))[:120],
                "message_group_id": str(row.get("message_group_id", ""))[:120],
            },
        )

    def _insert_message_batch(
        self, connection: Any, values: list[tuple[object, ...]]
    ) -> None:
        with connection.cursor() as cursor:
            cursor.executemany(
                """
                INSERT INTO message_pairs (
                    id, project_id, dataset_version_id, ordinal,
                    ticket_id, message_group_id, message, answer
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                values,
            )

    def _record_size_bytes(self, record: ValidRecord) -> int:
        return DATABASE_RECORD_OVERHEAD_BYTES + sum(
            len(value.encode("utf-8"))
            for value in (
                record.ticket_id,
                record.message_group_id,
                record.message,
                record.answer,
            )
        )

    def _iter_valid_record_batches(
        self, source_type: str, source_path: Path
    ) -> Iterator[list[ValidRecord]]:
        batch: list[ValidRecord] = []
        batch_bytes = 0
        for location, row in self._iter_rows(source_type, source_path):
            try:
                record = self._record_from_row(row, location)
            except ImportError:
                continue
            record_bytes = self._record_size_bytes(record)
            if batch and batch_bytes + record_bytes > DATABASE_BATCH_BYTES:
                yield batch
                batch = []
                batch_bytes = 0
            batch.append(record)
            batch_bytes += record_bytes
            if len(batch) == DATABASE_BATCH_SIZE or batch_bytes >= DATABASE_BATCH_BYTES:
                yield batch
                batch = []
                batch_bytes = 0
        if batch:
            yield batch
