from __future__ import annotations

import csv
import json
from datetime import UTC, datetime
from io import StringIO
from uuid import UUID, uuid4

import pytest

import backend.exports.service as export_service_module
from backend.exports import ExplorerExportInput, ExportError, ExportService
from backend.exports.service import EXPLORER_CSV_COLUMNS
from backend.exports.service import MAX_EXPLORER_EXPORT_SELECTION

ACTOR_ID = UUID("11111111-1111-1111-1111-111111111111")
PROJECT_ID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
RUN_ID = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
DATASET_ID = UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
CLUSTER_SET_ID = UUID("99999999-9999-9999-9999-999999999999")
CLUSTER_ID = UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")
EXCLUDED_CLUSTER_ID = UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee")
UNKNOWN_CLUSTER_ID = UUID("ffffffff-ffff-ffff-ffff-ffffffffffff")
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
        self.cluster_set: dict[str, object] | None = {
            "id": CLUSTER_SET_ID,
            "project_id": PROJECT_ID,
            "dataset_version_id": DATASET_ID,
            "indexing_run_id": RUN_ID,
            "status": "completed",
            "vector_basis": "combined",
            "algorithm": "hdbscan",
        }
        self.clusters: list[dict[str, object]] = [
            cluster_row(CLUSTER_ID),
            cluster_row(
                EXCLUDED_CLUSTER_ID,
                manual_status="rejected",
                auto_title="Billing issue",
                auto_category="billing",
                summary_question="Why was I charged?",
            ),
        ]
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
        if normalized.startswith("SELECT id, project_id, dataset_version_id"):
            assert params == (CLUSTER_SET_ID, PROJECT_ID)
            return FakeResult([] if self.cluster_set is None else [self.cluster_set])
        if normalized.startswith("SELECT c.id, c.project_id, c.analysis_run_id"):
            assert params == (PROJECT_ID, CLUSTER_SET_ID)
            return FakeResult(self.clusters)
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
                "cluster_set_id": params[8],
                "output_filename": params[9],
                "output_path": None,
                "row_count": params[10],
                "created_by_user_id": params[11],
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


def cluster_row(
    cluster_id: UUID,
    *,
    manual_status: str | None = None,
    auto_title: str = "Password reset",
    auto_category: str = "account",
    summary_question: str = "How can customers reset passwords?",
) -> dict[str, object]:
    return {
        "id": cluster_id,
        "project_id": PROJECT_ID,
        "analysis_run_id": RUN_ID,
        "dataset_version_id": DATASET_ID,
        "cluster_set_id": CLUSTER_SET_ID,
        "auto_title": auto_title,
        "manual_title": None,
        "auto_category": auto_category,
        "manual_category": None,
        "auto_status": "unreviewed",
        "manual_status": manual_status,
        "auto_summary_question": summary_question,
        "auto_summary_answer": "Send the reset link.",
        "keywords": ["password", "reset link"],
        "score": 0.91,
        "is_outlier": False,
        "algorithm": "hdbscan",
        "metadata": {"qa_mismatch": {"average": 0.12, "maximum": 0.31}},
        "created_at": NOW,
        "updated_at": NOW,
        "member_count": 3,
    }


def csv_rows(content: str) -> list[dict[str, str]]:
    return list(csv.DictReader(StringIO(content)))


def test_explorer_csv_export_filters_visible_rows_and_persists_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_connection = ExportConnection()
    monkeypatch.setattr(
        export_service_module,
        "open_database_connection",
        lambda _: fake_connection,
    )

    result = ExportService().export_explorer(
        PROJECT_ID,
        ExplorerExportInput(
            cluster_set_id=CLUSTER_SET_ID,
            export_format="csv",
            search_query="reset",
            cluster_ids=[CLUSTER_ID],
        ),
        actor_user_id=ACTOR_ID,
    )

    assert result.content_type == "text/csv"
    assert result.content.splitlines()[0].split(",") == EXPLORER_CSV_COLUMNS
    row = csv_rows(result.content)[0]
    assert row["cluster_set_id"] == str(CLUSTER_SET_ID)
    assert row["cluster_id"] == str(CLUSTER_ID)
    assert row["title"] == "Password reset"
    assert row["customer_question_count"] == "3"
    assert row["support_answer_count"] == "3"
    assert row["mismatch_maximum"] == "0.31"
    assert row["keywords"] == '["password","reset link"]'
    assert result.log.export_type == "explorer_csv"
    assert result.log.cluster_set_id == CLUSTER_SET_ID
    assert result.log.include_original_text is False
    assert result.log.row_count == 1
    assert fake_connection.export_logs[0]["created_by_user_id"] == ACTOR_ID
    assert "reset" not in "".join(fake_connection.audit_events)


def test_explorer_csv_export_neutralizes_formula_cells(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_connection = ExportConnection()
    fake_connection.clusters = [
        cluster_row(
            CLUSTER_ID,
            auto_title=' =HYPERLINK("http://attacker.test")',
            auto_category="+billing",
            summary_question='\t=IMPORTXML("http://attacker.test")',
        )
        | {
            "auto_summary_answer": "\r@unsafe",
        }
    ]
    monkeypatch.setattr(
        export_service_module,
        "open_database_connection",
        lambda _: fake_connection,
    )

    result = ExportService().export_explorer(
        PROJECT_ID,
        ExplorerExportInput(cluster_set_id=CLUSTER_SET_ID),
        actor_user_id=ACTOR_ID,
    )

    row = csv_rows(result.content)[0]
    assert row["title"].startswith("' =HYPERLINK")
    assert row["category"] == "'+billing"
    assert row["summary_question"].startswith("'\t=IMPORTXML")
    assert row["summary_answer"].startswith("'\r@unsafe")


def test_explorer_json_export_uses_visible_table_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_connection = ExportConnection()
    monkeypatch.setattr(
        export_service_module,
        "open_database_connection",
        lambda _: fake_connection,
    )

    result = ExportService().export_explorer(
        PROJECT_ID,
        ExplorerExportInput(
            cluster_set_id=CLUSTER_SET_ID,
            export_format="json",
            include_excluded=True,
        ),
        actor_user_id=ACTOR_ID,
    )

    payload = json.loads(result.content)
    assert result.content_type == "application/json"
    assert result.log.export_type == "explorer_json"
    assert len(payload["rows"]) == 2
    assert payload["rows"][0]["summary_answer"] == "Send the reset link."
    assert "customer_message" not in payload["rows"][0]
    assert payload["filters"]["include_excluded"] is True


def test_explorer_export_empty_filter_raises_catalogued_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_connection = ExportConnection()
    monkeypatch.setattr(
        export_service_module,
        "open_database_connection",
        lambda _: fake_connection,
    )

    with pytest.raises(ExportError) as error:
        ExportService().export_explorer(
            PROJECT_ID,
            ExplorerExportInput(
                cluster_set_id=CLUSTER_SET_ID,
                export_format="csv",
                category="missing",
            ),
            actor_user_id=ACTOR_ID,
        )

    assert error.value.code == "EXPLORER_EXPORT_EMPTY"
    assert error.value.status_code == 422
    assert fake_connection.export_logs == []


def test_explorer_export_rejects_unsupported_format_with_validation_code() -> None:
    with pytest.raises(ExportError) as error:
        ExportService().export_explorer(
            PROJECT_ID,
            ExplorerExportInput(
                cluster_set_id=CLUSTER_SET_ID,
                export_format="xlsx",
            ),
            actor_user_id=ACTOR_ID,
        )

    assert error.value.code == "EXPLORER_EXPORT_FORMAT_INVALID"
    assert error.value.status_code == 422
    assert error.value.suggested_action == "choose-format"
    assert error.value.field_errors == {
        "export_format": "Export format must be csv or json."
    }


def test_explorer_export_rejects_oversized_selection_with_validation_code() -> None:
    with pytest.raises(ExportError) as error:
        ExportService().export_explorer(
            PROJECT_ID,
            ExplorerExportInput(
                cluster_set_id=CLUSTER_SET_ID,
                cluster_ids=[uuid4() for _ in range(MAX_EXPLORER_EXPORT_SELECTION + 1)],
            ),
            actor_user_id=ACTOR_ID,
        )

    assert error.value.code == "EXPLORER_EXPORT_SELECTION_TOO_LARGE"
    assert error.value.status_code == 422
    assert error.value.suggested_action == "reduce-scope"
    assert error.value.field_errors == {"cluster_ids": "Too many selected clusters."}


def test_explorer_export_rejects_unknown_selected_cluster(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_connection = ExportConnection()
    monkeypatch.setattr(
        export_service_module,
        "open_database_connection",
        lambda _: fake_connection,
    )

    with pytest.raises(ExportError) as error:
        ExportService().export_explorer(
            PROJECT_ID,
            ExplorerExportInput(
                cluster_set_id=CLUSTER_SET_ID,
                export_format="csv",
                cluster_ids=[UNKNOWN_CLUSTER_ID],
            ),
            actor_user_id=ACTOR_ID,
        )

    assert error.value.code == "CLUSTER_SET_NOT_FOUND"
    assert error.value.status_code == 404


def test_lists_explorer_export_history_for_project(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_connection = ExportConnection()
    monkeypatch.setattr(
        export_service_module,
        "open_database_connection",
        lambda _: fake_connection,
    )
    service = ExportService()
    service.export_explorer(
        PROJECT_ID,
        ExplorerExportInput(cluster_set_id=CLUSTER_SET_ID, export_format="csv"),
        actor_user_id=ACTOR_ID,
    )

    logs = service.list_exports(PROJECT_ID)

    assert len(logs) == 1
    assert logs[0].project_id == PROJECT_ID
    assert logs[0].cluster_set_id == CLUSTER_SET_ID
    assert logs[0].output_filename.endswith(".csv")
