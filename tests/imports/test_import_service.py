from __future__ import annotations

from pathlib import Path

import pytest

import backend.imports.service as import_service_module
from backend.imports.service import MAX_SKIPPED_DETAILS, ImportService


def _scan(tmp_path: Path, source_type: str, content: str):
    source_path = tmp_path / f"fixture.{source_type}"
    source_path.write_text(content, encoding="utf-8")
    return ImportService()._scan_file(source_type, source_path)


def test_csv_parser_accepts_duplicates_and_skips_invalid_records(
    tmp_path: Path,
) -> None:
    result = _scan(
        tmp_path,
        "csv",
        "ticket_id,message_group_id,message,answer\n"
        "T-1,G-1,Hello,Answer\n"
        "T-1,G-1,Duplicate,Answer 2\n"
        "T-2,G-2,   ,Missing message\n",
    )

    assert result.status == "completed"
    assert result.total_records == 3
    assert result.valid_records == 2
    assert result.skipped_records == 1
    assert result.skipped_entries[0].reason == "message must not be empty"


def test_csv_parser_reports_missing_headers_and_malformed_csv(
    tmp_path: Path,
) -> None:
    missing = _scan(tmp_path, "csv", "ticket_id,message,answer\nT-1,Hi,A\n")
    malformed = _scan(
        tmp_path,
        "csv",
        'ticket_id,message_group_id,message,answer\nT-1,G-1,"Hi,A\n',
    )

    assert missing.status == "failed"
    assert missing.failure_reason == "CSV-Kopfzeilen fehlen: message_group_id."
    assert missing.total_records == 0
    assert malformed.status == "failed"
    assert malformed.failure_reason == "CSV ist fehlerhaft."


def test_import_parser_rejects_legacy_source_id_names(tmp_path: Path) -> None:
    csv_result = _scan(
        tmp_path,
        "csv",
        "ticketid,messagegroupid,message,answer\nT-1,G-1,Hi,A\n",
    )
    json_result = _scan(
        tmp_path,
        "json",
        '[{"ticketid":"T-1","messagegroupid":"G-1","message":"Hi","answer":"A"}]',
    )

    assert csv_result.status == "failed"
    assert csv_result.failure_reason == (
        "CSV-Kopfzeilen fehlen: ticket_id, message_group_id."
    )
    assert json_result.status == "failed"
    assert [entry.reason for entry in json_result.skipped_entries] == [
        "ticket_id is required"
    ]


def test_json_parser_requires_array_root_and_validates_records(
    tmp_path: Path,
) -> None:
    failed = _scan(tmp_path, "json", '{"ticket_id": "T-1"}')
    malformed = _scan(tmp_path, "json", '[{"ticket_id":')
    imported = _scan(
        tmp_path,
        "json",
        "["
        '{"ticket_id":"T-1","message_group_id":"G-1","message":"Hi","answer":"A"},'
        '{"ticket_id":"T-2","message_group_id":"G-2","message":"Hi","answer":""}'
        "]",
    )

    assert failed.status == "failed"
    assert failed.failure_reason == "JSON-Wurzel muss ein Array sein."
    assert malformed.failure_reason == "JSON ist fehlerhaft."
    assert imported.status == "completed"
    assert imported.valid_records == 1
    assert imported.skipped_entries[0].reason == "answer must not be empty"


def test_invalid_utf8_has_a_specific_file_failure(tmp_path: Path) -> None:
    source_path = tmp_path / "fixture.json"
    source_path.write_bytes(b'[{"message":"\xff"}]')

    result = ImportService()._scan_file("json", source_path)

    assert result.status == "failed"
    assert result.failure_reason == "Datei ist nicht gültig UTF-8-codiert."


def test_json_import_log_context_uses_bounded_snake_case_ids(
    tmp_path: Path,
) -> None:
    long_ticket_id = "T" * 121
    long_message_group_id = "G" * 121
    result = _scan(
        tmp_path,
        "json",
        (
            f'[{{"ticket_id":"{long_ticket_id}",'
            f'"message_group_id":"{long_message_group_id}",'
            '"message":"Hi","answer":""}]'
        ),
    )

    entry = result.skipped_entries[0]
    assert entry.reason == "answer must not be empty"
    assert entry.context == {
        "ticket_id": long_ticket_id[:120],
        "message_group_id": long_message_group_id[:120],
    }


def test_zero_valid_records_reports_failed_without_dataset(
    tmp_path: Path,
) -> None:
    result = _scan(
        tmp_path,
        "json",
        '[{"ticket_id":"T-1","message_group_id":"G-1","message":"","answer":""}]',
    )

    assert result.status == "failed"
    assert result.failure_reason == "Keine gültigen Datensätze gefunden."
    assert result.total_records == 1
    assert result.skipped_records == 1


def test_skipped_detail_collection_is_bounded_but_counts_are_complete(
    tmp_path: Path,
) -> None:
    invalid_records = ",".join("{}" for _ in range(MAX_SKIPPED_DETAILS + 7))
    result = _scan(tmp_path, "json", f"[{invalid_records}]")

    assert result.total_records == MAX_SKIPPED_DETAILS + 7
    assert result.skipped_records == MAX_SKIPPED_DETAILS + 7
    assert len(result.skipped_entries) == MAX_SKIPPED_DETAILS


def test_database_batches_flush_on_byte_budget_before_record_limit(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    source_path = tmp_path / "large-records.json"
    message = "ä" * 100
    source_path.write_text(
        "["
        + ",".join(
            (
                '{"ticket_id":"T-%d","message_group_id":"G-%d",'
                '"message":"%s","answer":"A"}'
            )
            % (index, index, message)
            for index in range(3)
        )
        + "]",
        encoding="utf-8",
    )
    service = ImportService()
    one_record_bytes = service._record_size_bytes(
        next(service._iter_valid_record_batches("json", source_path))[0]
    )
    monkeypatch.setattr(import_service_module, "DATABASE_BATCH_SIZE", 1_000)
    monkeypatch.setattr(
        import_service_module,
        "DATABASE_BATCH_BYTES",
        one_record_bytes * 2,
    )

    batches = list(service._iter_valid_record_batches("json", source_path))

    assert [len(batch) for batch in batches] == [2, 1]
    assert sum(len(batch) for batch in batches) == 3


def test_one_record_over_byte_budget_is_flushed_without_accumulating_another(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    source_path = tmp_path / "oversized-record.json"
    source_path.write_text(
        "["
        '{"ticket_id":"T-1","message_group_id":"G-1",'
        f'"message":"{"x" * 1_000}","answer":"A"}},'
        '{"ticket_id":"T-2","message_group_id":"G-2",'
        '"message":"small","answer":"A"}'
        "]",
        encoding="utf-8",
    )
    monkeypatch.setattr(import_service_module, "DATABASE_BATCH_SIZE", 1_000)
    monkeypatch.setattr(import_service_module, "DATABASE_BATCH_BYTES", 512)

    batches = list(ImportService()._iter_valid_record_batches("json", source_path))

    assert [len(batch) for batch in batches] == [1, 1]
