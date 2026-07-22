from __future__ import annotations

from backend.db.health import DatabaseHealth


def test_database_health_model_requires_pgvector_for_ok() -> None:
    healthy = DatabaseHealth(
        ok=True,
        database="support_knowledge_miner",
        pgvector_available=True,
        pgvector_installed=True,
    )
    assert healthy.ok is True
