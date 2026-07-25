from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from backend.api import create_app
from backend.auth import CurrentUser
from backend.auth.service import AuthenticationError
from backend.projects import ProjectError, PublicProject


OWNER_ID = UUID("11111111-1111-1111-1111-111111111111")
PROJECT_A_ID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
PROJECT_B_ID = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
NOW = datetime(2026, 7, 22, tzinfo=UTC)


class FakeAuthService:
    def seed_initial_user_from_env(self) -> None:
        return None

    def authenticate_token(self, token: str) -> CurrentUser:
        if token != "valid-token":
            raise AuthenticationError("invalid or expired session")
        return CurrentUser(
            id=OWNER_ID,
            first_name="Local",
            last_name="Owner",
            email="owner@example.test",
            created_at=NOW,
            updated_at=NOW,
            session_id=uuid4(),
        )


def project(project_id: UUID, name: str) -> PublicProject:
    return PublicProject(
        id=project_id,
        name=name,
        lifecycle_state="active",
        created_at=NOW,
        updated_at=NOW,
    )


class FakeProjectService:
    def __init__(self) -> None:
        self.projects = [project(PROJECT_A_ID, "Alpha"), project(PROJECT_B_ID, "Beta")]
        self.actor_ids: list[UUID] = []

    def list_projects(self) -> list[PublicProject]:
        return self.projects

    def get_project(self, project_id: UUID) -> PublicProject | None:
        return next((item for item in self.projects if item.id == project_id), None)

    def create_project(self, name: str, *, actor_user_id: UUID) -> PublicProject:
        self.actor_ids.append(actor_user_id)
        created = project(UUID("cccccccc-cccc-cccc-cccc-cccccccccccc"), name.strip())
        self.projects.append(created)
        return created

    def rename_project(
        self, project_id: UUID, name: str, *, actor_user_id: UUID
    ) -> PublicProject:
        self.actor_ids.append(actor_user_id)
        for index, item in enumerate(self.projects):
            if item.id == project_id:
                renamed = project(project_id, name.strip())
                self.projects[index] = renamed
                return renamed
        raise ProjectError("project not found")

    def delete_project(
        self,
        project_id: UUID,
        *,
        actor_user_id: UUID,
        confirmation_name: str,
    ) -> None:
        self.actor_ids.append(actor_user_id)
        existing = self.get_project(project_id)
        if existing is None:
            raise ProjectError("project not found")
        if existing.name != confirmation_name:
            raise ProjectError(
                "project deletion confirmation does not match project name"
            )
        self.projects = [item for item in self.projects if item.id != project_id]


@pytest.fixture
def client() -> TestClient:
    return TestClient(
        create_app(
            auth_service=FakeAuthService(),  # type: ignore[arg-type]
            project_service=FakeProjectService(),  # type: ignore[arg-type]
        )
    )


def auth_headers(token: str = "valid-token") -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_project_routes_require_authentication(client: TestClient) -> None:
    assert client.get("/api/projects").status_code == 401
    assert client.post("/api/projects", json={"name": "Gamma"}).status_code == 401


def test_project_lifecycle_and_deleted_project_is_not_returned(
    client: TestClient,
) -> None:
    listed = client.get("/api/projects", headers=auth_headers())
    assert listed.status_code == 200
    assert [item["name"] for item in listed.json()] == ["Alpha", "Beta"]

    created = client.post(
        "/api/projects",
        headers=auth_headers(),
        json={"name": "Gamma"},
    )
    assert created.status_code == 201
    assert created.json()["name"] == "Gamma"

    opened = client.get(f"/api/projects/{PROJECT_A_ID}", headers=auth_headers())
    assert opened.status_code == 200
    assert opened.json()["id"] == str(PROJECT_A_ID)

    renamed = client.patch(
        f"/api/projects/{PROJECT_A_ID}",
        headers=auth_headers(),
        json={"name": "Alpha renamed"},
    )
    assert renamed.status_code == 200
    assert renamed.json()["name"] == "Alpha renamed"

    bad_delete = client.request(
        "DELETE",
        f"/api/projects/{PROJECT_A_ID}",
        headers=auth_headers(),
        json={"confirmation_name": "Alpha"},
    )
    assert bad_delete.status_code == 400

    deleted = client.request(
        "DELETE",
        f"/api/projects/{PROJECT_A_ID}",
        headers=auth_headers(),
        json={"confirmation_name": "Alpha renamed"},
    )
    assert deleted.status_code == 204

    after_delete = client.get(f"/api/projects/{PROJECT_A_ID}", headers=auth_headers())
    assert after_delete.status_code == 404
    remaining = client.get("/api/projects", headers=auth_headers())
    assert [item["name"] for item in remaining.json()] == ["Beta", "Gamma"]
