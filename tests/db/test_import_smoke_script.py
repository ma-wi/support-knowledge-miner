from __future__ import annotations

from pathlib import Path


SMOKE_SCRIPT = Path("deployment/docker/scripts/smoke-imports.sh")


def test_import_smoke_script_covers_import_contracts() -> None:
    script = SMOKE_SCRIPT.read_text(encoding="utf-8")

    assert "/api/projects/{project_id}/imports" in script
    assert "fixture.csv" in script
    assert "fixture.json" in script
    assert "missing-header import" in script
    assert '"Content-Type": media_type' in script
    assert "filename*=UTF-8''{filename}" in script
    assert "content=content.encode" in script
    assert '"source_type"' not in script
    assert '"source_name"' not in script
    assert '"content":' not in script
    assert "DATABASE_BATCH_SIZE = 2" in script
    assert "injected batch failure" in script
    assert "temporary import file was not removed" in script
    assert "message_pairs" in script
    assert "imports_smoke=ok" in script
