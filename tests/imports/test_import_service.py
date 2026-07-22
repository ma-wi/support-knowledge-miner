from __future__ import annotations

from backend.imports.service import ImportService


def test_csv_parser_accepts_duplicates_and_skips_invalid_records() -> None:
    result = ImportService()._parse(
        "csv",
        "ticketid,messagegroupid,message,answer\n"
        "T-1,G-1,Hello,Answer\n"
        "T-1,G-1,Duplicate,Answer 2\n"
        "T-2,G-2,   ,Missing message\n",
    )

    assert result["status"] == "completed"
    assert result["total_records"] == 3
    assert len(result["valid_records"]) == 2
    assert len(result["skipped_entries"]) == 1
    assert result["skipped_entries"][0].reason == "message must not be empty"


def test_csv_parser_fails_missing_headers_before_dataset_creation() -> None:
    result = ImportService()._parse("csv", "ticketid,message,answer\nT-1,Hi,A\n")

    assert result["status"] == "failed"
    assert result["failure_reason"] == "missing CSV headers: messagegroupid"
    assert result["total_records"] == 0
    assert result["valid_records"] == []


def test_json_parser_requires_list_root_and_validates_records() -> None:
    failed = ImportService()._parse("json", '{"ticketid": "T-1"}')
    assert failed["status"] == "failed"
    assert failed["failure_reason"] == "JSON root must be a list"

    imported = ImportService()._parse(
        "json",
        "["
        '{"ticketid":"T-1","messagegroupid":"G-1","message":"Hi","answer":"A"},'
        '{"ticketid":"T-2","messagegroupid":"G-2","message":"Hi","answer":""}'
        "]",
    )
    assert imported["status"] == "completed"
    assert len(imported["valid_records"]) == 1
    assert imported["skipped_entries"][0].reason == "answer must not be empty"


def test_zero_valid_records_reports_failed_without_dataset() -> None:
    result = ImportService()._parse(
        "json",
        '[{"ticketid":"T-1","messagegroupid":"G-1","message":"","answer":""}]',
    )

    assert result["status"] == "failed"
    assert result["failure_reason"] == "no valid records found"
    assert result["total_records"] == 1
    assert len(result["skipped_entries"]) == 1
