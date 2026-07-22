"""ASGI entry point for local development."""

from backend.api import create_app

app = create_app()
