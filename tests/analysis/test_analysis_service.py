from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest

import backend.analysis.service as analysis_service_module
from backend.analysis import AnalysisRunInput, AnalysisService

ACTOR_ID = UUID("11111111-1111-1111-1111-111111111111")
PROJECT_ID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
DATASET_ID = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
PROFILE_ID = UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
PAIR_ID = UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee")
NOW = datetime(2026, 7, 22, tzinfo=UTC)


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


class AnalysisConnection:
    def __init__(self) -> None:
        self.run: dict[str, object] | None = None
        self.embeddings: list[dict[str, object]] = []

    def __enter__(self) -> AnalysisConnection:
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def transaction(self) -> FakeTransaction:
        return FakeTransaction()

    def execute(
        self, query: str, params: tuple[object, ...] | None = None
    ) -> FakeResult:
        normalized = " ".join(query.split())
        if normalized.startswith("SELECT id, record_count FROM dataset_versions"):
            return FakeResult([{"id": DATASET_ID, "record_count": 1}])
        if normalized.startswith("SELECT id, name, provider, model"):
            return FakeResult(
                [
                    {
                        "id": PROFILE_ID,
                        "name": "Local profile",
                        "provider": "vllm",
                        "model": "local-embed",
                        "is_cloud_provider": False,
                        "thresholds": {"similarity": 0.78},
                        "algorithm_settings": {"algorithm": "fixture"},
                        "prompt_identifier": "faq-v1",
                        "prompt_template": None,
                        "created_at": NOW,
                        "updated_at": NOW,
                    }
                ]
            )
        if normalized.startswith("INSERT INTO analysis_runs"):
            assert params is not None
            self.run = {
                "id": params[0],
                "project_id": params[1],
                "dataset_version_id": params[2],
                "analysis_profile_id": params[3],
                "status": "queued",
                "progress": 0,
                "profile_snapshot": unwrap_json(params[4]),
                "provider": params[5],
                "model": params[6],
                "parameters": unwrap_json(params[7]),
                "error_message": None,
                "diagnostics": {},
                "started_at": None,
                "completed_at": None,
                "created_at": NOW,
                "updated_at": NOW,
            }
            return FakeResult([self.run])
        if normalized.startswith("INSERT INTO audit_events"):
            return FakeResult()
        if normalized.startswith("UPDATE analysis_runs SET status = 'running'"):
            assert self.run is not None
            self.run["status"] = "running"
            self.run["progress"] = 5
            self.run["started_at"] = NOW
            return FakeResult(
                [
                    {
                        "id": self.run["id"],
                        "project_id": self.run["project_id"],
                        "dataset_version_id": self.run["dataset_version_id"],
                        "analysis_profile_id": self.run["analysis_profile_id"],
                        "model": self.run["model"],
                    }
                ]
            )
        if normalized.startswith(
            "SELECT id, ordinal, message, answer FROM message_pairs"
        ):
            return FakeResult(
                [
                    {
                        "id": PAIR_ID,
                        "ordinal": 1,
                        "message": "How do I reset it?",
                        "answer": "Use the reset link.",
                    }
                ]
            )
        if normalized.startswith("INSERT INTO embeddings"):
            assert params is not None
            self.embeddings.append(
                {
                    "id": params[0],
                    "project_id": params[1],
                    "analysis_run_id": params[2],
                    "dataset_version_id": params[3],
                    "analysis_profile_id": params[4],
                    "source_object_id": params[5],
                    "text_variant": params[6],
                    "model": params[7],
                    "dimensions": params[8],
                    "metadata": unwrap_json(params[9]),
                }
            )
            return FakeResult()
        if normalized.startswith("UPDATE analysis_runs SET status = 'completed'"):
            assert params is not None
            assert self.run is not None
            self.run["status"] = "completed"
            self.run["progress"] = 100
            self.run["completed_at"] = NOW
            self.run["diagnostics"] = unwrap_json(params[0])
            return FakeResult()
        if normalized.startswith("SELECT id, project_id, dataset_version_id"):
            assert self.run is not None
            return FakeResult([self.run])
        raise AssertionError(f"unexpected query: {normalized}")


def unwrap_json(value: object) -> object:
    return getattr(value, "obj", value)


def test_start_run_returns_queued_before_background_scaffold_completes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_connection = AnalysisConnection()
    monkeypatch.setattr(
        analysis_service_module,
        "open_database_connection",
        lambda _: fake_connection,
    )

    run = AnalysisService().start_run(
        PROJECT_ID,
        AnalysisRunInput(
            dataset_version_id=DATASET_ID,
            analysis_profile_id=PROFILE_ID,
            parameters={"mode": "fixture"},
        ),
        actor_user_id=ACTOR_ID,
    )

    assert run.status == "queued"
    assert run.progress == 0
    assert run.profile_snapshot["model"] == "local-embed"
    assert run.parameters == {"mode": "fixture"}
    assert fake_connection.embeddings == []

    AnalysisService().execute_queued_run(run.id)
    completed = AnalysisService().get_run(PROJECT_ID, run.id)

    assert completed is not None
    assert completed.status == "completed"
    assert completed.progress == 100
    assert completed.diagnostics["embeddings_written"] == 2
    assert len(fake_connection.embeddings) == 2
    assert {item["text_variant"] for item in fake_connection.embeddings} == {
        "message",
        "answer",
    }
    assert all(item["dimensions"] == 3 for item in fake_connection.embeddings)
    assert all(
        item["source_object_id"] == PAIR_ID for item in fake_connection.embeddings
    )
