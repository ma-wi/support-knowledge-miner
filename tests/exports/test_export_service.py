from __future__ import annotations

import csv
from datetime import UTC, datetime
from io import StringIO
from uuid import UUID

import pytest

import backend.exports.service as export_service_module
from backend.candidates import Candidate, CandidateSource
from backend.exports import ExportService
from backend.exports.service import CANDIDATE_CSV_COLUMNS, SOURCE_ASSIGNMENT_CSV_COLUMNS

ACTOR_ID = UUID("11111111-1111-1111-1111-111111111111")
PROJECT_ID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
RUN_ID = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
DATASET_ID = UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
CLUSTER_ID = UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")
CANDIDATE_ID = UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee")
PAIR_ID = UUID("ffffffff-ffff-ffff-ffff-ffffffffffff")
NOW = datetime(2026, 7, 23, 12, 0, tzinfo=UTC)


class FakeResult:
    def __init__(self, rows: list[dict[str, object]] | None = None) -> None:
        self._rows = rows or []

    def fetchone(self) -> dict[str, object] | None:
        return self._rows[0] if self._rows else None

    def fetchall(self) -> list[dict[str, object]]:
        return self._rows


class FakeTransaction:
    def __enter__(self) -> FakeTransaction:
        return self

    def __exit__(self, *_: object) -> None:
        return None


class ExportConnection:
    def __init__(self) -> None:
        self.export_logs: list[dict[str, object]] = []
        self.audit_events: list[str] = []

    def __enter__(self) -> ExportConnection:
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def transaction(self) -> FakeTransaction:
        return FakeTransaction()

    def execute(
        self, query: str, params: tuple[object, ...] | None = None
    ) -> FakeResult:
        normalized = " ".join(query.split())
        if normalized.startswith("INSERT INTO export_logs"):
            assert params is not None
            row = {
                "id": params[0],
                "project_id": params[1],
                "export_type": params[2],
                "include_original_text": params[3],
                "filters": unwrap_json(params[4]),
                "selection": unwrap_json(params[5]),
                "dataset_version_id": params[6],
                "analysis_run_id": params[7],
                "output_filename": params[8],
                "output_path": None,
                "row_count": params[9],
                "created_by_user_id": params[10],
                "created_at": NOW,
            }
            self.export_logs.append(row)
            return FakeResult([row])
        if normalized.startswith("INSERT INTO audit_events"):
            self.audit_events.append(str(params))
            return FakeResult()
        if normalized.startswith("SELECT id, project_id, export_type"):
            return FakeResult(list(reversed(self.export_logs)))
        raise AssertionError(f"unexpected query: {normalized}")


def unwrap_json(value: object) -> object:
    return getattr(value, "obj", value)


class FakeCandidateService:
    def list_candidates(self, project_id: UUID) -> list[Candidate]:
        assert project_id == PROJECT_ID
        return [candidate()]

    def list_sources(
        self, project_id: UUID, candidate_id: UUID
    ) -> list[CandidateSource]:
        assert project_id == PROJECT_ID
        assert candidate_id == CANDIDATE_ID
        return [candidate_source()]


def candidate() -> Candidate:
    return Candidate(
        id=CANDIDATE_ID,
        project_id=PROJECT_ID,
        dataset_version_id=DATASET_ID,
        analysis_run_id=RUN_ID,
        source_cluster_id=CLUSTER_ID,
        candidate_type="parameterized_faq",
        auto_status="unreviewed",
        manual_status="export_ready",
        effective_status="export_ready",
        language="de",
        auto_category_path="account/reset",
        manual_category_path="Account",
        effective_category_path="Account",
        auto_title="Cluster H",
        manual_title="Reset, FAQ",
        effective_title="Reset, FAQ",
        auto_canonical_question="How do I reset it?",
        manual_canonical_question="How can customers reset passwords?",
        effective_canonical_question="How can customers reset passwords?",
        auto_canonical_answer="Use the reset link.",
        manual_canonical_answer="Send a reset link.",
        effective_canonical_answer="Send a reset link.",
        auto_alternative_questions=["Password reset failed"],
        manual_alternative_questions=["Password reset does not work"],
        effective_alternative_questions=["Password reset does not work"],
        auto_parameters={},
        manual_parameters={"account_id": "required"},
        effective_parameters={"account_id": "required"},
        auto_external_data_dependencies=[],
        manual_external_data_dependencies=["identity-service"],
        effective_external_data_dependencies=["identity-service"],
        quality_score=0.91,
        faq_suitability_score=0.9,
        dynamicity_score=0.1,
        contradiction_score=0.0,
        source_pair_count=1,
        source_cluster_ids=[CLUSTER_ID],
        notes="Reviewed candidate.",
        metadata={},
        created_at=NOW,
        updated_at=NOW,
    )


def candidate_source() -> CandidateSource:
    return CandidateSource(
        candidate_id=CANDIDATE_ID,
        cluster_id=CLUSTER_ID,
        message_pair_id=PAIR_ID,
        ticketid="T-1",
        messagegroupid="G-1",
        message="How do I reset it, please?",
        answer="Use the reset link.",
        message_segment_id=None,
        source_language="en",
        normalized_customer_message="how do i reset it please",
        normalized_support_answer="use the reset link",
        assignment_type="automatic",
        membership_score=0.91,
        is_multi_intent=False,
        intent_label=None,
        dataset_version_id=DATASET_ID,
        analysis_run_id=RUN_ID,
    )


def csv_rows(content: str) -> list[dict[str, str]]:
    return list(csv.DictReader(StringIO(content)))


def test_candidate_export_uses_exact_baseline_columns_and_persists_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_connection = ExportConnection()
    monkeypatch.setattr(
        export_service_module,
        "open_database_connection",
        lambda _: fake_connection,
    )
    service = ExportService()
    service._candidates = FakeCandidateService()  # type: ignore[assignment]

    result = service.export_candidates(
        PROJECT_ID, include_original_text=True, actor_user_id=ACTOR_ID
    )

    header = result.csv_content.splitlines()[0].split(",")
    assert header == CANDIDATE_CSV_COLUMNS
    row = csv_rows(result.csv_content)[0]
    assert row["candidate_id"] == str(CANDIDATE_ID)
    assert row["title"] == "Reset, FAQ"
    assert row["parameters"] == '{"account_id":"required"}'
    assert row["source_cluster_ids"] == f'["{CLUSTER_ID}"]'
    assert row["contains_original_text"] == "true"
    assert result.log.export_type == "candidate_csv"
    assert result.log.include_original_text is True
    assert result.log.row_count == 1
    assert result.warning is not None
    assert fake_connection.export_logs[0]["created_by_user_id"] == ACTOR_ID
    assert fake_connection.audit_events


def test_candidate_export_marks_source_derived_text_even_when_not_requested(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_connection = ExportConnection()
    monkeypatch.setattr(
        export_service_module,
        "open_database_connection",
        lambda _: fake_connection,
    )
    service = ExportService()
    service._candidates = FakeCandidateService()  # type: ignore[assignment]

    result = service.export_candidates(
        PROJECT_ID, include_original_text=False, actor_user_id=ACTOR_ID
    )

    row = csv_rows(result.csv_content)[0]
    assert row["canonical_question"] == "How can customers reset passwords?"
    assert row["canonical_answer"] == "Send a reset link."
    assert row["contains_original_text"] == "true"
    assert result.log.include_original_text is True
    assert result.warning is not None
    assert fake_connection.export_logs[0]["include_original_text"] is True


def test_source_assignment_export_keeps_exact_headers_and_redacts_original_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_connection = ExportConnection()
    monkeypatch.setattr(
        export_service_module,
        "open_database_connection",
        lambda _: fake_connection,
    )
    service = ExportService()
    service._candidates = FakeCandidateService()  # type: ignore[assignment]

    result = service.export_source_assignments(
        PROJECT_ID, include_original_text=False, actor_user_id=ACTOR_ID
    )

    header = result.csv_content.splitlines()[0].split(",")
    assert header == SOURCE_ASSIGNMENT_CSV_COLUMNS
    row = csv_rows(result.csv_content)[0]
    assert row["pair_id"] == str(PAIR_ID)
    assert row["ticketid"] == "T-1"
    assert row["customer_message"] == ""
    assert row["support_answer"] == ""
    assert row["normalized_customer_message"] == "how do i reset it please"
    assert row["is_multi_intent"] == "false"
    assert result.log.export_type == "source_assignment_csv"
    assert result.log.include_original_text is False
    assert result.warning is None


def test_source_assignment_export_includes_original_text_when_requested(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_connection = ExportConnection()
    monkeypatch.setattr(
        export_service_module,
        "open_database_connection",
        lambda _: fake_connection,
    )
    service = ExportService()
    service._candidates = FakeCandidateService()  # type: ignore[assignment]

    result = service.export_source_assignments(
        PROJECT_ID, include_original_text=True, actor_user_id=ACTOR_ID
    )

    row = csv_rows(result.csv_content)[0]
    assert row["customer_message"] == "How do I reset it, please?"
    assert row["support_answer"] == "Use the reset link."
    assert result.log.include_original_text is True
    assert result.warning is not None


def test_lists_export_history_for_project(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_connection = ExportConnection()
    monkeypatch.setattr(
        export_service_module,
        "open_database_connection",
        lambda _: fake_connection,
    )
    service = ExportService()
    service._candidates = FakeCandidateService()  # type: ignore[assignment]
    service.export_candidates(
        PROJECT_ID, include_original_text=False, actor_user_id=ACTOR_ID
    )

    logs = service.list_exports(PROJECT_ID)

    assert len(logs) == 1
    assert logs[0].project_id == PROJECT_ID
    assert logs[0].output_filename.endswith(".csv")
