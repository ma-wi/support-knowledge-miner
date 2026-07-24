from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from backend.api import create_app
from backend.auth import AuthToken, CurrentUser
from backend.auth.service import AuthenticationError
from backend.users import CreateUserInput, PublicUser, UpdateUserInput
from backend.users.service import UserError


OWNER_ID = UUID("11111111-1111-1111-1111-111111111111")
OTHER_ID = UUID("22222222-2222-2222-2222-222222222222")
NOW = datetime(2026, 7, 22, tzinfo=UTC)


def public_user(
    user_id: UUID,
    email: str,
    first_name: str = "Local",
    last_name: str = "User",
) -> PublicUser:
    return PublicUser(
        id=user_id,
        username=email,
        first_name=first_name,
        last_name=last_name,
        email=email,
        created_at=NOW,
        updated_at=NOW,
    )


class FakeAuthService:
    def __init__(self) -> None:
        self.owner = public_user(
            OWNER_ID,
            "owner@example.test",
            first_name="Local",
            last_name="Owner",
        )
        self.valid_token = "valid-token"
        self.signed_out = False

    def seed_initial_user_from_env(self) -> None:
        return None

    def sign_in(self, email: str, password: str) -> AuthToken:
        if email != "owner@example.test" or password != "owner-password":
            raise AuthenticationError("invalid email or password")
        return AuthToken(
            access_token=self.valid_token,
            token_type="bearer",
            user=self.owner,
            expires_at=NOW + timedelta(hours=12),
        )

    def authenticate_token(self, token: str) -> CurrentUser:
        if token != self.valid_token:
            raise AuthenticationError("invalid or expired session")
        return CurrentUser(
            id=self.owner.id,
            username=self.owner.username,
            first_name=self.owner.first_name,
            last_name=self.owner.last_name,
            email=self.owner.email,
            created_at=self.owner.created_at,
            updated_at=self.owner.updated_at,
            session_id=uuid4(),
        )

    def sign_out(self, token: str, *, actor_user_id: UUID) -> None:
        if token == self.valid_token and actor_user_id == OWNER_ID:
            self.signed_out = True


class FakeUserService:
    def __init__(self) -> None:
        self.users = [
            public_user(
                OWNER_ID,
                "owner@example.test",
                first_name="Local",
                last_name="Owner",
            )
        ]
        self.password_updates: list[UUID] = []
        self.deleted: list[UUID] = []

    def list_users(self) -> list[PublicUser]:
        return self.users

    def create_user(
        self,
        data: CreateUserInput,
        *,
        actor_user_id: UUID | None,
        audit_action: str = "user.create",
    ) -> PublicUser:
        assert actor_user_id == OWNER_ID
        created = public_user(
            OTHER_ID,
            data.email,
            first_name=data.first_name,
            last_name=data.last_name,
        )
        self.users.append(created)
        return created

    def update_user(
        self, user_id: UUID, data: UpdateUserInput, *, actor_user_id: UUID
    ) -> PublicUser:
        assert actor_user_id == OWNER_ID
        for index, user in enumerate(self.users):
            if user.id == user_id:
                updated = public_user(
                    user_id,
                    data.email or user.email,
                    first_name=data.first_name or user.first_name,
                    last_name=data.last_name or user.last_name,
                )
                self.users[index] = updated
                return updated
        raise UserError("user not found")

    def set_password(
        self, user_id: UUID, password: str, *, actor_user_id: UUID
    ) -> None:
        assert actor_user_id == OWNER_ID
        assert password != ""
        self.password_updates.append(user_id)

    def delete_user(self, user_id: UUID, *, actor_user_id: UUID) -> None:
        if user_id == actor_user_id:
            raise UserError("users cannot delete themselves")
        self.deleted.append(user_id)
        self.users = [user for user in self.users if user.id != user_id]


@pytest.fixture
def client() -> TestClient:
    return TestClient(
        create_app(
            auth_service=FakeAuthService(),  # type: ignore[arg-type]
            user_service=FakeUserService(),  # type: ignore[arg-type]
        )
    )


def auth_headers(token: str = "valid-token") -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def assert_no_secret_fields(payload: object) -> None:
    text = str(payload)
    assert "password_hash" not in text
    assert "owner-password" not in text


def test_sign_in_success_returns_bearer_token_and_redacted_user(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/auth/sign-in",
        json={"email": "owner@example.test", "password": "owner-password"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["access_token"] == "valid-token"
    assert payload["token_type"] == "bearer"
    assert payload["user"]["email"] == "owner@example.test"
    assert "username" not in payload["user"]
    assert_no_secret_fields(payload)


def test_sign_in_invalid_credentials_are_generic(client: TestClient) -> None:
    response = client.post(
        "/api/auth/sign-in",
        json={"email": "owner@example.test", "password": "wrong"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "invalid credentials"}


def test_protected_routes_reject_missing_or_invalid_bearer_token(
    client: TestClient,
) -> None:
    missing = client.get("/api/users")
    invalid = client.get("/api/users", headers=auth_headers("invalid-token"))

    assert missing.status_code == 401
    assert invalid.status_code == 401
    assert missing.json() == {"detail": "authentication required"}
    assert invalid.json() == {"detail": "authentication required"}


def test_authenticated_user_crud_password_and_self_delete_contract(
    client: TestClient,
) -> None:
    users = client.get("/api/users", headers=auth_headers())
    assert users.status_code == 200
    assert users.json()[0]["email"] == "owner@example.test"
    assert "username" not in users.json()[0]
    assert_no_secret_fields(users.json())

    created = client.post(
        "/api/users",
        headers=auth_headers(),
        json={
            "first_name": "Support",
            "last_name": "Curator",
            "email": "curator@example.test",
            "password": "curator-password",
        },
    )
    assert created.status_code == 201
    assert created.json()["id"] == str(OTHER_ID)
    assert_no_secret_fields(created.json())

    updated = client.patch(
        f"/api/users/{OTHER_ID}",
        headers=auth_headers(),
        json={"first_name": "Knowledge"},
    )
    assert updated.status_code == 200
    assert updated.json()["first_name"] == "Knowledge"

    password = client.post(
        f"/api/users/{OTHER_ID}/password",
        headers=auth_headers(),
        json={"password": "changed-password"},
    )
    assert password.status_code == 204
    assert not password.content

    self_delete = client.delete(f"/api/users/{OWNER_ID}", headers=auth_headers())
    assert self_delete.status_code == 400
    assert "delete themselves" in self_delete.json()["detail"]

    deleted = client.delete(f"/api/users/{OTHER_ID}", headers=auth_headers())
    assert deleted.status_code == 204


def test_app_startup_runs_migrations_before_initial_user_seed() -> None:
    events: list[str] = []

    class StartupAuthService(FakeAuthService):
        def seed_initial_user_from_env(self) -> None:
            events.append("seed")

    with TestClient(
        create_app(
            auth_service=StartupAuthService(),  # type: ignore[arg-type]
            user_service=FakeUserService(),  # type: ignore[arg-type]
            migration_runner=lambda: events.append("migrate"),
        )
    ):
        pass

    assert events == ["migrate", "seed"]
