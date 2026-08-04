from __future__ import annotations

from datetime import UTC, datetime
from typing import cast
from uuid import UUID

import numpy as np
from pgvector import Vector
import pytest

import backend.clusters.service as cluster_service_module
from backend.clusters import ClusterError, ClusterService
from backend.clusters.service import (
    AGGLOMERATIVE_BYTES_PER_VECTOR_VALUE,
    HDBSCAN_BYTES_PER_VECTOR_VALUE,
    HDBSCAN_FIXED_BYTES_PER_RECORD,
    HDBSCAN_NEIGHBOR_BYTES_PER_CELL,
    MAX_CLUSTER_WORKING_SET_BYTES,
    NATIVE_FETCH_BYTES_PER_VALUE,
    NATIVE_VECTOR_FETCH_BATCH_SIZE,
    ClusterSetInput,
    _apply_outlier_threshold,
    _summary_sample_strategy,
    _validate_summary_call_budget,
    validate_algorithm_settings,
    validate_cluster_input_budget,
)

ACTOR_ID = UUID("11111111-1111-1111-1111-111111111111")
PROJECT_ID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
RUN_ID = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
DATASET_ID = UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
PAIR_A = UUID("dddddddd-dddd-dddd-dddd-ddddddddddda")
PAIR_B = UUID("dddddddd-dddd-dddd-dddd-dddddddddddb")
PAIR_C = UUID("dddddddd-dddd-dddd-dddd-dddddddddddc")
CLUSTER_A = UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeea")
CLUSTER_B = UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeeb")
CLUSTER_C = UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeec")
PARENT_CLUSTER_SET_ID = UUID("99999999-9999-9999-9999-999999999999")
NOW = datetime(2026, 7, 22, tzinfo=UTC)


class FakeResult:
    def __init__(self, rows: list[dict[str, object]] | None = None) -> None:
        self._rows = rows or []
        self._offset = 0

    def fetchone(self) -> dict[str, object] | None:
        return self._rows[0] if self._rows else None

    def fetchall(self) -> list[dict[str, object]]:
        return self._rows

    def fetchmany(self, size: int) -> list[dict[str, object]]:
        rows = self._rows[self._offset : self._offset + size]
        self._offset += len(rows)
        return rows


class FakeTransaction:
    def __enter__(self) -> FakeTransaction:
        return self

    def __exit__(self, *_: object) -> None:
        return None


class FakeNativeVectorCursor:
    def __init__(
        self,
        connection: ClusterConnection,
        *,
        name: str,
        binary: bool,
    ) -> None:
        self._connection = connection
        self._name = name
        self._binary = binary
        self._result: FakeResult | None = None

    def __enter__(self) -> FakeNativeVectorCursor:
        self._connection.native_cursor_events.append(("open", self._name, self._binary))
        return self

    def __exit__(self, *_: object) -> None:
        self._connection.native_cursor_events.append(
            ("close", self._name, self._binary)
        )

    def execute(
        self, query: str, params: tuple[object, ...] | None = None
    ) -> FakeNativeVectorCursor:
        normalized = " ".join(query.split())
        assert normalized.startswith("SELECT mp.id AS message_pair_id")
        assert params is not None
        assert params[:3] == (RUN_ID, PROJECT_ID, DATASET_ID)
        self._connection.message_pair_selects += 1
        self._result = FakeResult(self._connection.embedding_rows)
        return self

    def fetchmany(self, size: int) -> list[dict[str, object]]:
        assert size == NATIVE_VECTOR_FETCH_BATCH_SIZE
        assert self._result is not None
        return self._result.fetchmany(size)


class FakeClusterSetVectorCursor:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self._rows = rows
        self._result: FakeResult | None = None

    def __enter__(self) -> FakeClusterSetVectorCursor:
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def execute(
        self, query: str, params: tuple[object, ...] | None = None
    ) -> FakeClusterSetVectorCursor:
        normalized = " ".join(query.split())
        assert normalized.startswith("SELECT mp.id AS message_pair_id")
        assert "em.text_variant = 'message'" in normalized
        assert "ea.text_variant = 'answer'" in normalized
        assert params == (RUN_ID, RUN_ID, PROJECT_ID, DATASET_ID, 11)
        self._result = FakeResult(self._rows)
        return self

    def fetchmany(self, size: int) -> list[dict[str, object]]:
        assert size == NATIVE_VECTOR_FETCH_BATCH_SIZE
        assert self._result is not None
        return self._result.fetchmany(size)


class ClusterSetVectorConnection:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self._rows = rows

    def cursor(self, *, name: str, binary: bool) -> FakeClusterSetVectorCursor:
        assert name == f"cluster_set_vectors_{RUN_ID.hex}"
        assert binary is True
        return FakeClusterSetVectorCursor(self._rows)


class SourcePairResolutionConnection:
    def __init__(
        self,
        parent_pair_ids: set[UUID],
        *,
        cluster_pair_ids: dict[UUID, set[UUID]] | None = None,
    ) -> None:
        self._parent_pair_ids = parent_pair_ids
        self._cluster_pair_ids = cluster_pair_ids or {}

    def execute(
        self, query: str, params: tuple[object, ...] | None = None
    ) -> FakeResult:
        assert params is not None
        normalized = " ".join(query.split())
        if normalized.startswith(
            "SELECT DISTINCT c.id AS cluster_id, cm.message_pair_id"
        ):
            requested = set(cast(list[UUID], params[3]))
            return FakeResult(
                [
                    {"cluster_id": cluster_id, "message_pair_id": pair_id}
                    for cluster_id in sorted(
                        requested & self._cluster_pair_ids.keys(),
                        key=str,
                    )
                    for pair_id in sorted(self._cluster_pair_ids[cluster_id], key=str)
                ]
            )
        if normalized.startswith("SELECT DISTINCT cm.message_pair_id"):
            requested = set(cast(list[UUID], params[3]))
            return FakeResult(
                [
                    {"message_pair_id": pair_id}
                    for pair_id in sorted(requested & self._parent_pair_ids, key=str)
                ]
            )
        if normalized.startswith("SELECT id FROM message_pairs"):
            return FakeResult(
                [{"id": pair_id} for pair_id in cast(list[UUID], params[2])]
            )
        raise AssertionError(f"unexpected query: {normalized}")


class ParentStatusConnection:
    def __init__(
        self,
        *,
        parent_status: str,
        parent_indexing_run_id: UUID = RUN_ID,
    ) -> None:
        self._parent_status = parent_status
        self._parent_indexing_run_id = parent_indexing_run_id

    def __enter__(self) -> ParentStatusConnection:
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def transaction(self) -> FakeTransaction:
        return FakeTransaction()

    def execute(
        self, query: str, params: tuple[object, ...] | None = None
    ) -> FakeResult:
        normalized = " ".join(query.split())
        if normalized.startswith("SELECT r.id, r.project_id"):
            return FakeResult(
                [
                    {
                        "id": RUN_ID,
                        "project_id": PROJECT_ID,
                        "dataset_version_id": DATASET_ID,
                        "status": "completed",
                        "indexing_deleted_at": None,
                        "dataset_display_name": "Fixture dataset",
                        "dataset_deleted_at": None,
                    }
                ]
            )
        if normalized.startswith("SELECT id, indexing_run_id, status"):
            return FakeResult(
                [
                    {
                        "id": UUID("99999999-9999-9999-9999-999999999999"),
                        "indexing_run_id": self._parent_indexing_run_id,
                        "status": self._parent_status,
                    }
                ]
            )
        raise AssertionError(f"unexpected query: {normalized}")


class ClusterConnection:
    def __init__(
        self,
        *,
        algorithm_settings: dict[str, object] | None = None,
        embedding_rows: list[dict[str, object]] | None = None,
    ) -> None:
        self.clusters: list[dict[str, object]] = []
        self.memberships: list[dict[str, object]] = []
        self.message_pair_selects = 0
        self.native_cursor_events: list[tuple[str, str, bool]] = []
        self.algorithm_settings = algorithm_settings or {
            "algorithm": "hdbscan",
            "min_cluster_size": 2,
            "min_samples": 1,
        }
        self.embedding_rows = embedding_rows or [
            {
                "message_pair_id": PAIR_A,
                "embedding": Vector([0.0, 0.0]),
                "dimensions": 2,
            },
            {
                "message_pair_id": PAIR_B,
                "embedding": Vector([0.0, 0.1]),
                "dimensions": 2,
            },
            {
                "message_pair_id": PAIR_C,
                "embedding": Vector([10.0, 10.0]),
                "dimensions": 2,
            },
            {
                "message_pair_id": UUID("dddddddd-dddd-dddd-dddd-dddddddddddd"),
                "embedding": Vector([10.0, 10.1]),
                "dimensions": 2,
            },
        ]

    def __enter__(self) -> ClusterConnection:
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def transaction(self) -> FakeTransaction:
        return FakeTransaction()

    def cursor(self, *, name: str, binary: bool) -> FakeNativeVectorCursor:
        return FakeNativeVectorCursor(self, name=name, binary=binary)

    def execute(
        self, query: str, params: tuple[object, ...] | None = None
    ) -> FakeResult:
        normalized = " ".join(query.split())
        if normalized.startswith("SELECT id, project_id, dataset_version_id, status"):
            return FakeResult(
                [
                    {
                        "id": RUN_ID,
                        "project_id": PROJECT_ID,
                        "dataset_version_id": DATASET_ID,
                        "status": "completed",
                        "parameters": {"algorithm_settings": self.algorithm_settings},
                        "provider": "vllm",
                        "model": "local-embed",
                    }
                ]
            )
        if normalized.startswith("SELECT id FROM clusters"):
            return (
                FakeResult([{"id": self.clusters[0]["id"]}])
                if self.clusters
                else FakeResult()
            )
        if normalized.startswith("SELECT COUNT(mp.id) AS record_count"):
            present = [
                row for row in self.embedding_rows if row["embedding"] is not None
            ]
            dimensions = [
                int(str(row["dimensions"]))
                for row in present
                if row["dimensions"] is not None
            ]
            return FakeResult(
                [
                    {
                        "record_count": len(self.embedding_rows),
                        "embedding_count": len(present),
                        "minimum_dimensions": min(dimensions) if dimensions else None,
                        "maximum_dimensions": max(dimensions) if dimensions else None,
                    }
                ]
            )
        if normalized.startswith("INSERT INTO clusters"):
            assert params is not None
            self.clusters.append(
                {
                    "id": params[0],
                    "project_id": params[1],
                    "analysis_run_id": params[2],
                    "dataset_version_id": params[3],
                    "auto_title": params[4],
                    "manual_title": None,
                    "auto_category": params[5],
                    "manual_category": None,
                    "auto_status": params[6],
                    "manual_status": None,
                    "score": params[7],
                    "is_outlier": params[8],
                    "algorithm": params[9],
                    "metadata": unwrap_json(params[10]),
                    "created_at": NOW,
                    "updated_at": NOW,
                }
            )
            return FakeResult()
        if normalized.startswith("INSERT INTO cluster_memberships"):
            assert params is not None
            self.memberships.append(
                {
                    "cluster_id": params[2],
                    "message_pair_id": params[4],
                    "membership_score": params[5],
                    "is_outlier": params[6],
                }
            )
            return FakeResult()
        if normalized.startswith("INSERT INTO audit_events"):
            return FakeResult()
        if normalized.startswith("SELECT c.id, c.project_id"):
            rows = []
            for cluster in self.clusters:
                member_count = sum(
                    1
                    for item in self.memberships
                    if item["cluster_id"] == cluster["id"]
                )
                rows.append({**cluster, "member_count": member_count})
            return FakeResult(rows)
        raise AssertionError(f"unexpected query: {normalized}")


def source_row(pair_id: UUID, *, ordinal: int) -> dict[str, object]:
    return {
        "cluster_id": CLUSTER_A,
        "message_pair_id": pair_id,
        "ticket_id": f"T-{ordinal}",
        "message_group_id": f"G-{ordinal}",
        "message": f"Question {ordinal}",
        "answer": f"Answer {ordinal}",
        "membership_score": 0.9 - ordinal / 100,
        "is_outlier": False,
        "assignment_type": "automatic",
    }


class SourcePagingConnection:
    def __enter__(self) -> SourcePagingConnection:
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def execute(
        self, query: str, params: tuple[object, ...] | None = None
    ) -> FakeResult:
        normalized = " ".join(query.split())
        if normalized.startswith("SELECT c.id, c.cluster_set_id"):
            assert params == (CLUSTER_A, PROJECT_ID)
            return FakeResult(
                [
                    {
                        "id": CLUSTER_A,
                        "cluster_set_id": PARENT_CLUSTER_SET_ID,
                        "cluster_set_status": "completed",
                    }
                ]
            )
        if normalized.startswith("SELECT cm.cluster_id"):
            assert "LIMIT %s OFFSET %s" in normalized
            assert params == (PROJECT_ID, PROJECT_ID, CLUSTER_A, 3, 2)
            return FakeResult(
                [
                    source_row(PAIR_A, ordinal=1),
                    source_row(PAIR_B, ordinal=2),
                    source_row(PAIR_C, ordinal=3),
                ]
            )
        raise AssertionError(f"unexpected query: {normalized}")


def unwrap_json(value: object) -> object:
    return getattr(value, "obj", value)


def test_generate_for_run_clusters_persisted_vectors_with_transitional_hdbscan_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_connection = ClusterConnection(
        algorithm_settings={"algorithm": "agglomerative", "linkage": "ward"}
    )
    monkeypatch.setattr(
        cluster_service_module,
        "open_database_connection",
        lambda _: fake_connection,
    )

    clusters = ClusterService().generate_for_run(
        PROJECT_ID, RUN_ID, actor_user_id=ACTOR_ID
    )

    assert fake_connection.message_pair_selects == 1
    assert fake_connection.native_cursor_events == [
        ("open", f"cluster_vectors_{RUN_ID.hex}", True),
        ("close", f"cluster_vectors_{RUN_ID.hex}", True),
    ]
    assert len(clusters) == 2
    assert {cluster.member_count for cluster in clusters} == {2}
    assert all(cluster.algorithm == "hdbscan" for cluster in clusters)
    assert all(cluster.metadata["non_quadratic"] is True for cluster in clusters)
    assert all("linkage" not in cluster.metadata["parameters"] for cluster in clusters)
    assert len(fake_connection.memberships) == 4


def test_missing_embedding_fails_before_cluster_writes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_connection = ClusterConnection(
        embedding_rows=[
            {
                "message_pair_id": PAIR_A,
                "embedding": Vector([0.0, 0.0]),
                "dimensions": 2,
            },
            {"message_pair_id": PAIR_B, "embedding": None, "dimensions": None},
        ]
    )
    monkeypatch.setattr(
        cluster_service_module,
        "open_database_connection",
        lambda _: fake_connection,
    )

    with pytest.raises(ClusterError, match="missing message embeddings"):
        ClusterService().generate_for_run(PROJECT_ID, RUN_ID, actor_user_id=ACTOR_ID)

    assert fake_connection.clusters == []
    assert fake_connection.memberships == []


def test_list_sources_returns_bounded_page(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        cluster_service_module,
        "open_database_connection",
        lambda _: SourcePagingConnection(),
    )

    page = ClusterService().list_sources(PROJECT_ID, CLUSTER_A, limit=2, offset=2)

    assert [source.message_pair_id for source in page.sources] == [PAIR_A, PAIR_B]
    assert page.limit == 2
    assert page.offset == 2
    assert page.next_offset == 4
    assert page.has_more is True


def test_list_sources_rejects_unbounded_page_before_database_access() -> None:
    service = ClusterService()

    with pytest.raises(ClusterError) as error:
        service.list_sources(PROJECT_ID, CLUSTER_A, limit=51)

    assert error.value.code == "CLUSTER_SOURCE_PAGE_INVALID"
    assert error.value.status_code == 422


def test_cluster_set_combined_basis_uses_weighted_question_answer_vectors() -> None:
    service = ClusterService()
    connection = ClusterSetVectorConnection(
        [
            {
                "message_pair_id": PAIR_A,
                "message_embedding": Vector([1.0, 0.0]),
                "message_dimensions": 2,
                "answer_embedding": Vector([0.0, 1.0]),
                "answer_dimensions": 2,
            },
            {
                "message_pair_id": PAIR_B,
                "message_embedding": Vector([2.0, 0.0]),
                "message_dimensions": 2,
                "answer_embedding": Vector([0.0, 2.0]),
                "answer_dimensions": 2,
            },
        ]
    )

    pair_ids, vectors, mismatch_scores = service._load_cluster_set_embedding_matrix(
        connection,
        project_id=PROJECT_ID,
        indexing_run_id=RUN_ID,
        dataset_version_id=DATASET_ID,
        vector_basis="combined",
        message_weight=0.25,
        answer_weight=0.75,
        source_pair_ids=None,
        record_limit=10,
        expected_record_count=2,
        expected_dimensions=4,
        message_expected_dimensions=2,
        answer_expected_dimensions=2,
    )

    expected = np.array([0.25, 0.0, 0.0, 0.75], dtype=np.float32)
    assert pair_ids == [PAIR_A, PAIR_B]
    np.testing.assert_allclose(vectors[0], expected, rtol=1e-6)
    np.testing.assert_allclose(vectors[1], expected, rtol=1e-6)
    assert mismatch_scores[PAIR_A] == 1.0
    assert mismatch_scores[PAIR_B] == 1.0


def test_refinement_source_pair_ids_must_belong_to_parent_set() -> None:
    service = ClusterService()

    with pytest.raises(ClusterError, match="outside the parent Cluster-Set"):
        service._resolve_source_pair_ids(
            SourcePairResolutionConnection({PAIR_A}),
            project_id=PROJECT_ID,
            dataset_version_id=DATASET_ID,
            parent_cluster_set_id=UUID("99999999-9999-9999-9999-999999999999"),
            source_cluster_ids=[],
            source_pair_ids=[PAIR_A, PAIR_B],
        )


def test_refinement_source_pair_ids_from_parent_are_accepted() -> None:
    service = ClusterService()

    selected = service._resolve_source_pair_ids(
        SourcePairResolutionConnection({PAIR_A, PAIR_B}),
        project_id=PROJECT_ID,
        dataset_version_id=DATASET_ID,
        parent_cluster_set_id=PARENT_CLUSTER_SET_ID,
        source_cluster_ids=[],
        source_pair_ids=[PAIR_A, PAIR_B],
    )

    assert selected == sorted([PAIR_A, PAIR_B], key=str)


def test_refinement_source_cluster_ids_must_all_belong_to_parent_set() -> None:
    service = ClusterService()

    with pytest.raises(ClusterError) as error:
        service._resolve_source_pair_ids(
            SourcePairResolutionConnection(
                {PAIR_A},
                cluster_pair_ids={CLUSTER_A: {PAIR_A}},
            ),
            project_id=PROJECT_ID,
            dataset_version_id=DATASET_ID,
            parent_cluster_set_id=PARENT_CLUSTER_SET_ID,
            source_cluster_ids=[CLUSTER_A, CLUSTER_C],
            source_pair_ids=[],
        )

    assert error.value.code == "CLUSTER_REFINEMENT_EMPTY_SOURCE"
    assert error.value.field_errors == {
        "source_cluster_ids": "source clusters must belong to the parent Cluster-Set"
    }


def test_refinement_source_cluster_ids_from_parent_are_accepted() -> None:
    service = ClusterService()

    selected = service._resolve_source_pair_ids(
        SourcePairResolutionConnection(
            {PAIR_A, PAIR_B},
            cluster_pair_ids={CLUSTER_A: {PAIR_A}, CLUSTER_B: {PAIR_B}},
        ),
        project_id=PROJECT_ID,
        dataset_version_id=DATASET_ID,
        parent_cluster_set_id=PARENT_CLUSTER_SET_ID,
        source_cluster_ids=[CLUSTER_A, CLUSTER_B],
        source_pair_ids=[],
    )

    assert selected == sorted([PAIR_A, PAIR_B], key=str)


def test_cluster_set_refinement_requires_completed_parent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        cluster_service_module,
        "open_database_connection",
        lambda _: ParentStatusConnection(parent_status="running"),
    )
    service = ClusterService()

    with pytest.raises(ClusterError) as error:
        service.start_cluster_set(
            PROJECT_ID,
            ClusterSetInput(
                indexing_run_id=RUN_ID,
                parent_cluster_set_id=PARENT_CLUSTER_SET_ID,
                derivation_type="refinement",
            ),
            actor_user_id=ACTOR_ID,
        )

    assert error.value.code == "CLUSTER_SET_NOT_COMPLETE"


def test_cluster_set_parent_requires_non_root_derivation_type(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        cluster_service_module,
        "open_database_connection",
        lambda _: ParentStatusConnection(parent_status="completed"),
    )
    service = ClusterService()

    with pytest.raises(ClusterError) as error:
        service.start_cluster_set(
            PROJECT_ID,
            ClusterSetInput(
                indexing_run_id=RUN_ID,
                parent_cluster_set_id=PARENT_CLUSTER_SET_ID,
            ),
            actor_user_id=ACTOR_ID,
        )

    assert error.value.code == "CLUSTER_REFINEMENT_EMPTY_SOURCE"
    assert error.value.field_errors == {
        "derivation_type": "parent Cluster-Set requires a refinement derivation type"
    }


def test_cluster_set_refinement_requires_source_selection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        cluster_service_module,
        "open_database_connection",
        lambda _: ParentStatusConnection(parent_status="completed"),
    )
    service = ClusterService()

    with pytest.raises(ClusterError) as error:
        service.start_cluster_set(
            PROJECT_ID,
            ClusterSetInput(
                indexing_run_id=RUN_ID,
                parent_cluster_set_id=PARENT_CLUSTER_SET_ID,
                derivation_type="refinement",
            ),
            actor_user_id=ACTOR_ID,
        )

    assert error.value.code == "CLUSTER_REFINEMENT_EMPTY_SOURCE"
    assert error.value.field_errors == {
        "source_cluster_ids": "refinement requires at least one source selection",
        "source_pair_ids": "refinement requires at least one source selection",
    }


def test_cluster_set_parent_must_use_selected_indexing_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    other_run_id = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbc")
    monkeypatch.setattr(
        cluster_service_module,
        "open_database_connection",
        lambda _: ParentStatusConnection(
            parent_status="completed",
            parent_indexing_run_id=other_run_id,
        ),
    )
    service = ClusterService()

    with pytest.raises(ClusterError) as error:
        service.start_cluster_set(
            PROJECT_ID,
            ClusterSetInput(
                indexing_run_id=RUN_ID,
                parent_cluster_set_id=PARENT_CLUSTER_SET_ID,
                derivation_type="refinement",
                source_pair_ids=[PAIR_A],
            ),
            actor_user_id=ACTOR_ID,
        )

    assert error.value.code == "CLUSTER_REFINEMENT_EMPTY_SOURCE"
    assert error.value.field_errors == {
        "parent_cluster_set_id": "parent Cluster-Set must use the selected indexing run"
    }


def test_cluster_set_summary_sample_count_is_bounded() -> None:
    with pytest.raises(ClusterError, match="summary sample count is invalid"):
        _summary_sample_strategy(
            ClusterSetInput(
                indexing_run_id=RUN_ID,
                llm_provider="ollama",
                llm_model="llama3.1",
                llm_sample_count=0,
            )
        )


def test_cluster_set_summary_sample_count_defaults_to_ten() -> None:
    strategy = _summary_sample_strategy(
        ClusterSetInput(
            indexing_run_id=RUN_ID,
            llm_provider="ollama",
            llm_model="llama3.1",
            llm_sample_count=None,
        )
    )

    assert strategy["requested"] == 10


def test_summary_call_budget_rejects_too_many_llm_calls() -> None:
    with pytest.raises(ClusterError, match="Cluster summary call budget exceeded"):
        _validate_summary_call_budget(501)


def test_algorithm_settings_preserve_outlier_threshold() -> None:
    config = validate_algorithm_settings(
        {
            "algorithm": "hdbscan",
            "min_cluster_size": 2,
            "outlier_threshold": 0.42,
        }
    )

    assert config.parameters["outlier_threshold"] == 0.42


def test_outlier_threshold_reclassifies_low_confidence_members() -> None:
    labels = _apply_outlier_threshold([0, 0, 1], [0.9, 0.2, 0.7], 0.5)

    assert labels == [0, -1, 1]


def test_outlier_threshold_rejects_empty_result() -> None:
    with pytest.raises(ClusterError, match="outlier threshold removes all records"):
        _apply_outlier_threshold([0, 1], [0.2, 0.3], 0.5)


def test_cluster_summary_response_requires_schema_json() -> None:
    service = ClusterService()

    parsed = service._parse_cluster_summary_response(
        '{"title":"Reset","category":"Account","question":"How?","answer":"Use link","rationale":null}'
    )
    assert parsed["title"] == "Reset"
    assert parsed["question"] == "How?"

    with pytest.raises(ClusterError, match="Cluster summary response is invalid"):
        service._parse_cluster_summary_response("not json")


@pytest.mark.parametrize(
    "settings",
    [
        {"algorithm": "other"},
        {"algorithm": "hdbscan", "min_cluster_size": 1},
        {"algorithm": "hdbscan", "min_cluster_size": 100_001},
        {"algorithm": "hdbscan", "min_samples": 100_001},
        {"algorithm": "hdbscan", "outlier_threshold": 1.1},
        {"algorithm": "hdbscan", "n_clusters": 2},
        {
            "algorithm": "agglomerative",
            "n_clusters": 2,
            "distance_threshold": 0.5,
        },
        {"algorithm": "agglomerative", "linkage": "invalid"},
    ],
)
def test_algorithm_settings_reject_invalid_contract(
    settings: dict[str, object],
) -> None:
    with pytest.raises(ClusterError):
        validate_algorithm_settings(settings)


def _embedding_rows(count: int) -> list[dict[str, object]]:
    return [
        {
            "message_pair_id": UUID(int=index + 1),
            "embedding": Vector([float(index), 0.0]),
            "dimensions": 2,
        }
        for index in range(count)
    ]


def test_agglomerative_rejects_10001_records_before_estimator() -> None:
    config = validate_algorithm_settings({"algorithm": "agglomerative"})

    with pytest.raises(ClusterError, match="at most 10000"):
        validate_cluster_input_budget(
            config,
            record_count=10_001,
            embedding_count=10_001,
            minimum_dimensions=2,
            maximum_dimensions=2,
        )


def test_hdbscan_neighbor_budget_accepts_boundary_and_rejects_next_value() -> None:
    record_count = 10_000
    dimensions = 2
    fixed_bytes = (
        record_count * dimensions * HDBSCAN_BYTES_PER_VECTOR_VALUE
        + min(record_count, NATIVE_VECTOR_FETCH_BATCH_SIZE)
        * dimensions
        * NATIVE_FETCH_BYTES_PER_VALUE
        + record_count * HDBSCAN_FIXED_BYTES_PER_RECORD
    )
    accepted_neighbors = (MAX_CLUSTER_WORKING_SET_BYTES - fixed_bytes) // (
        record_count * HDBSCAN_NEIGHBOR_BYTES_PER_CELL
    )
    accepted = validate_algorithm_settings(
        {"algorithm": "hdbscan", "min_samples": accepted_neighbors}
    )

    accepted_dimensions = validate_cluster_input_budget(
        accepted,
        record_count=record_count,
        embedding_count=record_count,
        minimum_dimensions=dimensions,
        maximum_dimensions=dimensions,
    )

    assert accepted_dimensions == dimensions
    rejected = validate_algorithm_settings(
        {"algorithm": "hdbscan", "min_samples": accepted_neighbors + 1}
    )
    with pytest.raises(ClusterError, match="working set estimate .* exceeds"):
        validate_cluster_input_budget(
            rejected,
            record_count=record_count,
            embedding_count=record_count,
            minimum_dimensions=dimensions,
            maximum_dimensions=dimensions,
        )


def test_hdbscan_budget_uses_min_cluster_size_when_min_samples_is_absent() -> None:
    config = validate_algorithm_settings(
        {
            "algorithm": "hdbscan",
            "min_cluster_size": 10_000,
        }
    )

    with pytest.raises(ClusterError, match="working set estimate .* exceeds"):
        validate_cluster_input_budget(
            config,
            record_count=10_000,
            embedding_count=10_000,
            minimum_dimensions=2,
            maximum_dimensions=2,
        )


def test_agglomerative_budget_includes_full_ward_moment_matrix() -> None:
    record_count = 10_000
    dimensions = 3_000
    assert (
        record_count * dimensions * HDBSCAN_BYTES_PER_VECTOR_VALUE
        < MAX_CLUSTER_WORKING_SET_BYTES
    )
    assert (
        record_count * dimensions * AGGLOMERATIVE_BYTES_PER_VECTOR_VALUE
        > MAX_CLUSTER_WORKING_SET_BYTES
    )
    config = validate_algorithm_settings({"algorithm": "agglomerative"})

    with pytest.raises(ClusterError, match="working set estimate .* exceeds"):
        validate_cluster_input_budget(
            config,
            record_count=record_count,
            embedding_count=record_count,
            minimum_dimensions=dimensions,
            maximum_dimensions=dimensions,
        )


@pytest.mark.parametrize("linkage", ["complete", "average", "single"])
def test_non_ward_budget_includes_all_edge_dimension_distance_intermediates(
    linkage: str,
) -> None:
    record_count = 1_000
    dimensions = 900
    ward = validate_algorithm_settings(
        {"algorithm": "agglomerative", "linkage": "ward"}
    )
    non_ward = validate_algorithm_settings(
        {"algorithm": "agglomerative", "linkage": linkage}
    )

    assert (
        validate_cluster_input_budget(
            ward,
            record_count=record_count,
            embedding_count=record_count,
            minimum_dimensions=dimensions,
            maximum_dimensions=dimensions,
        )
        == dimensions
    )
    with pytest.raises(ClusterError, match="working set estimate .* exceeds"):
        validate_cluster_input_budget(
            non_ward,
            record_count=record_count,
            embedding_count=record_count,
            minimum_dimensions=dimensions,
            maximum_dimensions=dimensions,
        )


def test_hdbscan_effective_neighbors_cannot_exceed_record_count() -> None:
    config = validate_algorithm_settings({"algorithm": "hdbscan", "min_samples": 5})

    with pytest.raises(ClusterError, match="cannot exceed"):
        validate_cluster_input_budget(
            config,
            record_count=4,
            embedding_count=4,
            minimum_dimensions=2,
            maximum_dimensions=2,
        )


def test_total_vector_budget_fails_before_loading_or_cluster_writes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class OversizedSummaryConnection(ClusterConnection):
        def execute(
            self, query: str, params: tuple[object, ...] | None = None
        ) -> FakeResult:
            normalized = " ".join(query.split())
            if normalized.startswith("SELECT COUNT(mp.id) AS record_count"):
                return FakeResult(
                    [
                        {
                            "record_count": 10_000,
                            "embedding_count": 10_000,
                            "minimum_dimensions": 8_192,
                            "maximum_dimensions": 8_192,
                        }
                    ]
                )
            return super().execute(query, params)

    fake_connection = OversizedSummaryConnection()
    monkeypatch.setattr(
        cluster_service_module,
        "open_database_connection",
        lambda _: fake_connection,
    )

    with pytest.raises(ClusterError) as error:
        ClusterService().generate_for_run(PROJECT_ID, RUN_ID, actor_user_id=ACTOR_ID)

    message = str(error.value)
    assert "10000 records" in message
    assert "8192 dimensions" in message
    assert f"{MAX_CLUSTER_WORKING_SET_BYTES}-byte (512 MiB) limit" in message
    assert "HDBSCAN min_samples" in message
    assert fake_connection.message_pair_selects == 0
    assert fake_connection.clusters == []


def test_native_pgvector_fixture_that_exceeded_old_text_peak_reaches_estimator(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dimensions = 8_192
    record_count = 600
    assert record_count * dimensions * 192 > MAX_CLUSTER_WORKING_SET_BYTES

    class NativeSummaryConnection(ClusterConnection):
        def execute(
            self, query: str, params: tuple[object, ...] | None = None
        ) -> FakeResult:
            normalized = " ".join(query.split())
            if normalized.startswith("SELECT COUNT(mp.id) AS record_count"):
                return FakeResult(
                    [
                        {
                            "record_count": record_count,
                            "embedding_count": record_count,
                            "minimum_dimensions": dimensions,
                            "maximum_dimensions": dimensions,
                        }
                    ]
                )
            return super().execute(query, params)

    shared_vector = Vector(np.zeros(dimensions, dtype=np.float32))
    fake_connection = NativeSummaryConnection(
        algorithm_settings={
            "algorithm": "hdbscan",
            "min_cluster_size": 2,
            "min_samples": 1,
        },
        embedding_rows=[
            {
                "message_pair_id": UUID(int=index + 1),
                "embedding": shared_vector,
                "dimensions": dimensions,
            }
            for index in range(record_count)
        ],
    )
    monkeypatch.setattr(
        cluster_service_module,
        "open_database_connection",
        lambda _: fake_connection,
    )
    estimator_reached = False

    class FakeHDBSCAN:
        probabilities_ = np.ones(record_count, dtype=np.float32)

        def __init__(self, **_: object) -> None:
            return None

        def fit_predict(self, vectors: np.ndarray) -> np.ndarray:
            nonlocal estimator_reached
            estimator_reached = True
            assert vectors.shape == (record_count, dimensions)
            assert vectors.dtype == np.float32
            assert vectors.flags.c_contiguous
            return np.zeros(record_count, dtype=np.int32)

    monkeypatch.setattr(cluster_service_module, "HDBSCAN", FakeHDBSCAN)

    ClusterService().generate_for_run(PROJECT_ID, RUN_ID, actor_user_id=ACTOR_ID)

    assert estimator_reached is True
    assert fake_connection.message_pair_selects == 1
    assert len(fake_connection.memberships) == record_count


def test_hdbscan_neighbor_budget_fails_before_estimator() -> None:
    config = validate_algorithm_settings(
        {
            "algorithm": "hdbscan",
            "min_samples": 10_000,
        }
    )

    with pytest.raises(ClusterError, match="working set estimate .* exceeds"):
        validate_cluster_input_budget(
            config,
            record_count=10_000,
            embedding_count=10_000,
            minimum_dimensions=2,
            maximum_dimensions=2,
        )
