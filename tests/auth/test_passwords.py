from __future__ import annotations

from backend.auth.passwords import hash_password, verify_password


def test_password_hash_is_not_plaintext_and_verifies() -> None:
    password_hash = hash_password("correct horse battery staple")

    assert password_hash != "correct horse battery staple"
    assert "$argon2" in password_hash
    assert verify_password("correct horse battery staple", password_hash) is True
    assert verify_password("wrong password", password_hash) is False
