"""Authentication and server-side session management."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import hashlib
import os
import secrets
from uuid import UUID, uuid4

from backend.audit import AuditService
from backend.auth.passwords import verify_password
from backend.config import DatabaseSettings
from backend.db.connection import open_database_connection
from backend.users.service import (
    CreateUserInput,
    PublicUser,
    UserService,
    _public_user_from_row,
)


AUTH_SCHEME = "bearer"


class AuthenticationError(ValueError):
    """Raised for invalid credentials or sessions."""


@dataclass(frozen=True)
class CurrentUser(PublicUser):
    session_id: UUID


@dataclass(frozen=True)
class AuthToken:
    access_token: str
    token_type: str
    user: PublicUser
    expires_at: datetime


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _current_user_from_row(row: dict[str, object]) -> CurrentUser:
    public = _public_user_from_row(row)
    return CurrentUser(
        id=public.id,
        username=public.username,
        first_name=public.first_name,
        last_name=public.last_name,
        email=public.email,
        created_at=public.created_at,
        updated_at=public.updated_at,
        session_id=UUID(str(row["session_id"])),
    )


class AuthService:
    def __init__(
        self,
        settings: DatabaseSettings | None = None,
        *,
        session_ttl: timedelta = timedelta(hours=12),
    ) -> None:
        self._settings = settings
        self._session_ttl = session_ttl
        self._users = UserService(settings)
        self._audit = AuditService()

    def sign_in(self, email: str, password: str) -> AuthToken:
        stored = self._users.get_stored_user_by_username(email)
        if stored is None or not verify_password(password, stored.password_hash):
            raise AuthenticationError("invalid email or password")
        token = secrets.token_urlsafe(32)
        token_hash = hash_session_token(token)
        session_id = uuid4()
        expires_at = datetime.now(UTC) + self._session_ttl
        with open_database_connection(self._settings) as connection:
            with connection.transaction():
                connection.execute(
                    """
                    INSERT INTO user_sessions (id, user_id, token_hash, expires_at)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (session_id, stored.id, token_hash, expires_at),
                )
                self._audit.record_event(
                    connection,
                    actor_user_id=stored.id,
                    action="auth.sign_in",
                    target_type="user_session",
                    target_id=session_id,
                )
        return AuthToken(
            access_token=token,
            token_type=AUTH_SCHEME,
            user=stored,
            expires_at=expires_at,
        )

    def authenticate_token(self, token: str) -> CurrentUser:
        token_hash = hash_session_token(token)
        with open_database_connection(self._settings) as connection:
            row = connection.execute(
                """
                SELECT u.id, u.username, u.first_name, u.last_name, u.email,
                       u.created_at, u.updated_at, s.id AS session_id
                FROM user_sessions s
                JOIN users u ON u.id = s.user_id
                WHERE s.token_hash = %s
                  AND s.revoked_at IS NULL
                  AND s.expires_at > now()
                  AND u.deleted_at IS NULL
                """,
                (token_hash,),
            ).fetchone()
        if row is None:
            raise AuthenticationError("invalid or expired session")
        return _current_user_from_row(dict(row))

    def sign_out(self, token: str, *, actor_user_id: UUID) -> None:
        token_hash = hash_session_token(token)
        with open_database_connection(self._settings) as connection:
            with connection.transaction():
                row = connection.execute(
                    """
                    UPDATE user_sessions
                    SET revoked_at = now()
                    WHERE token_hash = %s AND revoked_at IS NULL
                    RETURNING id
                    """,
                    (token_hash,),
                ).fetchone()
                if row is not None:
                    self._audit.record_event(
                        connection,
                        actor_user_id=actor_user_id,
                        action="auth.sign_out",
                        target_type="user_session",
                        target_id=UUID(str(row["id"])),
                    )

    def seed_initial_user_from_env(self) -> PublicUser | None:
        password = os.environ.get("SKM_INITIAL_PASSWORD")
        email = os.environ.get("SKM_INITIAL_EMAIL")
        first_name = os.environ.get("SKM_INITIAL_FIRST_NAME", "Initial")
        last_name = os.environ.get("SKM_INITIAL_LAST_NAME", "User")
        if not password and not email:
            return None
        if not password or not email:
            raise ValueError(
                "SKM_INITIAL_PASSWORD and SKM_INITIAL_EMAIL must be set together"
            )
        with open_database_connection(self._settings) as connection:
            row = connection.execute("SELECT COUNT(*) AS count FROM users").fetchone()
        existing_count = int(str(row["count"] if row is not None else 0))
        if existing_count > 0:
            return None
        return self._users.create_user(
            CreateUserInput(
                username=email,
                first_name=first_name,
                last_name=last_name,
                email=email,
                password=password,
            ),
            actor_user_id=None,
            audit_action="user.initial_seed",
        )
