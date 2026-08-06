from __future__ import annotations

from datetime import UTC, datetime
from typing import cast
from uuid import UUID

import numpy as np
from pgvector import Vector
import pytest

import backend.clusters.service as cluster_service_module
from backend.clusters import (
    ClusterError,
    ClusterManualUpdate,
    ClusterService,
    ClusterSet,
)
from backend.clusters.service import (
    AGGLOMERATIVE_BYTES_PER_VECTOR_VALUE,
    HDBSCAN_BYTES_PER_VECTOR_VALUE,
    HDBSCAN_FIXED_BYTES_PER_RECORD,
    HDBSCAN_NEIGHBOR_BYTES_PER_CELL,
    MAX_CLUSTER_WORKING_SET_BYTES,
    NATIVE_FETCH_BYTES_PER_VALUE,
    NATIVE_VECTOR_FETCH_BATCH_SIZE,
    ClusterSetBasisBudget,
    ClusterSetInput,
    ClusterSetSummaryInput,
    _apply_outlier_threshold,
    _summary_sample_strategy,
    _validate_summary_call_budget,
    validate_algorithm_settings,
    validate_cluster_input_budget,
)
from backend.providers import ProviderConfiguration, ProviderError

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
        if normalized.startswith("LOCK TABLE cluster_sets"):
            return FakeResult()
        if normalized.startswith("SELECT id FROM cluster_sets"):
            return FakeResult()
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


class ClusterStartConnectionWithoutGlobalGuard(ParentStatusConnection):
    def __init__(self) -> None:
        super().__init__(parent_status="completed")

    def execute(
        self, query: str, params: tuple[object, ...] | None = None
    ) -> FakeResult:
        normalized = " ".join(query.split())
        if normalized.startswith("LOCK TABLE cluster_sets") or normalized.startswith(
            "SELECT id FROM cluster_sets"
        ):
            raise AssertionError("global Cluster-Set start guard must not be used")
        if normalized.startswith("SELECT COUNT(id) AS record_count"):
            return FakeResult([{"record_count": 4}])
        if normalized.startswith("INSERT INTO cluster_sets"):
            assert params is not None
            return FakeResult(
                [
                    {
                        "id": params[0],
                        "project_id": params[1],
                        "indexing_run_id": params[2],
                        "dataset_version_id": params[3],
                        "dataset_display_name": params[20],
                        "indexing_deleted_at": params[21],
                        "parent_cluster_set_id": params[4],
                        "display_name": params[5],
                        "status": "queued",
                        "progress": 0,
                        "phase": "queued",
                        "derivation_type": params[6],
                        "vector_basis": params[7],
                        "message_weight": params[8],
                        "answer_weight": params[9],
                        "algorithm": params[10],
                        "parameters": unwrap_json(params[11]),
                        "source_snapshot": unwrap_json(params[12]),
                        "llm_provider": params[13],
                        "llm_provider_configuration_id": params[14],
                        "llm_provider_display_name": params[15],
                        "llm_model": params[16],
                        "llm_parameters": unwrap_json(params[17]),
                        "llm_sample_strategy": unwrap_json(params[18]),
                        "error_code": None,
                        "error_message": None,
                        "diagnostics": {},
                        "started_at": None,
                        "completed_at": None,
                        "cancel_requested_at": None,
                        "deleted_at": None,
                        "created_at": NOW,
                        "updated_at": NOW,
                        "cluster_count": 0,
                    }
                ]
            )
        if normalized.startswith("INSERT INTO cluster_set_events"):
            return FakeResult()
        if normalized.startswith("INSERT INTO audit_events"):
            return FakeResult()
        return super().execute(query, params)


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
                        "provider": "ollama",
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
        if normalized.startswith("LOCK TABLE cluster_sets"):
            return FakeResult()
        if normalized.startswith("SELECT id FROM cluster_sets"):
            return FakeResult()
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


class ClusterManualUpdateConnection:
    def __init__(self) -> None:
        self.cluster_set_touch_count = 0

    def __enter__(self) -> ClusterManualUpdateConnection:
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def transaction(self) -> FakeTransaction:
        return FakeTransaction()

    def execute(
        self, query: str, params: tuple[object, ...] | None = None
    ) -> FakeResult:
        normalized = " ".join(query.split())
        if normalized.startswith("UPDATE clusters c"):
            assert params is not None
            assert params[6:] == (CLUSTER_A, PROJECT_ID)
            return FakeResult(
                [
                    {
                        "analysis_run_id": RUN_ID,
                        "cluster_set_id": PARENT_CLUSTER_SET_ID,
                    }
                ]
            )
        if normalized.startswith("UPDATE cluster_sets SET updated_at"):
            assert params == (PARENT_CLUSTER_SET_ID, PROJECT_ID)
            self.cluster_set_touch_count += 1
            return FakeResult()
        if normalized.startswith("INSERT INTO audit_events"):
            return FakeResult()
        if normalized.startswith("INSERT INTO cluster_set_events"):
            return FakeResult()
        if normalized.startswith("SELECT id, status FROM cluster_sets"):
            assert params == (PARENT_CLUSTER_SET_ID, PROJECT_ID)
            return FakeResult([{"id": PARENT_CLUSTER_SET_ID, "status": "completed"}])
        if normalized.startswith("SELECT c.id, c.project_id"):
            assert params == (PROJECT_ID, PARENT_CLUSTER_SET_ID)
            return FakeResult(
                [
                    {
                        "id": CLUSTER_A,
                        "project_id": PROJECT_ID,
                        "analysis_run_id": RUN_ID,
                        "dataset_version_id": DATASET_ID,
                        "cluster_set_id": PARENT_CLUSTER_SET_ID,
                        "auto_title": "Cluster A",
                        "manual_title": "Manual title",
                        "auto_category": "General",
                        "manual_category": None,
                        "auto_status": "unreviewed",
                        "manual_status": "reviewed",
                        "auto_summary_question": None,
                        "auto_summary_answer": None,
                        "score": 0.9,
                        "is_outlier": False,
                        "algorithm": "hdbscan",
                        "metadata": {},
                        "created_at": NOW,
                        "updated_at": NOW,
                        "member_count": 1,
                    }
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


def test_manual_cluster_update_touches_cluster_set_updated_at(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_connection = ClusterManualUpdateConnection()
    monkeypatch.setattr(
        cluster_service_module,
        "open_database_connection",
        lambda _: fake_connection,
    )

    cluster = ClusterService().update_cluster(
        PROJECT_ID,
        CLUSTER_A,
        ClusterManualUpdate(manual_title="Manual title", manual_status="reviewed"),
        actor_user_id=ACTOR_ID,
    )

    assert cluster.manual_title == "Manual title"
    assert cluster.manual_status == "reviewed"
    assert fake_connection.cluster_set_touch_count == 1


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


def test_active_cluster_set_does_not_block_second_start(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        cluster_service_module,
        "open_database_connection",
        lambda _: ClusterStartConnectionWithoutGlobalGuard(),
    )

    cluster_set = ClusterService().start_cluster_set(
        PROJECT_ID,
        ClusterSetInput(indexing_run_id=RUN_ID),
        actor_user_id=ACTOR_ID,
    )

    assert cluster_set.status == "queued"
    assert cluster_set.phase == "queued"


def test_cancel_queued_summary_regeneration_keeps_cluster_set_completed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class SummaryCancelConnection:
        def __init__(self) -> None:
            self.update_params: tuple[object, ...] | None = None
            self.event_metadata: dict[str, object] | None = None

        def __enter__(self) -> SummaryCancelConnection:
            return self

        def __exit__(self, *_: object) -> None:
            return None

        def transaction(self) -> FakeTransaction:
            return FakeTransaction()

        def execute(
            self, query: str, params: tuple[object, ...] | None = None
        ) -> FakeResult:
            normalized = " ".join(query.split())
            if normalized.startswith("SELECT status, phase FROM cluster_sets"):
                return FakeResult([{"status": "queued", "phase": "queued_summary"}])
            if normalized.startswith("UPDATE cluster_sets SET status = %s"):
                assert params is not None
                self.update_params = params
                return FakeResult()
            if normalized.startswith("INSERT INTO cluster_set_events"):
                assert params is not None
                self.event_metadata = cast(dict[str, object], unwrap_json(params[5]))
                return FakeResult()
            raise AssertionError(f"unexpected query: {normalized}")

    fake_connection = SummaryCancelConnection()
    monkeypatch.setattr(
        cluster_service_module,
        "open_database_connection",
        lambda _: fake_connection,
    )
    service = ClusterService()
    monkeypatch.setattr(
        service,
        "get_cluster_set",
        lambda *_args, **_kwargs: ClusterSet(
            id=PARENT_CLUSTER_SET_ID,
            project_id=PROJECT_ID,
            indexing_run_id=RUN_ID,
            dataset_version_id=DATASET_ID,
            dataset_display_name="Fixture dataset",
            indexing_deleted_at=None,
            parent_cluster_set_id=None,
            display_name="Summary Set",
            status="completed",
            progress=100,
            phase="completed",
            derivation_type="root",
            vector_basis="message",
            message_weight=1.0,
            answer_weight=0.0,
            algorithm="hdbscan",
            parameters={"min_cluster_size": 2},
            source_snapshot={},
            llm_provider="ollama",
            llm_provider_configuration_id=None,
            llm_provider_display_name="Ollama",
            llm_model="llama3.1",
            llm_parameters={},
            llm_sample_strategy={},
            error_code=None,
            error_message=None,
            diagnostics={"summary_regeneration_cancelled": True},
            started_at=NOW,
            completed_at=NOW,
            cancel_requested_at=NOW,
            deleted_at=None,
            created_at=NOW,
            updated_at=NOW,
            cluster_count=2,
        ),
    )

    cluster_set = service.cancel_cluster_set(
        PROJECT_ID, PARENT_CLUSTER_SET_ID, actor_user_id=ACTOR_ID
    )

    assert cluster_set.status == "completed"
    assert cluster_set.phase == "completed"
    assert fake_connection.update_params is not None
    assert fake_connection.update_params[:5] == (
        "completed",
        "completed",
        True,
        True,
        "completed",
    )
    assert fake_connection.event_metadata == {
        "status": "completed",
        "phase": "completed",
    }


def test_execute_cancelled_cluster_set_generation_stays_cancelled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class CancelledClusterExecutionConnection:
        def __init__(self) -> None:
            self.update_params: tuple[object, ...] | None = None

        def __enter__(self) -> CancelledClusterExecutionConnection:
            return self

        def __exit__(self, *_: object) -> None:
            return None

        def transaction(self) -> FakeTransaction:
            return FakeTransaction()

        def execute(
            self, query: str, params: tuple[object, ...] | None = None
        ) -> FakeResult:
            normalized = " ".join(query.split())
            if normalized.startswith("UPDATE cluster_sets cs SET status = 'running'"):
                return FakeResult(
                    [
                        {
                            "id": PARENT_CLUSTER_SET_ID,
                            "project_id": PROJECT_ID,
                            "indexing_run_id": RUN_ID,
                            "dataset_version_id": DATASET_ID,
                            "vector_basis": "message",
                            "message_weight": 1.0,
                            "answer_weight": 0.0,
                            "algorithm": "hdbscan",
                            "parameters": {"min_cluster_size": 2},
                            "source_snapshot": {},
                            "llm_provider": None,
                            "llm_provider_configuration_id": None,
                            "llm_provider_display_name": None,
                            "llm_model": None,
                            "llm_sample_strategy": {},
                            "provider": "ollama",
                            "model": "bge-m3:latest",
                        }
                    ]
                )
            if normalized.startswith("SELECT status FROM cluster_sets"):
                return FakeResult([{"status": "cancelling"}])
            if normalized.startswith("UPDATE cluster_sets SET status = 'cancelled'"):
                assert params is not None
                self.update_params = params
                return FakeResult()
            raise AssertionError(f"unexpected query: {normalized}")

    fake_connection = CancelledClusterExecutionConnection()
    monkeypatch.setattr(
        cluster_service_module,
        "open_database_connection",
        lambda _: fake_connection,
    )

    ClusterService().execute_queued_cluster_set(PARENT_CLUSTER_SET_ID)

    assert fake_connection.update_params is not None
    assert unwrap_json(fake_connection.update_params[0]) == {"cancelled": True}
    assert fake_connection.update_params[1] == PARENT_CLUSTER_SET_ID


def test_running_summary_regeneration_cancel_keeps_cluster_set_completed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class RunningSummaryCancelConnection:
        def __init__(self) -> None:
            self.update_params: tuple[object, ...] | None = None
            self.update_query: str | None = None

        def __enter__(self) -> RunningSummaryCancelConnection:
            return self

        def __exit__(self, *_: object) -> None:
            return None

        def transaction(self) -> FakeTransaction:
            return FakeTransaction()

        def execute(
            self, query: str, params: tuple[object, ...] | None = None
        ) -> FakeResult:
            normalized = " ".join(query.split())
            if normalized.startswith("UPDATE cluster_sets SET status = 'running'"):
                return FakeResult(
                    [
                        {
                            "id": PARENT_CLUSTER_SET_ID,
                            "project_id": PROJECT_ID,
                            "llm_provider": "ollama",
                            "llm_provider_configuration_id": PARENT_CLUSTER_SET_ID,
                            "llm_provider_display_name": "Ollama",
                            "llm_model": "llama3.1",
                            "llm_sample_strategy": {"requested": 10},
                        }
                    ]
                )
            if normalized.startswith("SELECT status FROM cluster_sets"):
                return FakeResult([{"status": "cancelling"}])
            if normalized.startswith("UPDATE cluster_sets SET status = 'completed'"):
                assert params is not None
                self.update_query = normalized
                self.update_params = params
                return FakeResult()
            raise AssertionError(f"unexpected query: {normalized}")

    fake_connection = RunningSummaryCancelConnection()
    monkeypatch.setattr(
        cluster_service_module,
        "open_database_connection",
        lambda _: fake_connection,
    )
    service = ClusterService()
    monkeypatch.setattr(
        service,
        "_generate_cluster_summaries",
        lambda **_kwargs: None,
    )

    service.execute_queued_cluster_set_summary_regeneration(PARENT_CLUSTER_SET_ID)

    assert fake_connection.update_query is not None
    assert "completed_at" not in fake_connection.update_query
    assert fake_connection.update_params is not None
    assert unwrap_json(fake_connection.update_params[0]) == {
        "summary_regeneration_cancelled": True
    }
    assert fake_connection.update_params[1] == PARENT_CLUSTER_SET_ID


def test_summary_regeneration_success_preserves_cluster_completed_at(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class SummarySuccessConnection:
        def __init__(self) -> None:
            self.completed_query: str | None = None
            self.completed_params: tuple[object, ...] | None = None

        def __enter__(self) -> SummarySuccessConnection:
            return self

        def __exit__(self, *_: object) -> None:
            return None

        def transaction(self) -> FakeTransaction:
            return FakeTransaction()

        def execute(
            self, query: str, params: tuple[object, ...] | None = None
        ) -> FakeResult:
            normalized = " ".join(query.split())
            if normalized.startswith("UPDATE cluster_sets SET status = 'running'"):
                return FakeResult(
                    [
                        {
                            "id": PARENT_CLUSTER_SET_ID,
                            "project_id": PROJECT_ID,
                            "llm_provider": "ollama",
                            "llm_provider_configuration_id": PARENT_CLUSTER_SET_ID,
                            "llm_provider_display_name": "Ollama",
                            "llm_model": "llama3.1",
                            "llm_sample_strategy": {"requested": 10},
                        }
                    ]
                )
            if normalized.startswith("SELECT status FROM cluster_sets"):
                return FakeResult([{"status": "running"}])
            if normalized.startswith("UPDATE cluster_sets SET status = 'completed'"):
                assert params is not None
                self.completed_query = normalized
                self.completed_params = params
                return FakeResult()
            raise AssertionError(f"unexpected query: {normalized}")

    fake_connection = SummarySuccessConnection()
    monkeypatch.setattr(
        cluster_service_module,
        "open_database_connection",
        lambda _: fake_connection,
    )
    service = ClusterService()
    monkeypatch.setattr(service, "_generate_cluster_summaries", lambda **_: None)

    service.execute_queued_cluster_set_summary_regeneration(PARENT_CLUSTER_SET_ID)

    assert fake_connection.completed_query is not None
    assert "completed_at" not in fake_connection.completed_query
    assert fake_connection.completed_params is not None
    assert unwrap_json(fake_connection.completed_params[0]) == {
        "summary_regenerated": True
    }


def test_summary_regeneration_start_requires_successful_status_update(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeProviderService:
        def ensure_text_generation_model(
            self,
            _provider_ref: UUID | str,
            _model: str,
        ) -> ProviderConfiguration:
            return ProviderConfiguration(
                id=PARENT_CLUSTER_SET_ID,
                provider="ollama",
                display_name="Ollama",
                endpoint_url="http://127.0.0.1:11434",
                available_models=["llama3.1"],
                manual_models=[],
                llm_models=["llama3.1"],
                api_key_set=False,
                updated_at=NOW,
            )

    class SummaryStartRaceConnection:
        def __init__(self) -> None:
            self.event_written = False

        def __enter__(self) -> SummaryStartRaceConnection:
            return self

        def __exit__(self, *_: object) -> None:
            return None

        def transaction(self) -> FakeTransaction:
            return FakeTransaction()

        def execute(
            self, query: str, params: tuple[object, ...] | None = None
        ) -> FakeResult:
            normalized = " ".join(query.split())
            if normalized.startswith("SELECT cs.id, cs.status, COUNT(c.id)"):
                return FakeResult(
                    [
                        {
                            "id": PARENT_CLUSTER_SET_ID,
                            "status": "completed",
                            "cluster_count": 2,
                        }
                    ]
                )
            if normalized.startswith("UPDATE cluster_sets SET status = 'queued'"):
                return FakeResult()
            if normalized.startswith("INSERT INTO cluster_set_events"):
                self.event_written = True
                return FakeResult()
            raise AssertionError(f"unexpected query: {normalized}")

    fake_connection = SummaryStartRaceConnection()
    monkeypatch.setattr(
        cluster_service_module,
        "open_database_connection",
        lambda _: fake_connection,
    )
    service = ClusterService(provider_service=FakeProviderService())  # type: ignore[arg-type]

    with pytest.raises(ClusterError) as error:
        service.start_cluster_set_summary_regeneration(
            PROJECT_ID,
            PARENT_CLUSTER_SET_ID,
            ClusterSetSummaryInput(
                llm_provider_id=PARENT_CLUSTER_SET_ID,
                llm_model="llama3.1",
            ),
            actor_user_id=ACTOR_ID,
        )

    assert error.value.code == "CLUSTER_SET_NOT_COMPLETE"
    assert fake_connection.event_written is False


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


def test_cluster_set_hdbscan_uses_all_local_jobs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    estimator_kwargs: dict[str, object] = {}

    class FakeHDBSCAN:
        probabilities_ = np.ones(2, dtype=np.float32)

        def __init__(self, **kwargs: object) -> None:
            estimator_kwargs.update(kwargs)
            return None

        def fit_predict(self, vectors: np.ndarray) -> np.ndarray:
            assert vectors.shape == (2, 2)
            return np.array([0, 0], dtype=np.int32)

    monkeypatch.setattr(cluster_service_module, "HDBSCAN", FakeHDBSCAN)
    config = validate_algorithm_settings(
        {"algorithm": "hdbscan", "min_cluster_size": 2}
    )

    labels, probabilities = ClusterService()._cluster_vectors(
        config, np.ones((2, 2), dtype=np.float32)
    )

    assert labels == [0, 0]
    assert probabilities == [1.0, 1.0]
    assert estimator_kwargs["n_jobs"] == -1


def test_hdbscan_pca_reduces_vectors_before_estimator(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    estimator_shape: tuple[int, int] | None = None

    class FakeHDBSCAN:
        probabilities_ = np.ones(6, dtype=np.float32)

        def __init__(self, **_: object) -> None:
            return None

        def fit_predict(self, vectors: np.ndarray) -> np.ndarray:
            nonlocal estimator_shape
            estimator_shape = tuple(vectors.shape)
            return np.zeros(len(vectors), dtype=np.int32)

    monkeypatch.setattr(cluster_service_module, "HDBSCAN", FakeHDBSCAN)
    config = validate_algorithm_settings(
        {
            "algorithm": "hdbscan",
            "min_cluster_size": 2,
            "reduction_method": "pca",
            "reduction_dimensions": 2,
            "execution_backend": "cpu",
        }
    )
    vectors = np.arange(30, dtype=np.float32).reshape((6, 5))

    labels, probabilities = ClusterService()._cluster_vectors(config, vectors)

    assert labels == [0, 0, 0, 0, 0, 0]
    assert probabilities == [1.0] * 6
    assert estimator_shape == (6, 2)


def test_hdbscan_cuml_backend_reports_missing_accelerator(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_import_module = cluster_service_module.importlib.import_module

    def fake_import_module(name: str) -> object:
        if name == "cuml.cluster":
            raise ImportError("missing cuml")
        return original_import_module(name)

    monkeypatch.setattr(
        cluster_service_module.importlib,
        "import_module",
        fake_import_module,
    )
    config = validate_algorithm_settings(
        {
            "algorithm": "hdbscan",
            "min_cluster_size": 2,
            "execution_backend": "cuml",
        }
    )

    with pytest.raises(ClusterError) as error:
        ClusterService()._cluster_vectors(config, np.ones((2, 2), dtype=np.float32))

    assert error.value.code == "CLUSTER_ACCELERATOR_UNAVAILABLE"
    assert error.value.retryable is True


def test_hdbscan_umap_reports_missing_reduction_as_retryable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_import_module = cluster_service_module.importlib.import_module

    def fake_import_module(name: str) -> object:
        if name in {"cuml.manifold", "umap"}:
            raise ImportError("missing reduction dependency")
        return original_import_module(name)

    monkeypatch.setattr(
        cluster_service_module.importlib,
        "import_module",
        fake_import_module,
    )
    config = validate_algorithm_settings(
        {
            "algorithm": "hdbscan",
            "min_cluster_size": 2,
            "reduction_method": "umap",
            "reduction_dimensions": 2,
            "execution_backend": "auto",
        }
    )

    with pytest.raises(ClusterError) as error:
        ClusterService()._cluster_vectors(config, np.ones((4, 3), dtype=np.float32))

    assert error.value.code == "CLUSTER_REDUCTION_UNAVAILABLE"
    assert error.value.retryable is True


def test_hdbscan_auto_backend_falls_back_to_cpu(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_import_module = cluster_service_module.importlib.import_module
    cpu_called = False

    def fake_import_module(name: str) -> object:
        if name == "cuml.cluster":
            raise ImportError("missing cuml")
        return original_import_module(name)

    class FakeHDBSCAN:
        probabilities_ = np.ones(3, dtype=np.float32)

        def __init__(self, **_: object) -> None:
            return None

        def fit_predict(self, vectors: np.ndarray) -> np.ndarray:
            nonlocal cpu_called
            cpu_called = True
            assert vectors.shape == (3, 2)
            return np.array([0, 0, 1], dtype=np.int32)

    monkeypatch.setattr(
        cluster_service_module.importlib,
        "import_module",
        fake_import_module,
    )
    monkeypatch.setattr(cluster_service_module, "HDBSCAN", FakeHDBSCAN)
    config = validate_algorithm_settings(
        {
            "algorithm": "hdbscan",
            "min_cluster_size": 2,
            "execution_backend": "auto",
        }
    )

    labels, probabilities, diagnostics = ClusterService()._fit_hdbscan_vectors(
        config, np.ones((3, 2), dtype=np.float32)
    )

    assert cpu_called is True
    assert labels == [0, 0, 1]
    assert probabilities == [1.0, 1.0, 1.0]
    assert diagnostics["execution_backend_requested"] == "auto"
    assert diagnostics["execution_backend_effective"] == "cpu"
    assert diagnostics["execution_backend_fallback"] is True


def test_execute_hdbscan_with_reduction_publishes_clustering_after_reducing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class ReductionProgressConnection:
        def __init__(self) -> None:
            self.completed_params: tuple[object, ...] | None = None

        def __enter__(self) -> ReductionProgressConnection:
            return self

        def __exit__(self, *_: object) -> None:
            return None

        def transaction(self) -> FakeTransaction:
            return FakeTransaction()

        def execute(
            self, query: str, params: tuple[object, ...] | None = None
        ) -> FakeResult:
            normalized = " ".join(query.split())
            if normalized.startswith("UPDATE cluster_sets cs SET status = 'running'"):
                return FakeResult(
                    [
                        {
                            "id": PARENT_CLUSTER_SET_ID,
                            "project_id": PROJECT_ID,
                            "indexing_run_id": RUN_ID,
                            "dataset_version_id": DATASET_ID,
                            "vector_basis": "message",
                            "message_weight": 1.0,
                            "answer_weight": 0.0,
                            "algorithm": "hdbscan",
                            "parameters": {
                                "min_cluster_size": 2,
                                "reduction_method": "pca",
                                "reduction_dimensions": 2,
                                "execution_backend": "cpu",
                            },
                            "source_snapshot": {},
                            "llm_provider": None,
                            "llm_provider_configuration_id": None,
                            "llm_provider_display_name": None,
                            "llm_model": None,
                            "llm_sample_strategy": {},
                            "provider": "ollama",
                            "model": "bge-m3:latest",
                        }
                    ]
                )
            if normalized.startswith("UPDATE cluster_sets SET status = 'completed'"):
                assert params is not None
                self.completed_params = params
                return FakeResult()
            return FakeResult()

    fake_connection = ReductionProgressConnection()
    monkeypatch.setattr(
        cluster_service_module,
        "open_database_connection",
        lambda _: fake_connection,
    )
    service = ClusterService()
    progress_phases: list[str] = []
    pair_ids = [UUID(int=index + 1) for index in range(4)]

    monkeypatch.setattr(service, "_raise_if_cluster_set_cancelled", lambda *_: None)
    monkeypatch.setattr(
        service,
        "_cluster_set_input_summary",
        lambda *_args, **_kwargs: {"record_count": 4},
    )
    monkeypatch.setattr(
        service,
        "_validate_cluster_set_basis_budget",
        lambda *_args, **_kwargs: ClusterSetBasisBudget(
            output_dimensions=4,
            message_dimensions=4,
            answer_dimensions=None,
        ),
    )
    monkeypatch.setattr(
        service,
        "_load_cluster_set_embedding_matrix",
        lambda *_args, **_kwargs: (
            pair_ids,
            np.arange(16, dtype=np.float32).reshape((4, 4)),
            [0.0] * 4,
        ),
    )
    monkeypatch.setattr(
        service,
        "_reduce_hdbscan_vectors",
        lambda _config, vectors: np.asarray(vectors[:, :2], dtype=np.float32),
    )

    def fake_fit_hdbscan_vectors(
        _config: object,
        vectors: np.ndarray,
    ) -> tuple[list[int], list[float], dict[str, object]]:
        assert progress_phases[-1] == "clustering"
        assert vectors.shape == (4, 2)
        return (
            [0, 0, 1, 1],
            [1.0] * 4,
            {
                "execution_backend_requested": "cpu",
                "execution_backend_effective": "cpu",
                "execution_backend_fallback": False,
                "effective_dimensions": 2,
            },
        )

    monkeypatch.setattr(service, "_fit_hdbscan_vectors", fake_fit_hdbscan_vectors)
    monkeypatch.setattr(service, "_insert_cluster_set_clusters", lambda *_, **__: None)
    monkeypatch.setattr(service, "_record_cluster_set_event", lambda *_, **__: None)
    monkeypatch.setattr(
        service,
        "_publish_cluster_set_progress",
        lambda _cluster_set_id, _progress, phase: progress_phases.append(phase),
    )

    service.execute_queued_cluster_set(PARENT_CLUSTER_SET_ID)

    assert progress_phases == ["loading", "reducing", "clustering", "persisting"]
    assert fake_connection.completed_params is not None
    diagnostics = unwrap_json(fake_connection.completed_params[0])
    assert isinstance(diagnostics, dict)
    assert diagnostics["clustering"] == {
        "execution_backend_requested": "cpu",
        "execution_backend_effective": "cpu",
        "execution_backend_fallback": False,
        "effective_dimensions": 2,
    }


def test_algorithm_settings_accepts_hdbscan_reduction_and_backend_parameters() -> None:
    config = validate_algorithm_settings(
        {
            "algorithm": "hdbscan",
            "min_cluster_size": 5,
            "reduction_method": "umap",
            "reduction_dimensions": 12,
            "umap_n_neighbors": 20,
            "umap_min_dist": 0.2,
            "execution_backend": "auto",
        }
    )

    assert config.parameters["reduction_method"] == "umap"
    assert config.parameters["reduction_dimensions"] == 12
    assert config.parameters["umap_n_neighbors"] == 20
    assert config.parameters["umap_min_dist"] == 0.2
    assert config.parameters["execution_backend"] == "auto"


def test_cluster_summary_response_requires_schema_json() -> None:
    service = ClusterService()

    parsed = service._parse_cluster_summary_response(
        '{"title":"Reset","category":"Account","question":"How?","answer":"Use link","rationale":null}'
    )
    assert parsed["title"] == "Reset"
    assert parsed["question"] == "How?"

    with pytest.raises(ClusterError, match="Cluster summary response"):
        service._parse_cluster_summary_response("not json")


def test_cluster_summary_response_accepts_json_inside_model_wrapping() -> None:
    service = ClusterService()

    prefaced = service._parse_cluster_summary_response(
        'Hier ist das JSON:\n{"title":"Versand","category":null,'
        '"question":"Wann kommt es?","answer":"In zwei Tagen.",'
        '"rationale":"Mehrere Beispiele fragen nach Versand."}\nDanke.'
    )
    fenced = service._parse_cluster_summary_response(
        '```json\n[{"title":"Login","category":"Konto",'
        '"question":"Wie melde ich mich an?","answer":"Mit E-Mail.",'
        '"rationale":null}]\n```'
    )

    assert prefaced["title"] == "Versand"
    assert prefaced["category"] is None
    assert fenced["title"] == "Login"
    assert fenced["question"] == "Wie melde ich mich an?"


def test_cluster_summary_response_accepts_common_model_variants() -> None:
    service = ClusterService()

    nested_german = service._parse_cluster_summary_response(
        '{"summary":{"titel":"Retouren","kategorie":"Logistik",'
        '"frage":"Wie sende ich Ware zurück?","antwort":"Nutze das Retourenportal.",'
        '"begruendung":"Mehrere Beispiele fragen nach Rücksendung."}}'
    )
    multi_candidate = service._parse_cluster_summary_response(
        'Schema: {"title":"string","category":"string|null",'
        '"question":"string","answer":"string","rationale":"string|null"}\n'
        'Antwort: {"title":"Zahlung","category":"Checkout",'
        '"question":"Warum wird die Zahlung abgelehnt?",'
        '"answer":"Bitte Zahlungsmethode prüfen.","rationale":null}'
    )
    array_candidate = service._parse_cluster_summary_response(
        '[{"message":"Rohbeispiel","answer":"Nicht die Summary"},'
        '{"title":"Login","question":"Wie melde ich mich an?",'
        '"answer":"Mit E-Mail und Passwort.","rationale":null}]'
    )
    multiline = service._parse_cluster_summary_response(
        '{"title":"Status","category":null,"question":"Wo ist die Bestellung?",'
        '"answer":"Prüfe den Versandstatus.\nFalls nötig, kontaktiere Support.",'
        '"rationale":null}'
    )
    labeled_text = service._parse_cluster_summary_response(
        "Titel: Widerruf\n"
        "Kategorie: Retoure\n"
        "Zusammengefasste Frage: Wie kann ein Kunde widerrufen?\n"
        "Zusammengefasste Antwort: Nutze das Widerrufsformular.\n"
        "Begründung: Die Beispiele behandeln Widerrufsfristen."
    )
    smart_quotes = service._parse_cluster_summary_response(
        "Antwort:\n"
        "{“title”: “Lieferadresse”, “category”: “Versand”, "
        "“question”: “Wie ändere ich die Lieferadresse?”, "
        "“answer”: “Ändere sie vor Versand im Konto.”, “rationale”: null}"
    )
    encoded_json = service._parse_cluster_summary_response(
        '"{\\"title\\":\\"Adresse\\",\\"category\\":\\"Versand\\",'
        '\\"question\\":\\"Wie ändere ich die Adresse?\\",'
        '\\"answer\\":\\"Passe sie vor Versand im Konto an.\\",'
        '\\"rationale\\":null}"'
    )

    assert nested_german["title"] == "Retouren"
    assert nested_german["question"] == "Wie sende ich Ware zurück?"
    assert multi_candidate["title"] == "Zahlung"
    assert array_candidate["answer"] == "Mit E-Mail und Passwort."
    assert multiline["answer"] == (
        "Prüfe den Versandstatus.\nFalls nötig, kontaktiere Support."
    )
    assert labeled_text["title"] == "Widerruf"
    assert labeled_text["question"] == "Wie kann ein Kunde widerrufen?"
    assert smart_quotes["title"] == "Lieferadresse"
    assert smart_quotes["answer"] == "Ändere sie vor Versand im Konto."
    assert encoded_json["title"] == "Adresse"


def test_cluster_summary_prompt_is_strict_and_truncates_long_examples() -> None:
    service = ClusterService()

    prompt = service._cluster_summary_prompt(
        [{"message": "M" * 2_000, "answer": "A" * 2_000}]
    )

    assert "Antworte ausschließlich mit einem einzelnen JSON-Objekt" in prompt
    assert "Keine Markdown-Fences" in prompt
    assert "M" * 1_200 in prompt
    assert "M" * 1_201 not in prompt


def test_cluster_summary_parse_failure_uses_extractive_fallback() -> None:
    class BrokenProviderService:
        def generate_text(
            self,
            _provider_ref: UUID | str,
            _model: str,
            _prompt: str,
        ) -> str:
            return "not json"

    service = ClusterService(provider_service=BrokenProviderService())  # type: ignore[arg-type]

    summary, mode, reason = service._cluster_summary_from_provider_or_examples(
        llm_provider="ollama",
        llm_model="qwen2.5:7b",
        prompt="Prompt",
        examples=[
            {
                "message": "Wie kann ich mein Passwort zurücksetzen?",
                "answer": "Nutze den Passwort-zurücksetzen-Link im Login.",
            }
        ],
    )

    assert mode == "fallback"
    assert reason is not None
    assert reason.startswith("parse_error:")
    assert summary["title"] == "kann ich mein Passwort zurücksetzen"
    assert summary["question"] == "Wie kann ich mein Passwort zurücksetzen?"
    assert summary["answer"] == "Nutze den Passwort-zurücksetzen-Link im Login."
    assert summary["rationale"] is not None
    assert "Fallback-Summary" in summary["rationale"]


def test_cluster_summary_provider_error_uses_extractive_fallback() -> None:
    class TimeoutProviderService:
        def generate_text(
            self,
            _provider_ref: UUID | str,
            _model: str,
            _prompt: str,
        ) -> str:
            raise ProviderError("LLM provider request failed: TimeoutError")

    service = ClusterService(provider_service=TimeoutProviderService())  # type: ignore[arg-type]

    summary, mode, reason = service._cluster_summary_from_provider_or_examples(
        llm_provider="ollama",
        llm_model="qwen2.5:7b",
        prompt="Prompt",
        examples=[
            {
                "message": "Paket ist beschädigt angekommen",
                "answer": "Bitte sende Fotos und die Bestellnummer an den Support.",
            }
        ],
    )

    assert mode == "fallback"
    assert reason == "provider_error:ProviderError"
    assert summary["title"] == "Paket ist beschädigt angekommen"
    assert summary["question"] == (
        "Wie ist diese Anfrage zu bearbeiten: Paket ist beschädigt angekommen"
    )
    assert summary["answer"] == (
        "Bitte sende Fotos und die Bestellnummer an den Support."
    )


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
    estimator_kwargs: dict[str, object] = {}

    class FakeHDBSCAN:
        probabilities_ = np.ones(record_count, dtype=np.float32)

        def __init__(self, **kwargs: object) -> None:
            estimator_kwargs.update(kwargs)
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
    assert estimator_kwargs["n_jobs"] == -1
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
