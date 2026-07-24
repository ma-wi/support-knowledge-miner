from __future__ import annotations

from typing import Any

from backend import main as backend_main


def test_main_runs_uvicorn_with_local_defaults(monkeypatch: Any) -> None:
    captured: dict[str, object] = {}

    def fake_run(app: object, *, host: str, port: int, log_level: str) -> None:
        captured.update(app=app, host=host, port=port, log_level=log_level)

    monkeypatch.delenv("SKM_BACKEND_HOST", raising=False)
    monkeypatch.delenv("SKM_BACKEND_PORT", raising=False)
    monkeypatch.setattr(backend_main.uvicorn, "run", fake_run)

    backend_main.main()

    assert captured == {
        "app": backend_main.app,
        "host": "127.0.0.1",
        "port": 8080,
        "log_level": "info",
    }
