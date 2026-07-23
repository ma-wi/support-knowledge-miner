from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from backend.api import create_app
from backend.auth import CurrentUser
from backend.auth.service import AuthenticationError
from backend.candidates import Candidate, CandidateManualUpdate, CandidateSource

OWNER_ID = UUID("11111111-1111-1111-1111-111111111111")
PROJECT_ID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
RUN_ID = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
DATASET_ID = UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
CLUSTER_ID = UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")
CANDIDATE_ID = UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee")
PAIR_ID = UUID("ffffffff-ffff-ffff-ffff-ffffffffffff")
NOW = datetime(2026, 7, 22, tzinfo=UTC)


class FakeAuthService:
    def seed_initial_user_from_env(self) -> None:
        return None

    def authenticate_token(self, token: str) -> CurrentUser:
        if token != "valid-token":
            raise AuthenticationError("invalid or expired session")
        return CurrentUser(
            id=OWNER_ID,
            username="owner",
            first_name="Local",
            last_name="Owner",
            email="owner@example.test",
            created_at=NOW,
            updated_at=NOW,
            session_id=uuid4(),
        )


class FakeCandidateService:
    def __init__(self) -> None:
        self.created_by: UUID | None = None
        self.updated_by: UUID | None = None
        self.last_update: CandidateManualUpdate | None = None
        self.candidate = self._candidate()

    def create_from_cluster(
        self, project_id: UUID, cluster_id: UUID, *, actor_user_id: UUID
    ) -> Candidate:
        assert project_id == PROJECT_ID
        assert cluster_id == CLUSTER_ID
        self.created_by = actor_user_id
        return self.candidate

    def list_candidates(self, project_id: UUID) -> list[Candidate]:
        assert project_id == PROJECT_ID
        return [self.candidate]

    def update_candidate(
        self,
        project_id: UUID,
        candidate_id: UUID,
        payload: CandidateManualUpdate,
        *,
        actor_user_id: UUID,
    ) -> Candidate:
        assert project_id == PROJECT_ID
        assert candidate_id == CANDIDATE_ID
        self.updated_by = actor_user_id
        self.last_update = payload
        fields_to_update = payload.fields_to_update or frozenset()
        self.candidate = self._candidate(
            candidate_type=(
                payload.candidate_type
                if "candidate_type" in fields_to_update
                and payload.candidate_type is not None
                else self.candidate.candidate_type
            ),
            manual_title=(
                payload.manual_title
                if "manual_title" in fields_to_update
                else self.candidate.manual_title
            ),
            manual_status=(
                payload.manual_status
                if "manual_status" in fields_to_update
                else self.candidate.manual_status
            ),
            manual_question=(
                payload.manual_canonical_question
                if "manual_canonical_question" in fields_to_update
                else self.candidate.manual_canonical_question
            ),
            manual_answer=(
                payload.manual_canonical_answer
                if "manual_canonical_answer" in fields_to_update
                else self.candidate.manual_canonical_answer
            ),
            manual_parameters=(
                payload.manual_parameters
                if "manual_parameters" in fields_to_update
                else self.candidate.manual_parameters
            ),
            notes=payload.notes
            if "notes" in fields_to_update
            else self.candidate.notes,
        )
        return self.candidate

    def list_sources(
        self, project_id: UUID, candidate_id: UUID
    ) -> list[CandidateSource]:
        assert project_id == PROJECT_ID
        assert candidate_id == CANDIDATE_ID
        return [
            CandidateSource(
                candidate_id=CANDIDATE_ID,
                cluster_id=CLUSTER_ID,
                message_pair_id=PAIR_ID,
                ticketid="T-1",
                messagegroupid="G-1",
                message="How do I reset it?",
                answer="Use the reset link.",
                message_segment_id=None,
                source_language="unknown",
                normalized_customer_message="how do i reset it?",
                normalized_support_answer="use the reset link.",
                assignment_type="automatic",
                membership_score=0.91,
                is_multi_intent=False,
                intent_label=None,
                dataset_version_id=DATASET_ID,
                analysis_run_id=RUN_ID,
            )
        ]

    def _candidate(
        self,
        *,
        candidate_type: str = "static_faq",
        manual_title: str | None = None,
        manual_status: str | None = None,
        manual_question: str | None = None,
        manual_answer: str | None = None,
        manual_parameters: dict[str, object] | None = None,
        notes: str | None = None,
    ) -> Candidate:
        return Candidate(
            id=CANDIDATE_ID,
            project_id=PROJECT_ID,
            dataset_version_id=DATASET_ID,
            analysis_run_id=RUN_ID,
            source_cluster_id=CLUSTER_ID,
            candidate_type=candidate_type,
            auto_status="unreviewed",
            manual_status=manual_status,
            effective_status=manual_status or "unreviewed",
            language="de",
            auto_category_path="account/reset",
            manual_category_path=None,
            effective_category_path="account/reset",
            auto_title="Cluster H",
            manual_title=manual_title,
            effective_title=manual_title or "Cluster H",
            auto_canonical_question="How do I reset it?",
            manual_canonical_question=manual_question,
            effective_canonical_question=manual_question or "How do I reset it?",
            auto_canonical_answer="Use the reset link.",
            manual_canonical_answer=manual_answer,
            effective_canonical_answer=manual_answer or "Use the reset link.",
            auto_alternative_questions=["Password reset failed"],
            manual_alternative_questions=None,
            effective_alternative_questions=["Password reset failed"],
            auto_parameters={"account_id": "optional"},
            manual_parameters=manual_parameters,
            effective_parameters=manual_parameters or {"account_id": "optional"},
            auto_external_data_dependencies=[],
            manual_external_data_dependencies=None,
            effective_external_data_dependencies=[],
            quality_score=0.91,
            faq_suitability_score=0.91,
            dynamicity_score=0.0,
            contradiction_score=0.0,
            source_pair_count=1,
            source_cluster_ids=[CLUSTER_ID],
            notes=notes,
            metadata={"generated_from": "cluster"},
            created_at=NOW,
            updated_at=NOW,
        )


def auth_headers(token: str = "valid-token") -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_candidate_routes_require_authentication() -> None:
    client = TestClient(
        create_app(
            auth_service=FakeAuthService(),  # type: ignore[arg-type]
            candidate_service=FakeCandidateService(),  # type: ignore[arg-type]
        )
    )

    assert client.get(f"/api/projects/{PROJECT_ID}/candidates").status_code == 401
    assert (
        client.post(
            f"/api/projects/{PROJECT_ID}/clusters/{CLUSTER_ID}/candidates"
        ).status_code
        == 401
    )


def test_candidate_api_creates_updates_lists_and_exposes_sources() -> None:
    fake_service = FakeCandidateService()
    client = TestClient(
        create_app(
            auth_service=FakeAuthService(),  # type: ignore[arg-type]
            candidate_service=fake_service,  # type: ignore[arg-type]
        )
    )

    created = client.post(
        f"/api/projects/{PROJECT_ID}/clusters/{CLUSTER_ID}/candidates",
        headers=auth_headers(),
    )
    assert created.status_code == 201
    assert created.json()["auto_title"] == "Cluster H"
    assert created.json()["effective_title"] == "Cluster H"
    assert created.json()["source_pair_count"] == 1
    assert fake_service.created_by == OWNER_ID

    listed = client.get(
        f"/api/projects/{PROJECT_ID}/candidates",
        headers=auth_headers(),
    )
    assert listed.status_code == 200
    assert listed.json()[0]["auto_canonical_question"] == "How do I reset it?"

    updated = client.patch(
        f"/api/projects/{PROJECT_ID}/candidates/{CANDIDATE_ID}",
        headers=auth_headers(),
        json={
            "candidate_type": "parameterized_faq",
            "manual_title": "Reset FAQ",
            "manual_status": "export_ready",
            "manual_canonical_question": "How can customers reset passwords?",
            "manual_canonical_answer": "Send a reset link.",
            "notes": "Reviewed.",
        },
    )
    assert updated.status_code == 200
    assert updated.json()["candidate_type"] == "parameterized_faq"
    assert updated.json()["auto_title"] == "Cluster H"
    assert updated.json()["manual_title"] == "Reset FAQ"
    assert updated.json()["effective_title"] == "Reset FAQ"
    assert updated.json()["effective_status"] == "export_ready"
    assert fake_service.updated_by == OWNER_ID
    assert fake_service.last_update is not None
    assert fake_service.last_update.fields_to_update == {
        "candidate_type",
        "manual_title",
        "manual_status",
        "manual_canonical_question",
        "manual_canonical_answer",
        "notes",
    }

    sources = client.get(
        f"/api/projects/{PROJECT_ID}/candidates/{CANDIDATE_ID}/sources",
        headers=auth_headers(),
    )
    assert sources.status_code == 200
    payload = sources.json()[0]
    assert payload["ticketid"] == "T-1"
    assert payload["messagegroupid"] == "G-1"
    assert payload["message"] == "How do I reset it?"
    assert payload["answer"] == "Use the reset link."
    assert payload["cluster_id"] == str(CLUSTER_ID)


def test_candidate_patch_preserves_omitted_fields_and_allows_explicit_clear() -> None:
    fake_service = FakeCandidateService()
    fake_service.candidate = fake_service._candidate(
        manual_title="Curated title",
        manual_parameters={"account_id": "required"},
        notes="Existing notes.",
    )
    client = TestClient(
        create_app(
            auth_service=FakeAuthService(),  # type: ignore[arg-type]
            candidate_service=fake_service,  # type: ignore[arg-type]
        )
    )

    partial = client.patch(
        f"/api/projects/{PROJECT_ID}/candidates/{CANDIDATE_ID}",
        headers=auth_headers(),
        json={"manual_status": "in_progress"},
    )

    assert partial.status_code == 200
    assert partial.json()["manual_status"] == "in_progress"
    assert partial.json()["manual_title"] == "Curated title"
    assert partial.json()["manual_parameters"] == {"account_id": "required"}
    assert fake_service.last_update is not None
    assert fake_service.last_update.fields_to_update == {"manual_status"}

    cleared = client.patch(
        f"/api/projects/{PROJECT_ID}/candidates/{CANDIDATE_ID}",
        headers=auth_headers(),
        json={"manual_title": None, "manual_parameters": None},
    )

    assert cleared.status_code == 200
    assert cleared.json()["manual_title"] is None
    assert cleared.json()["effective_title"] == "Cluster H"
    assert cleared.json()["manual_parameters"] is None
    assert cleared.json()["effective_parameters"] == {"account_id": "optional"}
    assert fake_service.last_update.fields_to_update == {
        "manual_title",
        "manual_parameters",
    }
