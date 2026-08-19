from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest

import backend.projects.service as project_service_module
from backend.projects import ProjectError, ProjectService


PROJECT_ID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
ACTOR_ID = UUID("11111111-1111-1111-1111-111111111111")
NOW = datetime(2026, 7, 22, tzinfo=UTC)


class FakeResult:
    def __init__(self, row: dict[str, object] | None = None, rowcount: int = 0) -> None:
        self._row = row
        self.rowcount = rowcount

    def fetchone(self) -> dict[str, object] | None:
        return self._row


class FakeTransaction:
    def __enter__(self) -> FakeTransaction:
        return self

    def __exit__(self, *_: object) -> None:
        return None


class RenameBetweenConfirmationAndDeleteConnection:
    deleted_without_confirmed_name = False

    def __enter__(self) -> RenameBetweenConfirmationAndDeleteConnection:
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def transaction(self) -> FakeTransaction:
        return FakeTransaction()

    def execute(
        self, query: str, params: tuple[object, ...] | None = None
    ) -> FakeResult:
        normalized = " ".join(query.split())
        if normalized.startswith("SELECT id, name"):
            return FakeResult(
                {
                    "id": PROJECT_ID,
                    "name": "Alpha",
                    "lifecycle_state": "active",
                    "created_at": NOW,
                    "updated_at": NOW,
                    "ticket_url_template": None,
                }
            )
        if normalized.startswith("DELETE FROM projects"):
            if "name = %s" in normalized:
                assert params == (PROJECT_ID, "Alpha")
                return FakeResult(None, rowcount=0)
            self.deleted_without_confirmed_name = True
            return FakeResult(rowcount=1)
        if normalized.startswith("INSERT INTO audit_events"):
            return FakeResult(rowcount=1)
        raise AssertionError(f"unexpected query: {normalized}")


def test_delete_project_rejects_stale_confirmation_when_name_changed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_connection = RenameBetweenConfirmationAndDeleteConnection()
    monkeypatch.setattr(
        project_service_module,
        "open_database_connection",
        lambda _: fake_connection,
    )

    with pytest.raises(ProjectError, match="confirmation"):
        ProjectService().delete_project(
            PROJECT_ID,
            actor_user_id=ACTOR_ID,
            confirmation_name="Alpha",
        )

    assert fake_connection.deleted_without_confirmed_name is False


class ProjectSettingsConnection:
    def __init__(self) -> None:
        self.update_params: tuple[object, ...] | None = None

    def __enter__(self) -> ProjectSettingsConnection:
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def transaction(self) -> FakeTransaction:
        return FakeTransaction()

    def execute(
        self, query: str, params: tuple[object, ...] | None = None
    ) -> FakeResult:
        normalized = " ".join(query.split())
        if normalized.startswith("UPDATE projects"):
            self.update_params = params
            assert params is not None
            return FakeResult(
                {
                    "id": PROJECT_ID,
                    "name": "Alpha",
                    "lifecycle_state": "active",
                    "created_at": NOW,
                    "updated_at": NOW,
                    "ticket_url_template": "https://tickets.example.test/T-<ticket_id>",
                    "llm_taxonomy_max_source_clusters": (
                        200 if bool(params[3]) else params[4]
                    ),
                    "llm_taxonomy_max_prompt_characters": (
                        80_000 if bool(params[5]) else params[6]
                    ),
                    "llm_taxonomy_max_total_keyword_terms": (
                        250_000 if bool(params[7]) else params[8]
                    ),
                }
            )
        if normalized.startswith("INSERT INTO audit_events"):
            return FakeResult(rowcount=1)
        raise AssertionError(f"unexpected query: {normalized}")


def test_update_project_settings_persists_valid_ticket_url_template(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_connection = ProjectSettingsConnection()
    monkeypatch.setattr(
        project_service_module,
        "open_database_connection",
        lambda _: fake_connection,
    )

    project = ProjectService().update_project_settings(
        PROJECT_ID,
        name=" Alpha ",
        ticket_url_template=" https://tickets.example.test/T-<ticket_id> ",
        actor_user_id=ACTOR_ID,
    )

    assert project.name == "Alpha"
    assert project.ticket_url_template == "https://tickets.example.test/T-<ticket_id>"
    assert fake_connection.update_params == (
        "Alpha",
        False,
        "https://tickets.example.test/T-<ticket_id>",
        True,
        None,
        True,
        None,
        True,
        None,
        ACTOR_ID,
        PROJECT_ID,
    )


def test_update_project_settings_persists_valid_cluster_budgets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_connection = ProjectSettingsConnection()
    monkeypatch.setattr(
        project_service_module,
        "open_database_connection",
        lambda _: fake_connection,
    )

    project = ProjectService().update_project_settings(
        PROJECT_ID,
        name="Alpha",
        ticket_url_template_unchanged=True,
        llm_taxonomy_max_source_clusters=350,
        llm_taxonomy_max_source_clusters_unchanged=False,
        llm_taxonomy_max_prompt_characters=240_000,
        llm_taxonomy_max_prompt_characters_unchanged=False,
        llm_taxonomy_max_total_keyword_terms=750_000,
        llm_taxonomy_max_total_keyword_terms_unchanged=False,
        actor_user_id=ACTOR_ID,
    )

    assert project.llm_taxonomy_max_source_clusters == 350
    assert project.llm_taxonomy_max_prompt_characters == 240_000
    assert project.llm_taxonomy_max_total_keyword_terms == 750_000
    assert fake_connection.update_params is not None
    assert fake_connection.update_params[3:9] == (
        False,
        350,
        False,
        240_000,
        False,
        750_000,
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("llm_taxonomy_max_source_clusters", 0),
        ("llm_taxonomy_max_source_clusters", 501),
        ("llm_taxonomy_max_prompt_characters", 9_999),
        ("llm_taxonomy_max_prompt_characters", 500_001),
        ("llm_taxonomy_max_total_keyword_terms", 999),
        ("llm_taxonomy_max_total_keyword_terms", 1_000_001),
    ],
)
def test_update_project_settings_rejects_cluster_budget_outside_hard_caps(
    field: str, value: int
) -> None:
    kwargs: dict[str, object] = {
        "name": "Alpha",
        f"{field}_unchanged": False,
        field: value,
        "actor_user_id": ACTOR_ID,
    }

    with pytest.raises(ProjectError) as exc_info:
        ProjectService().update_project_settings(PROJECT_ID, **kwargs)  # type: ignore[arg-type]

    assert exc_info.value.code == "VALIDATION_FAILED"
    assert set(exc_info.value.field_errors) == {field}


@pytest.mark.parametrize(
    "template",
    [
        "javascript:alert(1)<ticket_id>",
        "https://user:pass@example.test/tickets/<ticket_id>",
        "https://tickets.example.test:invalid/tickets/<ticket_id>",
        "https://tickets.example.test/tickets/",
        "https://tickets.example.test/tickets/<ticket_id> bad",
        "x" * 2049 + "<ticket_id>",
    ],
)
def test_update_project_settings_rejects_invalid_ticket_url_template(
    template: str,
) -> None:
    with pytest.raises(ProjectError) as exc_info:
        ProjectService().update_project_settings(
            PROJECT_ID,
            name="Alpha",
            ticket_url_template=template,
            actor_user_id=ACTOR_ID,
        )

    assert exc_info.value.code == "VALIDATION_FAILED"
    assert exc_info.value.field_errors == {
        "ticket_url_template": (
            "Die Ticket-Link-Vorlage muss eine http(s)-URL mit <ticket_id> sein."
        )
    }
