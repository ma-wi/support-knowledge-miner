from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest

import backend.candidates.service as candidate_service_module
from backend.candidates import CandidateManualUpdate, CandidateService

ACTOR_ID = UUID("11111111-1111-1111-1111-111111111111")
PROJECT_ID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
RUN_ID = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
LATER_RUN_ID = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbc")
DATASET_ID = UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
CLUSTER_ID = UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")
PAIR_A = UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeea")
PAIR_B = UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeeb")
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


class CandidateConnection:
    def __init__(self) -> None:
        self.candidates: list[dict[str, object]] = []
        self.assignments: list[dict[str, object]] = []
        self.audit_events: list[str] = []
        self.cluster = {
            "id": CLUSTER_ID,
            "project_id": PROJECT_ID,
            "analysis_run_id": RUN_ID,
            "dataset_version_id": DATASET_ID,
            "auto_title": "Cluster Reset",
            "manual_title": None,
            "auto_category": "account/reset",
            "manual_category": None,
            "score": 0.82,
            "is_outlier": False,
        }
        self.sources = [
            {
                "message_pair_id": PAIR_A,
                "membership_score": 0.82,
                "message": "How do I reset my password?",
                "answer": "Use the reset link.",
                "ticket_id": "T-1",
                "message_group_id": "G-1",
            },
            {
                "message_pair_id": PAIR_B,
                "membership_score": 0.75,
                "message": "Password reset failed",
                "answer": "Request a new reset link.",
                "ticket_id": "T-2",
                "message_group_id": "G-2",
            },
        ]

    def __enter__(self) -> CandidateConnection:
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def transaction(self) -> FakeTransaction:
        return FakeTransaction()

    def execute(
        self, query: str, params: tuple[object, ...] | None = None
    ) -> FakeResult:
        normalized = " ".join(query.split())
        if normalized.startswith("SELECT id FROM candidates"):
            assert params is not None
            existing = [
                {"id": candidate["id"]}
                for candidate in self.candidates
                if candidate["project_id"] == params[0]
                and candidate["source_cluster_id"] == params[1]
            ]
            return FakeResult(existing[:1])
        if normalized.startswith("SELECT id, project_id, analysis_run_id"):
            return FakeResult([self.cluster])
        if normalized.startswith("SELECT cm.message_pair_id"):
            return FakeResult(self.sources)
        if normalized.startswith("INSERT INTO candidates"):
            assert params is not None
            self.candidates.append(
                {
                    "id": params[0],
                    "project_id": params[1],
                    "dataset_version_id": params[2],
                    "analysis_run_id": params[3],
                    "source_cluster_id": params[4],
                    "candidate_type": params[5],
                    "auto_status": "unreviewed",
                    "manual_status": None,
                    "language": "de",
                    "auto_category_path": params[6],
                    "manual_category_path": None,
                    "auto_title": params[7],
                    "manual_title": None,
                    "auto_canonical_question": params[8],
                    "manual_canonical_question": None,
                    "auto_canonical_answer": params[9],
                    "manual_canonical_answer": None,
                    "auto_alternative_questions": unwrap_json(params[10]),
                    "manual_alternative_questions": None,
                    "auto_parameters": {},
                    "manual_parameters": None,
                    "auto_external_data_dependencies": [],
                    "manual_external_data_dependencies": None,
                    "quality_score": params[11],
                    "faq_suitability_score": params[12],
                    "dynamicity_score": params[13],
                    "contradiction_score": 0.0,
                    "notes": None,
                    "metadata": unwrap_json(params[14]),
                    "created_at": NOW,
                    "updated_at": NOW,
                }
            )
            return FakeResult()
        if normalized.startswith("INSERT INTO candidate_source_assignments"):
            assert params is not None
            self.assignments.append(
                {
                    "candidate_id": params[2],
                    "cluster_id": params[3],
                    "message_pair_id": params[4],
                    "dataset_version_id": params[5],
                    "analysis_run_id": params[6],
                    "normalized_customer_message": params[7],
                    "normalized_support_answer": params[8],
                    "assignment_type": "automatic",
                    "membership_score": params[9],
                }
            )
            return FakeResult()
        if normalized.startswith("INSERT INTO audit_events"):
            self.audit_events.append(str(params))
            return FakeResult()
        if normalized.startswith("SELECT c.id, c.project_id"):
            rows = [self._candidate_row(candidate) for candidate in self.candidates]
            if "AND c.id =" in normalized:
                assert params is not None
                rows = [row for row in rows if row["id"] == params[1]]
            return FakeResult(rows)
        if normalized.startswith("UPDATE candidates"):
            assert params is not None
            for candidate in self.candidates:
                if (
                    candidate["id"] == params[20]
                    and candidate["project_id"] == params[21]
                ):
                    updates = {
                        "candidate_type": (params[0], params[1]),
                        "manual_status": (params[2], params[3]),
                        "manual_category_path": (params[4], params[5]),
                        "manual_title": (params[6], params[7]),
                        "manual_canonical_question": (params[8], params[9]),
                        "manual_canonical_answer": (params[10], params[11]),
                        "manual_alternative_questions": (
                            params[12],
                            unwrap_json(params[13]),
                        ),
                        "manual_parameters": (params[14], unwrap_json(params[15])),
                        "manual_external_data_dependencies": (
                            params[16],
                            unwrap_json(params[17]),
                        ),
                        "notes": (params[18], params[19]),
                    }
                    for field, (should_update, value) in updates.items():
                        if should_update:
                            if field == "candidate_type" and value is None:
                                continue
                            candidate[field] = value
                    candidate["updated_at"] = NOW
                    return FakeResult([{"id": candidate["id"]}])
            return FakeResult()
        if normalized.startswith("SELECT csa.candidate_id"):
            rows = []
            for assignment in self.assignments:
                for source in self.sources:
                    if source["message_pair_id"] == assignment["message_pair_id"]:
                        rows.append(
                            {
                                **assignment,
                                "ticket_id": source["ticket_id"],
                                "message_group_id": source["message_group_id"],
                                "message": source["message"],
                                "answer": source["answer"],
                                "message_segment_id": None,
                                "source_language": "unknown",
                                "is_multi_intent": False,
                                "intent_label": None,
                            }
                        )
            return FakeResult(rows)
        raise AssertionError(f"unexpected query: {normalized}")

    def _candidate_row(self, candidate: dict[str, object]) -> dict[str, object]:
        source_cluster_ids = sorted(
            {
                str(assignment["cluster_id"])
                for assignment in self.assignments
                if assignment["candidate_id"] == candidate["id"]
                and assignment["cluster_id"] is not None
            }
        )
        return {
            **candidate,
            "source_pair_count": sum(
                1
                for assignment in self.assignments
                if assignment["candidate_id"] == candidate["id"]
            ),
            "source_cluster_ids": source_cluster_ids,
        }


def unwrap_json(value: object) -> object:
    return getattr(value, "obj", value)


def test_create_from_cluster_preserves_generated_manual_and_sources(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_connection = CandidateConnection()
    monkeypatch.setattr(
        candidate_service_module,
        "open_database_connection",
        lambda _: fake_connection,
    )

    candidate = CandidateService().create_from_cluster(
        PROJECT_ID, CLUSTER_ID, actor_user_id=ACTOR_ID
    )

    assert candidate.candidate_type == "static_faq"
    assert candidate.auto_title == "Cluster Reset"
    assert candidate.manual_title is None
    assert candidate.effective_title == "Cluster Reset"
    assert candidate.auto_canonical_question == "How do I reset my password?"
    assert candidate.auto_alternative_questions == ["Password reset failed"]
    assert candidate.source_pair_count == 2
    assert candidate.source_cluster_ids == [CLUSTER_ID]
    assert len(fake_connection.assignments) == 2
    assert fake_connection.audit_events


def test_manual_candidate_curation_survives_later_analysis_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_connection = CandidateConnection()
    monkeypatch.setattr(
        candidate_service_module,
        "open_database_connection",
        lambda _: fake_connection,
    )
    service = CandidateService()
    created = service.create_from_cluster(
        PROJECT_ID, CLUSTER_ID, actor_user_id=ACTOR_ID
    )

    updated = service.update_candidate(
        PROJECT_ID,
        created.id,
        CandidateManualUpdate(
            candidate_type="parameterized_faq",
            manual_status="export_ready",
            manual_category_path="Account / Password",
            manual_title="Password reset FAQ",
            manual_canonical_question="How can customers reset passwords?",
            manual_canonical_answer="Send a reset link and ask for a retry.",
            manual_alternative_questions=["Password reset does not work"],
            manual_parameters={"account_id": "optional"},
            manual_external_data_dependencies=["identity-service"],
            notes="Reviewed by curation.",
        ),
        actor_user_id=ACTOR_ID,
    )
    fake_connection.cluster = {
        **fake_connection.cluster,
        "analysis_run_id": LATER_RUN_ID,
    }

    reopened = service.list_candidates(PROJECT_ID)[0]

    assert updated.auto_title == "Cluster Reset"
    assert reopened.candidate_type == "parameterized_faq"
    assert reopened.manual_status == "export_ready"
    assert reopened.effective_title == "Password reset FAQ"
    assert reopened.effective_canonical_question == "How can customers reset passwords?"
    assert (
        reopened.effective_canonical_answer == "Send a reset link and ask for a retry."
    )
    assert reopened.effective_parameters == {"account_id": "optional"}
    assert reopened.effective_external_data_dependencies == ["identity-service"]
    assert reopened.source_pair_count == 2


def test_status_only_update_preserves_generated_multi_value_effective_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_connection = CandidateConnection()
    monkeypatch.setattr(
        candidate_service_module,
        "open_database_connection",
        lambda _: fake_connection,
    )
    service = CandidateService()
    created = service.create_from_cluster(
        PROJECT_ID, CLUSTER_ID, actor_user_id=ACTOR_ID
    )
    fake_connection.candidates[0]["auto_parameters"] = {"account_id": "optional"}
    fake_connection.candidates[0]["auto_external_data_dependencies"] = [
        "identity-service"
    ]

    updated = service.update_candidate(
        PROJECT_ID,
        created.id,
        CandidateManualUpdate(
            manual_status="in_progress",
            notes="Reviewed without touching generated multi-value fields.",
        ),
        actor_user_id=ACTOR_ID,
    )

    assert updated.manual_alternative_questions is None
    assert updated.effective_alternative_questions == ["Password reset failed"]
    assert updated.manual_parameters is None
    assert updated.effective_parameters == {"account_id": "optional"}
    assert updated.manual_external_data_dependencies is None
    assert updated.effective_external_data_dependencies == ["identity-service"]


def test_partial_update_preserves_existing_manual_curation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_connection = CandidateConnection()
    monkeypatch.setattr(
        candidate_service_module,
        "open_database_connection",
        lambda _: fake_connection,
    )
    service = CandidateService()
    created = service.create_from_cluster(
        PROJECT_ID, CLUSTER_ID, actor_user_id=ACTOR_ID
    )
    service.update_candidate(
        PROJECT_ID,
        created.id,
        CandidateManualUpdate(
            manual_title="Curated title",
            manual_canonical_question="Curated question?",
            manual_parameters={"account_id": "required"},
            fields_to_update=frozenset(
                {
                    "manual_title",
                    "manual_canonical_question",
                    "manual_parameters",
                }
            ),
        ),
        actor_user_id=ACTOR_ID,
    )

    updated = service.update_candidate(
        PROJECT_ID,
        created.id,
        CandidateManualUpdate(
            manual_status="in_progress",
            notes="Only status and notes changed.",
            fields_to_update=frozenset({"manual_status", "notes"}),
        ),
        actor_user_id=ACTOR_ID,
    )

    assert updated.manual_status == "in_progress"
    assert updated.manual_title == "Curated title"
    assert updated.effective_title == "Curated title"
    assert updated.manual_canonical_question == "Curated question?"
    assert updated.manual_parameters == {"account_id": "required"}
    assert updated.effective_parameters == {"account_id": "required"}
    assert updated.notes == "Only status and notes changed."


def test_explicit_null_clears_existing_manual_curation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_connection = CandidateConnection()
    monkeypatch.setattr(
        candidate_service_module,
        "open_database_connection",
        lambda _: fake_connection,
    )
    service = CandidateService()
    created = service.create_from_cluster(
        PROJECT_ID, CLUSTER_ID, actor_user_id=ACTOR_ID
    )
    service.update_candidate(
        PROJECT_ID,
        created.id,
        CandidateManualUpdate(
            manual_title="Curated title",
            manual_parameters={"account_id": "required"},
            fields_to_update=frozenset({"manual_title", "manual_parameters"}),
        ),
        actor_user_id=ACTOR_ID,
    )

    updated = service.update_candidate(
        PROJECT_ID,
        created.id,
        CandidateManualUpdate(
            manual_title=None,
            manual_parameters=None,
            fields_to_update=frozenset({"manual_title", "manual_parameters"}),
        ),
        actor_user_id=ACTOR_ID,
    )

    assert updated.manual_title is None
    assert updated.effective_title == "Cluster Reset"
    assert updated.manual_parameters is None
    assert updated.effective_parameters == {}


def test_candidate_source_traceability_reaches_original_pair_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_connection = CandidateConnection()
    monkeypatch.setattr(
        candidate_service_module,
        "open_database_connection",
        lambda _: fake_connection,
    )
    service = CandidateService()
    candidate = service.create_from_cluster(
        PROJECT_ID, CLUSTER_ID, actor_user_id=ACTOR_ID
    )

    sources = service.list_sources(PROJECT_ID, candidate.id)

    assert sources[0].ticket_id == "T-1"
    assert sources[0].message_group_id == "G-1"
    assert sources[0].message == "How do I reset my password?"
    assert sources[0].answer == "Use the reset link."
    assert sources[0].cluster_id == CLUSTER_ID
    assert sources[0].dataset_version_id == DATASET_ID
    assert sources[0].analysis_run_id == RUN_ID
