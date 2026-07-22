from __future__ import annotations

from backend.api import create_app


def test_auth_api_openapi_does_not_expose_password_hash_or_plaintext_password_response() -> (
    None
):
    schema_text = str(create_app().openapi())

    assert "password_hash" not in schema_text
    assert "access_token" in schema_text
    assert "SignInRequest" in schema_text
    assert "CreateUserRequest" in schema_text
    assert "SetPasswordRequest" in schema_text


def test_user_management_routes_are_registered() -> None:
    routes = {str(getattr(route, "path", "")) for route in create_app().routes}

    assert "/api/auth/sign-in" in routes
    assert "/api/auth/me" in routes
    assert "/api/users" in routes
    assert "/api/users/{user_id}" in routes
    assert "/api/users/{user_id}/password" in routes
