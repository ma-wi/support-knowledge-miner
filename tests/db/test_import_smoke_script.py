from __future__ import annotations

from pathlib import Path


SMOKE_SCRIPT = Path("deployment/docker/scripts/smoke-imports.sh")


def test_import_smoke_script_covers_import_contracts() -> None:
    script = SMOKE_SCRIPT.read_text(encoding="utf-8")

    assert "/api/projects/{project_id}/imports" in script
    assert "fixture.csv" in script
    assert "fixture.json" in script
    assert "missing-header import" in script
    assert "message_pairs" in script
    assert "imports_smoke=ok" in script
