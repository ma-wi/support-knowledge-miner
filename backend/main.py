"""ASGI entry point and local development server."""

from __future__ import annotations

import os

import uvicorn

from backend.api import create_app
from backend.config import load_local_environment
from backend.db import run_migrations

load_local_environment()
app = create_app(migration_runner=run_migrations)


def main() -> None:
    """Run the local API server when invoked as a module."""

    host = os.environ.get("SKM_BACKEND_HOST", "127.0.0.1")
    port = int(os.environ.get("SKM_BACKEND_PORT", "8080"))
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
