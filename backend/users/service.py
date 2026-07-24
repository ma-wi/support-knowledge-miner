"""Equal-permission local user management."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

from psycopg import IntegrityError

from backend.audit import AuditService
from backend.auth.passwords import hash_password
from backend.config import DatabaseSettings
from backend.db.connection import open_database_connection


class UserError(ValueError):
    """Raised when a user-management operation is invalid."""


@dataclass(frozen=True)
class PublicUser:
    id: UUID
    username: str
    first_name: str
    last_name: str
    email: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class StoredUser(PublicUser):
    password_hash: str


@dataclass(frozen=True)
class CreateUserInput:
    username: str
    first_name: str
    last_name: str
    email: str
    password: str


@dataclass(frozen=True)
class UpdateUserInput:
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None


def _clean(value: str, field: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise UserError(f"{field} must not be empty")
    return cleaned


def _public_user_from_row(row: dict[str, object]) -> PublicUser:
    return PublicUser(
        id=UUID(str(row["id"])),
        username=str(row["username"]),
        first_name=str(row["first_name"]),
        last_name=str(row["last_name"]),
        email=str(row["email"]),
        created_at=row["created_at"],  # type: ignore[arg-type]
        updated_at=row["updated_at"],  # type: ignore[arg-type]
    )


def _stored_user_from_row(row: dict[str, object]) -> StoredUser:
    public = _public_user_from_row(row)
    return StoredUser(
        id=public.id,
        username=public.username,
        first_name=public.first_name,
        last_name=public.last_name,
        email=public.email,
        created_at=public.created_at,
        updated_at=public.updated_at,
        password_hash=str(row["password_hash"]),
    )


class UserService:
    def __init__(self, settings: DatabaseSettings | None = None) -> None:
        self._settings = settings
        self._audit = AuditService()

    def list_users(self) -> list[PublicUser]:
        with open_database_connection(self._settings) as connection:
            rows = connection.execute(
                """
                SELECT id, username, first_name, last_name, email, created_at, updated_at
                FROM users
                WHERE deleted_at IS NULL
                ORDER BY username ASC
                """
            ).fetchall()
        return [_public_user_from_row(dict(row)) for row in rows]

    def get_user(self, user_id: UUID) -> PublicUser | None:
        with open_database_connection(self._settings) as connection:
            row = connection.execute(
                """
                SELECT id, username, first_name, last_name, email, created_at, updated_at
                FROM users
                WHERE id = %s AND deleted_at IS NULL
                """,
                (user_id,),
            ).fetchone()
        return _public_user_from_row(dict(row)) if row is not None else None

    def get_stored_user_by_username(self, username: str) -> StoredUser | None:
        login = username.strip()
        with open_database_connection(self._settings) as connection:
            row = connection.execute(
                """
                SELECT id, username, first_name, last_name, email,
                       password_hash, created_at, updated_at
                FROM users
                WHERE (username = %s OR email = %s) AND deleted_at IS NULL
                """,
                (login, login),
            ).fetchone()
        return _stored_user_from_row(dict(row)) if row is not None else None

    def create_user(
        self,
        data: CreateUserInput,
        *,
        actor_user_id: UUID | None,
        audit_action: str = "user.create",
    ) -> PublicUser:
        user_id = uuid4()
        username = _clean(data.username, "username")
        first_name = _clean(data.first_name, "first_name")
        last_name = _clean(data.last_name, "last_name")
        email = _clean(data.email, "email")
        password_hash = hash_password(data.password)
        try:
            with open_database_connection(self._settings) as connection:
                with connection.transaction():
                    row = connection.execute(
                        """
                        INSERT INTO users (
                            id, username, first_name, last_name, email, password_hash
                        )
                        VALUES (%s, %s, %s, %s, %s, %s)
                        RETURNING id, username, first_name, last_name, email,
                                  created_at, updated_at
                        """,
                        (
                            user_id,
                            username,
                            first_name,
                            last_name,
                            email,
                            password_hash,
                        ),
                    ).fetchone()
                    if row is None:
                        raise RuntimeError("user insert returned no row")
                    self._audit.record_event(
                        connection,
                        actor_user_id=actor_user_id,
                        action=audit_action,
                        target_type="user",
                        target_id=user_id,
                    )
        except IntegrityError as exc:
            raise UserError("email already exists") from exc
        return _public_user_from_row(dict(row))

    def update_user(
        self,
        user_id: UUID,
        data: UpdateUserInput,
        *,
        actor_user_id: UUID,
    ) -> PublicUser:
        current = self.get_user(user_id)
        if current is None:
            raise UserError("user not found")
        username = (
            _clean(data.username, "username")
            if data.username is not None
            else current.username
        )
        first_name = (
            _clean(data.first_name, "first_name")
            if data.first_name is not None
            else current.first_name
        )
        last_name = (
            _clean(data.last_name, "last_name")
            if data.last_name is not None
            else current.last_name
        )
        email = _clean(data.email, "email") if data.email is not None else current.email
        try:
            with open_database_connection(self._settings) as connection:
                with connection.transaction():
                    row = connection.execute(
                        """
                        UPDATE users
                        SET username = %s,
                            first_name = %s,
                            last_name = %s,
                            email = %s,
                            updated_at = now()
                        WHERE id = %s AND deleted_at IS NULL
                        RETURNING id, username, first_name, last_name, email,
                                  created_at, updated_at
                        """,
                        (username, first_name, last_name, email, user_id),
                    ).fetchone()
                    if row is None:
                        raise UserError("user not found")
                    self._audit.record_event(
                        connection,
                        actor_user_id=actor_user_id,
                        action="user.update",
                        target_type="user",
                        target_id=user_id,
                    )
        except IntegrityError as exc:
            raise UserError("email already exists") from exc
        return _public_user_from_row(dict(row))

    def set_password(
        self, user_id: UUID, password: str, *, actor_user_id: UUID
    ) -> None:
        password_hash = hash_password(password)
        with open_database_connection(self._settings) as connection:
            with connection.transaction():
                result = connection.execute(
                    """
                    UPDATE users
                    SET password_hash = %s,
                        updated_at = now()
                    WHERE id = %s AND deleted_at IS NULL
                    """,
                    (password_hash, user_id),
                )
                if result.rowcount != 1:
                    raise UserError("user not found")
                self._audit.record_event(
                    connection,
                    actor_user_id=actor_user_id,
                    action="user.password_set",
                    target_type="user",
                    target_id=user_id,
                )

    def delete_user(self, user_id: UUID, *, actor_user_id: UUID) -> None:
        if user_id == actor_user_id:
            raise UserError("users cannot delete themselves")
        with open_database_connection(self._settings) as connection:
            with connection.transaction():
                result = connection.execute(
                    """
                    UPDATE users
                    SET deleted_at = now(),
                        updated_at = now()
                    WHERE id = %s AND deleted_at IS NULL
                    """,
                    (user_id,),
                )
                if result.rowcount != 1:
                    raise UserError("user not found")
                self._audit.record_event(
                    connection,
                    actor_user_id=actor_user_id,
                    action="user.delete",
                    target_type="user",
                    target_id=user_id,
                )
