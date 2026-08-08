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


def project(
    project_id: UUID,
    name: str,
    ticket_url_template: str | None = None,
) -> PublicProject:
    return PublicProject(
        id=project_id,
        name=name,
        lifecycle_state="active",
        created_at=NOW,
        updated_at=NOW,
        ticket_url_template=ticket_url_template,
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
        return self.update_project_settings(
            project_id,
            name=name,
            ticket_url_template=None,
            ticket_url_template_unchanged=True,
            actor_user_id=actor_user_id,
        )

    def update_project_settings(
        self,
        project_id: UUID,
        *,
        name: str,
        ticket_url_template: str | None = None,
        ticket_url_template_unchanged: bool = False,
        actor_user_id: UUID,
    ) -> PublicProject:
        self.actor_ids.append(actor_user_id)
        for index, item in enumerate(self.projects):
            if item.id == project_id:
                if ticket_url_template == "ftp://tickets.example.test/<ticket_id>":
                    raise ProjectError(
                        "ticket URL template is invalid",
                        field_errors={
                            "ticket_url_template": (
                                "Die Ticket-Link-Vorlage muss eine http(s)-URL "
                                "mit <ticket_id> sein."
                            )
                        },
                    )
                renamed = project(
                    project_id,
                    name.strip(),
                    item.ticket_url_template
                    if ticket_url_template_unchanged
                    else ticket_url_template,
                )
                self.projects[index] = renamed
                return renamed
        from backend.projects.service import ProjectNotFoundError

        raise ProjectNotFoundError("project not found")

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
    assert [item["ticket_url_template"] for item in listed.json()] == [None, None]

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
    assert renamed.json()["ticket_url_template"] is None

    bad_delete = client.request(
        "DELETE",
        f"/api/projects/{PROJECT_A_ID}",
        headers=auth_headers(),
        json={"confirmation_name": "Alpha"},
    )
    assert bad_delete.status_code == 422
    assert bad_delete.json()["code"] == "VALIDATION_FAILED"

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


def test_project_settings_update_validates_ticket_url_template(
    client: TestClient,
) -> None:
    invalid = client.patch(
        f"/api/projects/{PROJECT_A_ID}",
        headers=auth_headers(),
        json={
            "name": "Alpha",
            "ticket_url_template": "ftp://tickets.example.test/<ticket_id>",
        },
    )

    assert invalid.status_code == 422
    payload = invalid.json()
    assert payload["code"] == "VALIDATION_FAILED"
    assert payload["suggestedAction"] == "correct-input"
    assert payload["fieldErrors"] == [
        {
            "field": "ticket_url_template",
            "message": "Die Ticket-Link-Vorlage muss eine http(s)-URL mit <ticket_id> sein.",
        }
    ]

    updated = client.patch(
        f"/api/projects/{PROJECT_A_ID}",
        headers=auth_headers(),
        json={
            "name": "Alpha Settings",
            "ticket_url_template": "https://tickets.example.test/T-<ticket_id>",
        },
    )

    assert updated.status_code == 200
    assert updated.json()["name"] == "Alpha Settings"
    assert (
        updated.json()["ticket_url_template"]
        == "https://tickets.example.test/T-<ticket_id>"
    )


def test_project_settings_update_maps_missing_project_to_safe_problem(
    client: TestClient,
) -> None:
    missing_id = UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")

    response = client.patch(
        f"/api/projects/{missing_id}",
        headers=auth_headers(),
        json={
            "name": "Missing",
            "ticket_url_template": "https://tickets.example.test/T-<ticket_id>",
        },
    )

    assert response.status_code == 404
    payload = response.json()
    assert payload["code"] == "PROJECT_NOT_FOUND"
    assert payload["suggestedAction"] == "reload"
    assert payload["detail"] == "Das Projekt wurde nicht gefunden."
