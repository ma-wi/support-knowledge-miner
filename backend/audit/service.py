"""Audit event persistence for protected mutations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4

from psycopg import Connection
from psycopg.rows import DictRow
from psycopg.types.json import Jsonb


@dataclass(frozen=True)
class AuditService:
    """Record auditable actions with the authenticated actor."""

    def record_event(
        self,
        connection: Connection[DictRow],
        *,
        actor_user_id: UUID | None,
        action: str,
        target_type: str,
        target_id: UUID | str | None,
        metadata: dict[str, Any] | None = None,
    ) -> UUID:
        event_id = uuid4()
        connection.execute(
            """
            INSERT INTO audit_events (
                id, actor_user_id, action, target_type, target_id, metadata
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                event_id,
                actor_user_id,
                action,
                target_type,
                str(target_id) if target_id is not None else None,
                Jsonb(metadata or {}),
            ),
        )
        return event_id
