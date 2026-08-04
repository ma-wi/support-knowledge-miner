from __future__ import annotations

from pathlib import Path


SMOKE_SCRIPT = Path("deployment/docker/scripts/smoke-providers-profiles.sh")


def test_provider_profile_smoke_script_covers_secret_and_indexing_runs() -> None:
    script = SMOKE_SCRIPT.read_text(encoding="utf-8")

    assert "/api/providers/openai" in script
    assert "sk-local-smoke-secret" in script
    assert "secret leaked" in script
    assert "SKM_PROVIDER_ENCRYPTION_KEY" in script
    assert "fernet:" in script
    assert "credential was not encrypted in storage" in script
    assert "/indexing-runs" in script
    assert "INDEXING_CLOUD_CONFIRMATION_REQUIRED" in script
    assert "analysis profile table still exists" in script
    assert "providers_indexing_smoke=ok" in script
