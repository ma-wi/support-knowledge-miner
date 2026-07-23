from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest

import backend.clusters.service as cluster_service_module
from backend.clusters import ClusterService

ACTOR_ID = UUID("11111111-1111-1111-1111-111111111111")
PROJECT_ID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
RUN_ID = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
DATASET_ID = UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
PAIR_A = UUID("dddddddd-dddd-dddd-dddd-ddddddddddda")
PAIR_B = UUID("dddddddd-dddd-dddd-dddd-dddddddddddb")
PAIR_C = UUID("dddddddd-dddd-dddd-dddd-dddddddddddc")
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


class ClusterConnection:
    def __init__(self) -> None:
        self.clusters: list[dict[str, object]] = []
        self.memberships: list[dict[str, object]] = []
        self.message_pair_selects = 0

    def __enter__(self) -> ClusterConnection:
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def transaction(self) -> FakeTransaction:
        return FakeTransaction()

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
                    }
                ]
            )
        if normalized.startswith("SELECT id FROM clusters"):
            return (
                FakeResult([{"id": self.clusters[0]["id"]}])
                if self.clusters
                else FakeResult()
            )
        if normalized.startswith(
            "SELECT id, ticketid, messagegroupid, message, answer"
        ):
            self.message_pair_selects += 1
            return FakeResult(
                [
                    {
                        "id": PAIR_A,
                        "ticketid": "T-1",
                        "messagegroupid": "G-1",
                        "message": "Reset password",
                        "answer": "Use reset link",
                    },
                    {
                        "id": PAIR_B,
                        "ticketid": "T-2",
                        "messagegroupid": "G-2",
                        "message": "Return order",
                        "answer": "Use returns portal",
                    },
                    {
                        "id": PAIR_C,
                        "ticketid": "T-3",
                        "messagegroupid": "G-3",
                        "message": "Warranty request",
                        "answer": "Open warranty form",
                    },
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


def unwrap_json(value: object) -> object:
    return getattr(value, "obj", value)


def test_generate_for_run_uses_single_pass_grouping_and_marks_outliers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_connection = ClusterConnection()
    monkeypatch.setattr(
        cluster_service_module,
        "open_database_connection",
        lambda _: fake_connection,
    )

    clusters = ClusterService().generate_for_run(
        PROJECT_ID, RUN_ID, actor_user_id=ACTOR_ID
    )

    assert fake_connection.message_pair_selects == 1
    assert len(clusters) == 2
    assert {cluster.member_count for cluster in clusters} == {1, 2}
    assert any(cluster.is_outlier for cluster in clusters)
    assert any(not cluster.is_outlier for cluster in clusters)
    assert all(cluster.metadata["non_quadratic"] is True for cluster in clusters)
    assert len(fake_connection.memberships) == 3
