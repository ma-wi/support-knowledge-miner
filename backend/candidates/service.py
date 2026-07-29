"""Candidate persistence, manual curation, and source traceability."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

from psycopg.types.json import Jsonb

from backend.audit import AuditService
from backend.config import DatabaseSettings
from backend.db.connection import open_database_connection

VALID_CANDIDATE_TYPES = {
    "static_faq",
    "parameterized_faq",
    "dynamic_case",
    "text_block",
    "single_case",
    "not_usable",
}
VALID_STATUSES = {"unreviewed", "in_progress", "reviewed", "rejected", "export_ready"}


class CandidateError(ValueError):
    """Raised when candidate input or state is invalid."""


@dataclass(frozen=True)
class CandidateManualUpdate:
    candidate_type: str | None = None
    manual_status: str | None = None
    manual_category_path: str | None = None
    manual_title: str | None = None
    manual_canonical_question: str | None = None
    manual_canonical_answer: str | None = None
    manual_alternative_questions: list[str] | None = None
    manual_parameters: dict[str, object] | None = None
    manual_external_data_dependencies: list[str] | None = None
    notes: str | None = None
    fields_to_update: frozenset[str] | None = None


@dataclass(frozen=True)
class Candidate:
    id: UUID
    project_id: UUID
    dataset_version_id: UUID
    analysis_run_id: UUID | None
    source_cluster_id: UUID | None
    candidate_type: str
    auto_status: str
    manual_status: str | None
    effective_status: str
    language: str
    auto_category_path: str | None
    manual_category_path: str | None
    effective_category_path: str | None
    auto_title: str
    manual_title: str | None
    effective_title: str
    auto_canonical_question: str
    manual_canonical_question: str | None
    effective_canonical_question: str
    auto_canonical_answer: str
    manual_canonical_answer: str | None
    effective_canonical_answer: str
    auto_alternative_questions: list[str]
    manual_alternative_questions: list[str] | None
    effective_alternative_questions: list[str]
    auto_parameters: dict[str, object]
    manual_parameters: dict[str, object] | None
    effective_parameters: dict[str, object]
    auto_external_data_dependencies: list[str]
    manual_external_data_dependencies: list[str] | None
    effective_external_data_dependencies: list[str]
    quality_score: float
    faq_suitability_score: float
    dynamicity_score: float
    contradiction_score: float
    source_pair_count: int
    source_cluster_ids: list[UUID]
    notes: str | None
    metadata: dict[str, object]
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class CandidateSource:
    candidate_id: UUID
    cluster_id: UUID | None
    message_pair_id: UUID
    ticket_id: str
    message_group_id: str
    message: str
    answer: str
    message_segment_id: str | None
    source_language: str
    normalized_customer_message: str | None
    normalized_support_answer: str | None
    assignment_type: str
    membership_score: float
    is_multi_intent: bool
    intent_label: str | None
    dataset_version_id: UUID
    analysis_run_id: UUID | None


def _clean_optional(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def _object_dict(value: object) -> dict[str, object]:
    return dict(value) if isinstance(value, dict) else {}


def _candidate_from_row(row: dict[str, object]) -> Candidate:
    manual_status = row["manual_status"]
    manual_category = row["manual_category_path"]
    manual_title = row["manual_title"]
    manual_question = row["manual_canonical_question"]
    manual_answer = row["manual_canonical_answer"]
    manual_alternatives = (
        _string_list(row["manual_alternative_questions"])
        if row["manual_alternative_questions"] is not None
        else None
    )
    manual_parameters = (
        _object_dict(row["manual_parameters"])
        if row["manual_parameters"] is not None
        else None
    )
    manual_dependencies = (
        _string_list(row["manual_external_data_dependencies"])
        if row["manual_external_data_dependencies"] is not None
        else None
    )
    auto_category = row["auto_category_path"]
    source_cluster_ids = [
        UUID(str(item)) for item in _string_list(row.get("source_cluster_ids", []))
    ]
    analysis_run = row["analysis_run_id"]
    source_cluster = row["source_cluster_id"]
    return Candidate(
        id=UUID(str(row["id"])),
        project_id=UUID(str(row["project_id"])),
        dataset_version_id=UUID(str(row["dataset_version_id"])),
        analysis_run_id=UUID(str(analysis_run)) if analysis_run is not None else None,
        source_cluster_id=(
            UUID(str(source_cluster)) if source_cluster is not None else None
        ),
        candidate_type=str(row["candidate_type"]),
        auto_status=str(row["auto_status"]),
        manual_status=str(manual_status) if manual_status is not None else None,
        effective_status=(
            str(manual_status) if manual_status is not None else str(row["auto_status"])
        ),
        language=str(row["language"]),
        auto_category_path=str(auto_category) if auto_category is not None else None,
        manual_category_path=(
            str(manual_category) if manual_category is not None else None
        ),
        effective_category_path=(
            str(manual_category)
            if manual_category is not None
            else (str(auto_category) if auto_category is not None else None)
        ),
        auto_title=str(row["auto_title"]),
        manual_title=str(manual_title) if manual_title is not None else None,
        effective_title=(
            str(manual_title) if manual_title is not None else str(row["auto_title"])
        ),
        auto_canonical_question=str(row["auto_canonical_question"]),
        manual_canonical_question=(
            str(manual_question) if manual_question is not None else None
        ),
        effective_canonical_question=(
            str(manual_question)
            if manual_question is not None
            else str(row["auto_canonical_question"])
        ),
        auto_canonical_answer=str(row["auto_canonical_answer"]),
        manual_canonical_answer=str(manual_answer)
        if manual_answer is not None
        else None,
        effective_canonical_answer=(
            str(manual_answer)
            if manual_answer is not None
            else str(row["auto_canonical_answer"])
        ),
        auto_alternative_questions=_string_list(row["auto_alternative_questions"]),
        manual_alternative_questions=manual_alternatives,
        effective_alternative_questions=(
            manual_alternatives
            if manual_alternatives is not None
            else _string_list(row["auto_alternative_questions"])
        ),
        auto_parameters=_object_dict(row["auto_parameters"]),
        manual_parameters=manual_parameters,
        effective_parameters=(
            manual_parameters
            if manual_parameters is not None
            else _object_dict(row["auto_parameters"])
        ),
        auto_external_data_dependencies=_string_list(
            row["auto_external_data_dependencies"]
        ),
        manual_external_data_dependencies=manual_dependencies,
        effective_external_data_dependencies=(
            manual_dependencies
            if manual_dependencies is not None
            else _string_list(row["auto_external_data_dependencies"])
        ),
        quality_score=float(str(row["quality_score"])),
        faq_suitability_score=float(str(row["faq_suitability_score"])),
        dynamicity_score=float(str(row["dynamicity_score"])),
        contradiction_score=float(str(row["contradiction_score"])),
        source_pair_count=int(str(row["source_pair_count"])),
        source_cluster_ids=source_cluster_ids,
        notes=str(row["notes"]) if row["notes"] is not None else None,
        metadata=_object_dict(row["metadata"]),
        created_at=row["created_at"],  # type: ignore[arg-type]
        updated_at=row["updated_at"],  # type: ignore[arg-type]
    )


def _source_from_row(row: dict[str, object]) -> CandidateSource:
    cluster_id = row["cluster_id"]
    analysis_run_id = row["analysis_run_id"]
    return CandidateSource(
        candidate_id=UUID(str(row["candidate_id"])),
        cluster_id=UUID(str(cluster_id)) if cluster_id is not None else None,
        message_pair_id=UUID(str(row["message_pair_id"])),
        ticket_id=str(row["ticket_id"]),
        message_group_id=str(row["message_group_id"]),
        message=str(row["message"]),
        answer=str(row["answer"]),
        message_segment_id=(
            str(row["message_segment_id"])
            if row["message_segment_id"] is not None
            else None
        ),
        source_language=str(row["source_language"]),
        normalized_customer_message=(
            str(row["normalized_customer_message"])
            if row["normalized_customer_message"] is not None
            else None
        ),
        normalized_support_answer=(
            str(row["normalized_support_answer"])
            if row["normalized_support_answer"] is not None
            else None
        ),
        assignment_type=str(row["assignment_type"]),
        membership_score=float(str(row["membership_score"])),
        is_multi_intent=bool(row["is_multi_intent"]),
        intent_label=str(row["intent_label"])
        if row["intent_label"] is not None
        else None,
        dataset_version_id=UUID(str(row["dataset_version_id"])),
        analysis_run_id=UUID(str(analysis_run_id))
        if analysis_run_id is not None
        else None,
    )


class CandidateService:
    def __init__(self, settings: DatabaseSettings | None = None) -> None:
        self._settings = settings
        self._audit = AuditService()

    def create_from_cluster(
        self, project_id: UUID, cluster_id: UUID, *, actor_user_id: UUID
    ) -> Candidate:
        with open_database_connection(self._settings) as connection:
            with connection.transaction():
                existing = connection.execute(
                    """
                    SELECT id
                    FROM candidates
                    WHERE project_id = %s AND source_cluster_id = %s
                    """,
                    (project_id, cluster_id),
                ).fetchone()
                if existing is not None:
                    candidate_id = UUID(str(existing["id"]))
                else:
                    cluster = connection.execute(
                        """
                        SELECT id, project_id, analysis_run_id, dataset_version_id,
                               auto_title, manual_title, auto_category,
                               manual_category, score, is_outlier
                        FROM clusters
                        WHERE id = %s AND project_id = %s
                        """,
                        (cluster_id, project_id),
                    ).fetchone()
                    if cluster is None:
                        raise CandidateError("cluster not found")
                    sources = connection.execute(
                        """
                        SELECT cm.message_pair_id, cm.membership_score,
                               mp.message, mp.answer
                        FROM cluster_memberships cm
                        JOIN message_pairs mp ON mp.id = cm.message_pair_id
                        WHERE cm.project_id = %s AND cm.cluster_id = %s
                        ORDER BY cm.is_outlier ASC, cm.membership_score DESC,
                                 mp.ordinal ASC
                        """,
                        (project_id, cluster_id),
                    ).fetchall()
                    if not sources:
                        raise CandidateError("cluster has no sources")
                    first_source = dict(sources[0])
                    candidate_id = uuid4()
                    manual_title = cluster["manual_title"]
                    manual_category = cluster["manual_category"]
                    title = (
                        _clean_optional(str(manual_title))
                        if manual_title is not None
                        else None
                    ) or str(cluster["auto_title"])
                    category = (
                        _clean_optional(str(manual_category))
                        if manual_category is not None
                        else None
                    ) or (
                        str(cluster["auto_category"])
                        if cluster["auto_category"] is not None
                        else None
                    )
                    candidate_type = (
                        "single_case" if bool(cluster["is_outlier"]) else "static_faq"
                    )
                    connection.execute(
                        """
                        INSERT INTO candidates (
                            id, project_id, dataset_version_id, analysis_run_id,
                            source_cluster_id, candidate_type, auto_status,
                            language, auto_category_path, auto_title,
                            auto_canonical_question, auto_canonical_answer,
                            auto_alternative_questions, quality_score,
                            faq_suitability_score, dynamicity_score,
                            contradiction_score, metadata, created_by_user_id
                        )
                        VALUES (
                            %s, %s, %s, %s, %s, %s, 'unreviewed', 'de',
                            %s, %s, %s, %s, %s, %s, %s, %s, 0, %s, %s
                        )
                        """,
                        (
                            candidate_id,
                            project_id,
                            cluster["dataset_version_id"],
                            cluster["analysis_run_id"],
                            cluster_id,
                            candidate_type,
                            category,
                            title,
                            str(first_source["message"]),
                            str(first_source["answer"]),
                            Jsonb(
                                [
                                    str(source["message"])
                                    for source in sources[1:]
                                    if str(source["message"]).strip()
                                ]
                            ),
                            float(str(cluster["score"])),
                            float(str(cluster["score"])),
                            1.0 if candidate_type == "single_case" else 0.0,
                            Jsonb({"generated_from": "cluster"}),
                            actor_user_id,
                        ),
                    )
                    for source in sources:
                        connection.execute(
                            """
                            INSERT INTO candidate_source_assignments (
                                id, project_id, candidate_id, cluster_id,
                                message_pair_id, dataset_version_id,
                                analysis_run_id, normalized_customer_message,
                                normalized_support_answer, assignment_type,
                                membership_score
                            )
                            VALUES (
                                %s, %s, %s, %s, %s, %s, %s, %s, %s,
                                'automatic', %s
                            )
                            """,
                            (
                                uuid4(),
                                project_id,
                                candidate_id,
                                cluster_id,
                                source["message_pair_id"],
                                cluster["dataset_version_id"],
                                cluster["analysis_run_id"],
                                str(source["message"]).strip().lower(),
                                str(source["answer"]).strip().lower(),
                                source["membership_score"],
                            ),
                        )
                    self._audit.record_event(
                        connection,
                        actor_user_id=actor_user_id,
                        action="candidate.create_from_cluster",
                        target_type="candidate",
                        target_id=candidate_id,
                        metadata={
                            "project_id": str(project_id),
                            "cluster_id": str(cluster_id),
                            "source_pair_count": len(sources),
                        },
                    )
        candidate = self.get_candidate(project_id, candidate_id)
        if candidate is None:
            raise RuntimeError("candidate disappeared after creation")
        return candidate

    def list_candidates(self, project_id: UUID) -> list[Candidate]:
        with open_database_connection(self._settings) as connection:
            rows = connection.execute(
                self._candidate_list_sql(),
                (project_id,),
            ).fetchall()
        return [_candidate_from_row(dict(row)) for row in rows]

    def get_candidate(self, project_id: UUID, candidate_id: UUID) -> Candidate | None:
        with open_database_connection(self._settings) as connection:
            row = connection.execute(
                self._candidate_get_sql(),
                (project_id, candidate_id),
            ).fetchone()
        return _candidate_from_row(dict(row)) if row is not None else None

    def update_candidate(
        self,
        project_id: UUID,
        candidate_id: UUID,
        payload: CandidateManualUpdate,
        *,
        actor_user_id: UUID,
    ) -> Candidate:
        fields_to_update = payload.fields_to_update or frozenset(
            field
            for field in (
                "candidate_type",
                "manual_status",
                "manual_category_path",
                "manual_title",
                "manual_canonical_question",
                "manual_canonical_answer",
                "manual_alternative_questions",
                "manual_parameters",
                "manual_external_data_dependencies",
                "notes",
            )
            if getattr(payload, field) is not None
        )
        candidate_type = _clean_optional(payload.candidate_type)
        manual_status = _clean_optional(payload.manual_status)
        if (
            "candidate_type" in fields_to_update
            and candidate_type is not None
            and candidate_type not in VALID_CANDIDATE_TYPES
        ):
            raise CandidateError("candidate_type is invalid")
        if (
            "manual_status" in fields_to_update
            and manual_status is not None
            and manual_status not in VALID_STATUSES
        ):
            raise CandidateError("manual_status is invalid")
        with open_database_connection(self._settings) as connection:
            with connection.transaction():
                row = connection.execute(
                    """
                    UPDATE candidates
                    SET candidate_type = CASE
                            WHEN %s THEN COALESCE(%s, candidate_type)
                            ELSE candidate_type
                        END,
                        manual_status = CASE
                            WHEN %s THEN %s ELSE manual_status
                        END,
                        manual_category_path = CASE
                            WHEN %s THEN %s ELSE manual_category_path
                        END,
                        manual_title = CASE
                            WHEN %s THEN %s ELSE manual_title
                        END,
                        manual_canonical_question = CASE
                            WHEN %s THEN %s ELSE manual_canonical_question
                        END,
                        manual_canonical_answer = CASE
                            WHEN %s THEN %s ELSE manual_canonical_answer
                        END,
                        manual_alternative_questions = CASE
                            WHEN %s THEN %s ELSE manual_alternative_questions
                        END,
                        manual_parameters = CASE
                            WHEN %s THEN %s ELSE manual_parameters
                        END,
                        manual_external_data_dependencies = CASE
                            WHEN %s THEN %s
                            ELSE manual_external_data_dependencies
                        END,
                        notes = CASE
                            WHEN %s THEN %s ELSE notes
                        END,
                        updated_at = now()
                    WHERE id = %s AND project_id = %s
                    RETURNING id
                    """,
                    (
                        "candidate_type" in fields_to_update,
                        candidate_type,
                        "manual_status" in fields_to_update,
                        manual_status,
                        "manual_category_path" in fields_to_update,
                        _clean_optional(payload.manual_category_path),
                        "manual_title" in fields_to_update,
                        _clean_optional(payload.manual_title),
                        "manual_canonical_question" in fields_to_update,
                        _clean_optional(payload.manual_canonical_question),
                        "manual_canonical_answer" in fields_to_update,
                        _clean_optional(payload.manual_canonical_answer),
                        "manual_alternative_questions" in fields_to_update,
                        (
                            Jsonb(payload.manual_alternative_questions)
                            if payload.manual_alternative_questions is not None
                            else None
                        ),
                        "manual_parameters" in fields_to_update,
                        (
                            Jsonb(payload.manual_parameters)
                            if payload.manual_parameters is not None
                            else None
                        ),
                        "manual_external_data_dependencies" in fields_to_update,
                        (
                            Jsonb(payload.manual_external_data_dependencies)
                            if payload.manual_external_data_dependencies is not None
                            else None
                        ),
                        "notes" in fields_to_update,
                        _clean_optional(payload.notes),
                        candidate_id,
                        project_id,
                    ),
                ).fetchone()
                if row is None:
                    raise CandidateError("candidate not found")
                self._audit.record_event(
                    connection,
                    actor_user_id=actor_user_id,
                    action="candidate.update_manual",
                    target_type="candidate",
                    target_id=candidate_id,
                    metadata={"project_id": str(project_id)},
                )
        candidate = self.get_candidate(project_id, candidate_id)
        if candidate is None:
            raise RuntimeError("candidate disappeared after update")
        return candidate

    def list_sources(
        self, project_id: UUID, candidate_id: UUID
    ) -> list[CandidateSource]:
        with open_database_connection(self._settings) as connection:
            rows = connection.execute(
                """
                SELECT csa.candidate_id, csa.cluster_id, csa.message_pair_id,
                       mp.ticket_id, mp.message_group_id, mp.message, mp.answer,
                       csa.message_segment_id, csa.source_language,
                       csa.normalized_customer_message,
                       csa.normalized_support_answer, csa.assignment_type,
                       csa.membership_score, csa.is_multi_intent,
                       csa.intent_label, csa.dataset_version_id,
                       csa.analysis_run_id
                FROM candidate_source_assignments csa
                JOIN candidates c ON c.id = csa.candidate_id
                JOIN message_pairs mp ON mp.id = csa.message_pair_id
                WHERE csa.project_id = %s AND csa.candidate_id = %s
                  AND c.project_id = %s
                ORDER BY csa.membership_score DESC, mp.ordinal ASC
                """,
                (project_id, candidate_id, project_id),
            ).fetchall()
        return [_source_from_row(dict(row)) for row in rows]

    @staticmethod
    def _candidate_list_sql() -> str:
        return """
            SELECT c.id, c.project_id, c.dataset_version_id, c.analysis_run_id,
                   c.source_cluster_id, c.candidate_type, c.auto_status,
                   c.manual_status, c.language, c.auto_category_path,
                   c.manual_category_path, c.auto_title, c.manual_title,
                   c.auto_canonical_question, c.manual_canonical_question,
                   c.auto_canonical_answer, c.manual_canonical_answer,
                   c.auto_alternative_questions, c.manual_alternative_questions,
                   c.auto_parameters, c.manual_parameters,
                   c.auto_external_data_dependencies,
                   c.manual_external_data_dependencies, c.quality_score,
                   c.faq_suitability_score, c.dynamicity_score,
                   c.contradiction_score, c.notes, c.metadata, c.created_at,
                   c.updated_at, COUNT(csa.id) AS source_pair_count,
                   COALESCE(
                       array_agg(DISTINCT csa.cluster_id)
                       FILTER (WHERE csa.cluster_id IS NOT NULL),
                       ARRAY[]::uuid[]
                   ) AS source_cluster_ids
            FROM candidates c
            LEFT JOIN candidate_source_assignments csa
              ON csa.candidate_id = c.id
            WHERE c.project_id = %s
            GROUP BY c.id
            ORDER BY c.updated_at DESC, c.created_at DESC
        """

    @staticmethod
    def _candidate_get_sql() -> str:
        return """
            SELECT c.id, c.project_id, c.dataset_version_id, c.analysis_run_id,
                   c.source_cluster_id, c.candidate_type, c.auto_status,
                   c.manual_status, c.language, c.auto_category_path,
                   c.manual_category_path, c.auto_title, c.manual_title,
                   c.auto_canonical_question, c.manual_canonical_question,
                   c.auto_canonical_answer, c.manual_canonical_answer,
                   c.auto_alternative_questions, c.manual_alternative_questions,
                   c.auto_parameters, c.manual_parameters,
                   c.auto_external_data_dependencies,
                   c.manual_external_data_dependencies, c.quality_score,
                   c.faq_suitability_score, c.dynamicity_score,
                   c.contradiction_score, c.notes, c.metadata, c.created_at,
                   c.updated_at, COUNT(csa.id) AS source_pair_count,
                   COALESCE(
                       array_agg(DISTINCT csa.cluster_id)
                       FILTER (WHERE csa.cluster_id IS NOT NULL),
                       ARRAY[]::uuid[]
                   ) AS source_cluster_ids
            FROM candidates c
            LEFT JOIN candidate_source_assignments csa
              ON csa.candidate_id = c.id
            WHERE c.project_id = %s AND c.id = %s
            GROUP BY c.id
        """
