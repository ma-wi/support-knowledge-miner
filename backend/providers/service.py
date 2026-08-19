"""Provider configuration and embedding-provider calls."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from http.client import HTTPConnection, HTTPSConnection, HTTPException
import json
import logging
import math
import os
import re
from threading import Lock
from typing import Any
from urllib.parse import urlparse
from uuid import UUID, uuid4

from psycopg.types.json import Jsonb

from backend.audit import AuditService
from backend.config import DatabaseSettings
from backend.db.connection import open_database_connection
from backend.providers.secrets import (
    ProviderSecretError,
    decrypt_provider_secret,
    encrypt_provider_secret,
)

LLM_DIAGNOSTIC_LOGGER = logging.getLogger("uvicorn.error.skm.llm")
SUPPORTED_PROVIDERS = {"openai", "ollama"}
MAX_MODELS = 200
MAX_MODEL_LENGTH = 160
MAX_ENDPOINT_LENGTH = 500
PROVIDER_CHECK_TIMEOUT_SECONDS = 2.0
PROVIDER_EMBEDDING_TIMEOUT_SECONDS = 60.0
PROVIDER_LLM_TIMEOUT_SECONDS = 180.0
MAX_EMBEDDING_BATCH_SIZE = 64
MAX_EMBEDDING_TEXT_LENGTH = 100_000
MAX_EMBEDDING_BATCH_CHARACTERS = 500_000
MAX_EMBEDDING_RESPONSE_BYTES = 16 * 1024 * 1024
MAX_EMBEDDING_DIMENSIONS = 8_192
MAX_LLM_PROMPT_CHARACTERS = 80_000
HARD_MAX_LLM_PROMPT_CHARACTERS = 500_000
MAX_LLM_OUTPUT_TOKENS = 128_000
MAX_LLM_RESPONSE_BYTES = 8 * 1024 * 1024
MAX_LLM_OUTPUT_CHARACTERS = 50_000
HARD_MAX_LLM_OUTPUT_CHARACTERS = 1_000_000
LLM_SUMMARY_OUTPUT_TOKENS = 700
LLM_SUMMARY_JSON_INSTRUCTIONS = (
    "You generate compact JSON for support-cluster summaries. Return exactly one "
    "JSON object. Do not include markdown, code fences, comments, prose before the "
    "object, prose after the object, or schema examples."
)
LLM_SUMMARY_JSON_SCHEMA: dict[str, object] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "title": {
            "type": "string",
            "description": "Short cluster title, maximum 80 characters.",
        },
        "category": {
            "type": ["string", "null"],
            "description": "Short category label or null.",
        },
        "question": {
            "type": "string",
            "description": "Canonical customer question represented by the cluster.",
        },
        "answer": {
            "type": "string",
            "description": "Canonical support answer represented by the cluster.",
        },
        "rationale": {
            "type": ["string", "null"],
            "description": "Brief reason for the summary or null.",
        },
    },
    "required": ["title", "category", "question", "answer", "rationale"],
}
OLLAMA_PULL_TIMEOUT_SECONDS = 1800.0
OPENAI_API_HOST = "api.openai.com"
DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"
LOCAL_PROVIDER_HOSTS = {
    "localhost",
    "127.0.0.1",
    "::1",
    "ollama",
}
_OLLAMA_PULL_LOCK = Lock()


class ProviderError(ValueError):
    """Raised when provider input is invalid."""


class ProviderPullInProgress(ProviderError):
    """Raised when another Ollama model pull is already active."""


class ProviderDeleteBlocked(ProviderError):
    """Raised when a provider is still referenced by active queued/running work."""


@dataclass(frozen=True)
class ProviderSettingsInput:
    provider: str
    display_name: str | None = None
    endpoint_url: str | None = None
    preserve_endpoint_url: bool = False
    available_models: list[str] | None = None
    manual_models: list[str] | None = None
    llm_models: list[str] | None = None
    api_key: str | None = None
    remove_api_key: bool = False


@dataclass(frozen=True)
class ProviderConfiguration:
    id: UUID
    provider: str
    display_name: str
    endpoint_url: str | None
    available_models: list[str]
    manual_models: list[str]
    llm_models: list[str]
    api_key_set: bool
    updated_at: datetime


@dataclass(frozen=True)
class ProviderCheckResult:
    id: UUID
    provider: str
    ok: bool
    models: list[str]
    embedding_models: list[str]
    llm_models: list[str]
    message: str


def _provider(provider: str) -> str:
    cleaned = provider.strip().lower()
    if cleaned not in SUPPORTED_PROVIDERS:
        raise ProviderError("provider must be openai or ollama")
    return cleaned


def _safe_diagnostic_correlation_id(value: object) -> str:
    if value is None:
        return "unavailable"
    if not isinstance(value, UUID):
        raise ProviderError("LLM diagnostic correlation is invalid")
    return str(value)


def _clean_model(value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ProviderError("model must not be empty")
    if len(cleaned) > MAX_MODEL_LENGTH:
        raise ProviderError("model is too long")
    return cleaned


def _clean_display_name(value: str | None, *, fallback: str) -> str:
    cleaned = (value or fallback).strip()
    if not cleaned:
        raise ProviderError("display_name must not be empty")
    if len(cleaned) > 160:
        raise ProviderError("display_name is too long")
    return cleaned


def _clean_discovered_model(value: str) -> str | None:
    """Normalize an untrusted discovered model ID or explicitly reject it."""
    try:
        return _clean_model(value)
    except ProviderError:
        return None


def _split_env_models(value: str | None) -> list[str]:
    if value is None:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _clean_models(values: list[str] | None) -> list[str]:
    if values is None:
        return []
    cleaned: list[str] = []
    seen: set[str] = set()
    for value in values:
        model = _clean_model(value)
        if model not in seen:
            cleaned.append(model)
            seen.add(model)
    if len(cleaned) > MAX_MODELS:
        raise ProviderError("too many models configured")
    return cleaned


def _merge_models(*model_lists: list[str]) -> list[str]:
    merged: list[str] = []
    for models in model_lists:
        merged.extend(models)
    return _clean_models(merged)


def _is_openai_embedding_model(model: str) -> bool:
    return model.casefold().startswith("text-embedding-")


def _is_openai_llm_model(model: str) -> bool:
    cleaned = model.casefold()
    if cleaned == "o4-mini":
        return True
    if cleaned.startswith("gpt-4.1") or cleaned.startswith("gpt-4o"):
        return True
    match = re.match(r"^gpt-(\d+)(?:[.\-].*)?$", cleaned)
    return match is not None and int(match.group(1)) >= 5


def _purpose_models(provider: str, models: list[str]) -> tuple[list[str], list[str]]:
    if provider == "openai":
        return (
            [model for model in models if _is_openai_embedding_model(model)],
            [model for model in models if _is_openai_llm_model(model)],
        )
    return models, models


def _purpose_allow_lists(
    provider: str, embedding_models: list[str], llm_models: list[str]
) -> tuple[list[str], list[str]]:
    if provider != "openai":
        return embedding_models, llm_models
    return (
        [model for model in embedding_models if _is_openai_embedding_model(model)],
        [model for model in llm_models if _is_openai_llm_model(model)],
    )


def _provider_check_result(
    *,
    config: ProviderConfiguration,
    ok: bool,
    models: list[str],
    message: str,
) -> ProviderCheckResult:
    clean_models = _clean_models(models)
    embedding_models, llm_models = _purpose_models(config.provider, clean_models)
    return ProviderCheckResult(
        id=config.id,
        provider=config.provider,
        ok=ok,
        models=_merge_models(embedding_models, llm_models),
        embedding_models=embedding_models,
        llm_models=llm_models,
        message=message,
    )


def _clean_endpoint(endpoint_url: str | None) -> str | None:
    if endpoint_url is None:
        return None
    cleaned = endpoint_url.strip()
    if not cleaned:
        return None
    if len(cleaned) > MAX_ENDPOINT_LENGTH:
        raise ProviderError("endpoint_url is too long")
    parsed = urlparse(cleaned)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ProviderError("endpoint_url must be an http or https URL")
    return cleaned.rstrip("/") + "/"


def _require_local_endpoint(provider: str, endpoint_url: str) -> None:
    parsed = urlparse(endpoint_url)
    hostname = parsed.hostname.casefold() if parsed.hostname is not None else None
    if (
        hostname not in LOCAL_PROVIDER_HOSTS
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise ProviderError(f"{provider} requires an explicitly allowed local endpoint")


def _require_local_ollama_endpoint(endpoint_url: str) -> None:
    _require_local_endpoint("ollama", endpoint_url)


def _openai_compatible_path(base_path: str, resource: str) -> str:
    cleaned = base_path.rstrip("/")
    prefix = cleaned if cleaned.endswith("/v1") else f"{cleaned}/v1"
    return f"{prefix}/{resource}".removeprefix("//")


def _safe_embedding_http_error(status: int, raw: bytes) -> str:
    diagnostic = raw[:64_000].decode("utf-8", errors="ignore").casefold()
    context_markers = (
        "context length",
        "context window",
        "maximum context",
        "max context",
        "too many tokens",
        "input length exceeds",
    )
    if any(marker in diagnostic for marker in context_markers):
        return "embedding input exceeds the model context window"
    if status in {401, 403}:
        return "embedding provider rejected authentication"
    if status == 404:
        return "embedding model or endpoint was not found"
    if status == 429:
        return "embedding provider capacity is exhausted; retry later"
    if status >= 500:
        return "embedding provider is temporarily unavailable"
    return f"embedding provider rejected the request (HTTP {status})"


def _safe_llm_http_error(status: int, raw: bytes) -> str:
    diagnostic = raw[:64_000].decode("utf-8", errors="ignore").casefold()
    context_markers = (
        "context length",
        "context window",
        "maximum context",
        "max context",
        "too many tokens",
        "input length exceeds",
    )
    if any(marker in diagnostic for marker in context_markers):
        return "LLM input exceeds the model context window"
    if status in {401, 403}:
        return "LLM provider rejected authentication"
    if status == 404:
        return "LLM model or endpoint was not found"
    if status == 429:
        return "LLM provider capacity is exhausted; retry later"
    if status >= 500:
        return "LLM provider is temporarily unavailable"
    return f"LLM provider rejected the request (HTTP {status})"


def _configuration_from_row(row: dict[str, object]) -> ProviderConfiguration:
    provider = str(row["provider"])
    available_models = row.get("available_models", [])
    manual_models = row["manual_models"]
    llm_models = row.get("llm_models", [])
    embedding_allow_list = (
        list(manual_models) if isinstance(manual_models, list) else []
    )
    llm_allow_list = list(llm_models) if isinstance(llm_models, list) else []
    embedding_allow_list, llm_allow_list = _purpose_allow_lists(
        provider,
        embedding_allow_list,
        llm_allow_list,
    )
    available = list(available_models) if isinstance(available_models, list) else []
    if not available:
        available = _merge_models(embedding_allow_list, llm_allow_list)
    return ProviderConfiguration(
        id=UUID(str(row["id"])),
        provider=provider,
        display_name=str(row["display_name"]),
        endpoint_url=(
            str(row["endpoint_url"]) if row["endpoint_url"] is not None else None
        ),
        available_models=available,
        manual_models=embedding_allow_list,
        llm_models=llm_allow_list,
        api_key_set=row["api_key_secret"] is not None,
        updated_at=row["updated_at"],  # type: ignore[arg-type]
    )


class ProviderService:
    def __init__(self, settings: DatabaseSettings | None = None) -> None:
        self._settings = settings
        self._audit = AuditService()

    def list_configurations(self) -> list[ProviderConfiguration]:
        with open_database_connection(self._settings) as connection:
            rows = connection.execute(
                """
                SELECT id, provider, display_name, endpoint_url,
                       available_models,
                       embedding_models AS manual_models,
                       llm_models, api_key_secret, updated_at
                FROM provider_configurations
                WHERE provider IN ('openai', 'ollama')
                ORDER BY provider ASC, created_at ASC, id ASC
                """
            ).fetchall()
        return [_configuration_from_row(dict(row)) for row in rows]

    def list_llm_configurations(self) -> list[ProviderConfiguration]:
        with open_database_connection(self._settings) as connection:
            rows = connection.execute(
                """
                SELECT id, provider, display_name, endpoint_url,
                       available_models,
                       embedding_models AS manual_models,
                       llm_models, api_key_secret, updated_at
                FROM provider_configurations
                WHERE provider IN ('openai', 'ollama')
                  AND jsonb_array_length(llm_models) > 0
                ORDER BY provider ASC, created_at ASC, id ASC
                """
            ).fetchall()
        return [_configuration_from_row(dict(row)) for row in rows]

    def create_configuration(
        self, provider: str, *, actor_user_id: UUID
    ) -> ProviderConfiguration:
        clean_provider = _provider(provider)
        provider_id = uuid4()
        with open_database_connection(self._settings) as connection:
            with connection.transaction():
                display_name = self._next_display_name(connection, clean_provider)
                row = connection.execute(
                    """
                    INSERT INTO provider_configurations (
                        id, provider, display_name, endpoint_url, manual_models,
                        available_models, embedding_models, llm_models,
                        created_by_user_id, updated_by_user_id
                    )
                    VALUES (
                        %s, %s, %s, %s, '[]'::jsonb, '[]'::jsonb, '[]'::jsonb,
                        '[]'::jsonb, %s, %s
                    )
                    RETURNING id, provider, display_name, endpoint_url,
                              available_models, embedding_models AS manual_models,
                              llm_models, api_key_secret, updated_at
                    """,
                    (
                        provider_id,
                        clean_provider,
                        display_name,
                        DEFAULT_OLLAMA_BASE_URL + "/"
                        if clean_provider == "ollama"
                        else None,
                        actor_user_id,
                        actor_user_id,
                    ),
                ).fetchone()
                if row is None:
                    raise RuntimeError("provider configuration insert returned no row")
                self._audit.record_event(
                    connection,
                    actor_user_id=actor_user_id,
                    action="provider.create",
                    target_type="provider_configuration",
                    target_id=provider_id,
                    metadata={
                        "provider": clean_provider,
                        "display_name": display_name,
                    },
                )
        return _configuration_from_row(dict(row))

    def update_configuration(
        self,
        provider_id: UUID,
        payload: ProviderSettingsInput,
        *,
        actor_user_id: UUID,
    ) -> ProviderConfiguration:
        existing = self._get_configuration_by_id(provider_id)
        if existing is None:
            raise ProviderError("provider is not configured")
        provider = (
            existing.provider
            if not payload.provider.strip()
            else _provider(payload.provider)
        )
        if provider != existing.provider:
            raise ProviderError("provider type cannot be changed")
        endpoint_url = (
            existing.endpoint_url
            if payload.preserve_endpoint_url
            else _clean_endpoint(payload.endpoint_url)
        )
        if provider == "ollama" and endpoint_url is not None:
            _require_local_endpoint(provider, endpoint_url)
        requested_available_models = (
            _clean_models(payload.available_models)
            if payload.available_models is not None
            else existing.available_models
        )
        requested_manual_models = (
            _clean_models(payload.manual_models)
            if payload.manual_models is not None
            else existing.manual_models
        )
        requested_llm_models = (
            _clean_models(payload.llm_models)
            if payload.llm_models is not None
            else existing.llm_models
        )
        requested_manual_models, requested_llm_models = _purpose_allow_lists(
            provider,
            requested_manual_models,
            requested_llm_models,
        )
        clean_api_key = payload.api_key.strip() if payload.api_key is not None else None
        if clean_api_key == "":
            clean_api_key = None
        if provider == "ollama" and clean_api_key is not None:
            raise ProviderError("ollama does not accept an api_key")
        if payload.remove_api_key and clean_api_key is not None:
            raise ProviderError("api_key and remove_api_key cannot be used together")
        encrypted_api_key: str | None = None
        if clean_api_key is not None:
            try:
                encrypted_api_key = encrypt_provider_secret(clean_api_key)
            except ProviderSecretError as exc:
                raise ProviderError(str(exc)) from exc
        display_name = _clean_display_name(
            payload.display_name, fallback=existing.display_name
        )
        available_models = _merge_models(
            requested_available_models,
            requested_manual_models,
            requested_llm_models,
        )
        with open_database_connection(self._settings) as connection:
            with connection.transaction():
                row = connection.execute(
                    """
                    UPDATE provider_configurations
                    SET display_name = %s,
                        endpoint_url = %s,
                        api_key_secret = CASE
                            WHEN %s THEN NULL
                            WHEN %s::text IS NOT NULL THEN %s
                            ELSE api_key_secret
                        END,
                        manual_models = %s,
                        available_models = %s,
                        embedding_models = %s,
                        llm_models = %s,
                        updated_by_user_id = %s,
                        updated_at = now()
                    WHERE id = %s
                    RETURNING id, provider, display_name, endpoint_url,
                              available_models, embedding_models AS manual_models,
                              llm_models, api_key_secret, updated_at
                    """,
                    (
                        display_name,
                        endpoint_url,
                        payload.remove_api_key,
                        encrypted_api_key,
                        encrypted_api_key,
                        Jsonb(requested_manual_models),
                        Jsonb(available_models),
                        Jsonb(requested_manual_models),
                        Jsonb(requested_llm_models),
                        actor_user_id,
                        provider_id,
                    ),
                ).fetchone()
                if row is None:
                    raise ProviderError("provider is not configured")
                self._audit.record_event(
                    connection,
                    actor_user_id=actor_user_id,
                    action="provider.configure",
                    target_type="provider_configuration",
                    target_id=provider_id,
                    metadata={
                        "provider": provider,
                        "display_name": display_name,
                        "endpoint_set": endpoint_url is not None,
                        "available_model_count": len(available_models),
                        "manual_model_count": len(requested_manual_models),
                        "llm_model_count": len(requested_llm_models),
                        "api_key_set": clean_api_key is not None,
                        "api_key_removed": payload.remove_api_key,
                    },
                )
        return _configuration_from_row(dict(row))

    def delete_configuration(self, provider_id: UUID, *, actor_user_id: UUID) -> None:
        with open_database_connection(self._settings) as connection:
            with connection.transaction():
                active_reference = connection.execute(
                    """
                    SELECT id
                    FROM analysis_runs
                    WHERE provider_configuration_id = %s
                      AND deleted_at IS NULL
                      AND status IN ('queued', 'running', 'cancelling')
                    UNION ALL
                    SELECT id
                    FROM cluster_sets
                    WHERE llm_provider_configuration_id = %s
                      AND deleted_at IS NULL
                      AND status IN ('queued', 'running', 'cancelling')
                    LIMIT 1
                    """,
                    (provider_id, provider_id),
                ).fetchone()
                if active_reference is not None:
                    raise ProviderDeleteBlocked("provider is still used by active jobs")
                row = connection.execute(
                    """
                    DELETE FROM provider_configurations
                    WHERE id = %s
                    RETURNING id, provider, display_name
                    """,
                    (provider_id,),
                ).fetchone()
                if row is None:
                    raise ProviderError("provider is not configured")
                self._audit.record_event(
                    connection,
                    actor_user_id=actor_user_id,
                    action="provider.delete",
                    target_type="provider_configuration",
                    target_id=provider_id,
                    metadata={
                        "provider": str(row["provider"]),
                        "display_name": str(row["display_name"]),
                    },
                )

    def seed_ollama_provider_from_env(self) -> None:
        embedding_models = _clean_models(
            _split_env_models(os.environ.get("SKM_OLLAMA_MODELS"))
        )
        llm_models = _clean_models(
            _split_env_models(os.environ.get("SKM_OLLAMA_LLM_MODELS"))
        )
        available_models = _merge_models(embedding_models, llm_models)
        endpoint_url = _clean_endpoint(
            os.environ.get("SKM_OLLAMA_BASE_URL")
            or (DEFAULT_OLLAMA_BASE_URL if embedding_models or llm_models else None)
        )
        if endpoint_url is not None:
            _require_local_ollama_endpoint(endpoint_url)
        if endpoint_url is None and not embedding_models and not llm_models:
            return
        with open_database_connection(self._settings) as connection:
            with connection.transaction():
                connection.execute(
                    """
                    INSERT INTO provider_configurations (
                        id, provider, display_name, endpoint_url, manual_models,
                        available_models, embedding_models, llm_models
                    )
                    SELECT %s, 'ollama', %s, %s, %s, %s, %s, %s
                    WHERE NOT EXISTS (
                        SELECT 1
                        FROM provider_configurations
                        WHERE provider = 'ollama' AND endpoint_url = %s
                    )
                    """,
                    (
                        uuid4(),
                        self._next_display_name(connection, "ollama"),
                        endpoint_url,
                        Jsonb(embedding_models),
                        Jsonb(available_models),
                        Jsonb(embedding_models),
                        Jsonb(llm_models),
                        endpoint_url,
                    ),
                )

    def upsert_configuration(
        self,
        payload: ProviderSettingsInput,
        *,
        actor_user_id: UUID,
    ) -> ProviderConfiguration:
        provider = _provider(payload.provider)
        endpoint_url = _clean_endpoint(payload.endpoint_url)
        if provider == "ollama" and endpoint_url is not None:
            _require_local_endpoint(provider, endpoint_url)
        requested_available_models = (
            _clean_models(payload.available_models)
            if payload.available_models is not None
            else None
        )
        requested_manual_models = (
            _clean_models(payload.manual_models)
            if payload.manual_models is not None
            else None
        )
        requested_llm_models = (
            _clean_models(payload.llm_models)
            if payload.llm_models is not None
            else None
        )
        clean_api_key = payload.api_key.strip() if payload.api_key is not None else None
        if clean_api_key == "":
            clean_api_key = None
        if provider == "ollama" and clean_api_key is not None:
            raise ProviderError(f"{provider} does not accept an api_key")
        if payload.remove_api_key and clean_api_key is not None:
            raise ProviderError("api_key and remove_api_key cannot be used together")
        encrypted_api_key: str | None = None
        if clean_api_key is not None:
            try:
                encrypted_api_key = encrypt_provider_secret(clean_api_key)
            except ProviderSecretError as exc:
                raise ProviderError(str(exc)) from exc

        existing = self._get_configuration(provider)
        provider_id = existing.id if existing is not None else uuid4()
        display_name = _clean_display_name(
            payload.display_name,
            fallback=existing.display_name
            if existing is not None
            else provider.capitalize(),
        )
        manual_models = (
            requested_manual_models
            if requested_manual_models is not None
            else (existing.manual_models if existing is not None else [])
        )
        llm_models = (
            requested_llm_models
            if requested_llm_models is not None
            else (existing.llm_models if existing is not None else [])
        )
        manual_models, llm_models = _purpose_allow_lists(
            provider,
            manual_models,
            llm_models,
        )
        available_models = _merge_models(
            requested_available_models
            if requested_available_models is not None
            else (existing.available_models if existing is not None else []),
            manual_models,
            llm_models,
        )

        with open_database_connection(self._settings) as connection:
            with connection.transaction():
                row = connection.execute(
                    """
                    INSERT INTO provider_configurations (
                        id, provider, display_name, endpoint_url, api_key_secret,
                        manual_models, available_models, embedding_models,
                        llm_models, created_by_user_id, updated_by_user_id
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE
                    SET display_name = EXCLUDED.display_name,
                        endpoint_url = EXCLUDED.endpoint_url,
                        api_key_secret = CASE
                            WHEN %s THEN NULL
                            WHEN %s::text IS NOT NULL THEN %s
                            ELSE provider_configurations.api_key_secret
                        END,
                        manual_models = EXCLUDED.manual_models,
                        available_models = EXCLUDED.available_models,
                        embedding_models = EXCLUDED.embedding_models,
                        llm_models = EXCLUDED.llm_models,
                        updated_by_user_id = EXCLUDED.updated_by_user_id,
                        updated_at = now()
                    RETURNING id, provider, display_name, endpoint_url,
                              available_models, embedding_models AS manual_models,
                              llm_models, api_key_secret, updated_at
                    """,
                    (
                        provider_id,
                        provider,
                        display_name,
                        endpoint_url,
                        encrypted_api_key,
                        Jsonb(manual_models),
                        Jsonb(available_models),
                        Jsonb(manual_models),
                        Jsonb(llm_models),
                        actor_user_id,
                        actor_user_id,
                        payload.remove_api_key,
                        encrypted_api_key,
                        encrypted_api_key,
                    ),
                ).fetchone()
                if row is None:
                    raise RuntimeError("provider configuration upsert returned no row")
                self._audit.record_event(
                    connection,
                    actor_user_id=actor_user_id,
                    action="provider.configure",
                    target_type="provider_configuration",
                    target_id=provider_id,
                    metadata={
                        "provider": provider,
                        "display_name": display_name,
                        "endpoint_set": endpoint_url is not None,
                        "available_model_count": len(available_models),
                        "manual_model_count": len(manual_models),
                        "llm_model_count": len(llm_models),
                        "api_key_set": clean_api_key is not None,
                        "api_key_removed": payload.remove_api_key,
                    },
                )
        return _configuration_from_row(dict(row))

    def check_provider(self, provider_ref: UUID | str) -> ProviderCheckResult:
        config = self._get_configuration_by_ref(provider_ref)
        if config is None:
            raise ProviderError("provider is not configured")
        if config.provider == "openai":
            api_key_secret = self._get_api_key_secret(config.id)
            if api_key_secret is None:
                return _provider_check_result(
                    config=config,
                    ok=False,
                    models=config.available_models,
                    message="OpenAI API key is not configured",
                )
            try:
                api_key = decrypt_provider_secret(api_key_secret)
            except ProviderSecretError as exc:
                return _provider_check_result(
                    config=config,
                    ok=False,
                    models=config.available_models,
                    message=f"OpenAI model discovery failed: {exc}",
                )
            return self._check_openai(config, api_key)
        if config.endpoint_url is None:
            raise ProviderError("ollama endpoint_url is required")
        return self._check_ollama(config, config.endpoint_url)

    def pull_ollama_model(
        self, provider_ref: UUID | str, model: str, *, actor_user_id: UUID
    ) -> ProviderConfiguration:
        clean_model = _clean_model(model)
        config = self._get_configuration_by_ref(provider_ref)
        if config is None:
            raise ProviderError("ollama provider is not configured")
        if config.provider != "ollama":
            raise ProviderError("model pull is only available for ollama")
        if config.endpoint_url is None:
            raise ProviderError("ollama endpoint_url is required")
        if not _OLLAMA_PULL_LOCK.acquire(blocking=False):
            raise ProviderPullInProgress("ollama model pull already in progress")
        try:
            self._pull_ollama_model(config.endpoint_url, clean_model)
        finally:
            _OLLAMA_PULL_LOCK.release()
        available_models = _merge_models(config.available_models, [clean_model])
        return self.update_configuration(
            config.id,
            ProviderSettingsInput(
                provider="ollama",
                display_name=config.display_name,
                endpoint_url=config.endpoint_url,
                available_models=available_models,
                manual_models=config.manual_models,
                llm_models=config.llm_models,
            ),
            actor_user_id=actor_user_id,
        )

    def embed_texts(
        self, provider_ref: UUID | str, model: str, texts: list[str]
    ) -> list[list[float]]:
        """Generate exactly one validated embedding per input without fallback."""
        clean_model = _clean_model(model)
        if not texts or len(texts) > MAX_EMBEDDING_BATCH_SIZE:
            raise ProviderError(
                f"embedding batch must contain 1 to {MAX_EMBEDDING_BATCH_SIZE} texts"
            )
        if any(not isinstance(text, str) for text in texts):
            raise ProviderError("embedding input must contain strings")
        if any(len(text) > MAX_EMBEDDING_TEXT_LENGTH for text in texts):
            raise ProviderError("embedding input is too long")
        if sum(len(text) for text in texts) > MAX_EMBEDDING_BATCH_CHARACTERS:
            raise ProviderError("embedding batch is too large")

        config = self._get_configuration_by_ref(provider_ref)
        if config is None:
            raise ProviderError("provider is not configured for embeddings")
        if clean_model not in config.manual_models:
            raise ProviderError("model is not configured for provider")
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if config.provider == "openai":
            secret = self._get_api_key_secret(config.id)
            if secret is None:
                raise ProviderError("OpenAI API key is not configured")
            try:
                api_key = decrypt_provider_secret(secret)
            except ProviderSecretError as exc:
                raise ProviderError("OpenAI API key could not be loaded") from exc
            headers["Authorization"] = f"Bearer {api_key}"
            payload = self._post_embedding_request(
                scheme="https",
                netloc=OPENAI_API_HOST,
                path="/v1/embeddings",
                body={"model": clean_model, "input": texts},
                headers=headers,
            )
            embeddings = self._openai_compatible_embeddings(payload, len(texts))
        else:
            if config.endpoint_url is None:
                raise ProviderError("ollama endpoint_url is required")
            _require_local_endpoint(config.provider, config.endpoint_url)
            parsed = urlparse(config.endpoint_url)
            base_path = parsed.path.rstrip("/")
            path = f"{base_path}/api/embed" if base_path else "/api/embed"
            payload = self._post_embedding_request(
                scheme=parsed.scheme,
                netloc=parsed.netloc,
                path=path,
                body={
                    "model": clean_model,
                    "input": texts,
                    "keep_alive": "5m",
                },
                headers=headers,
            )
            embeddings = self._ollama_embeddings(payload, len(texts))
        return self._validate_embeddings(embeddings, len(texts))

    def ensure_text_generation_model(
        self, provider_ref: UUID | str, model: str
    ) -> ProviderConfiguration:
        clean_model = _clean_model(model)
        config = self._get_configuration_by_ref(provider_ref)
        if config is None:
            raise ProviderError("provider is not configured for LLM use")
        if clean_model not in config.llm_models:
            raise ProviderError("LLM model is not configured for provider")
        if config.provider == "openai" and self._get_api_key_secret(config.id) is None:
            raise ProviderError("OpenAI API key is not configured")
        if config.provider == "ollama":
            if config.endpoint_url is None:
                raise ProviderError("ollama endpoint_url is required")
            _require_local_ollama_endpoint(config.endpoint_url)
        return config

    def generate_text(
        self,
        provider_ref: UUID | str,
        model: str,
        prompt: str,
        *,
        instructions: str = LLM_SUMMARY_JSON_INSTRUCTIONS,
        response_schema: dict[str, object] | None = None,
        schema_name: str = "cluster_summary",
        max_output_tokens: int = LLM_SUMMARY_OUTPUT_TOKENS,
        max_prompt_characters: int = MAX_LLM_PROMPT_CHARACTERS,
        max_output_characters: int = MAX_LLM_OUTPUT_CHARACTERS,
        diagnostic_correlation_id: UUID | None = None,
    ) -> str:
        """Generate one bounded text response from an explicitly configured LLM."""
        _safe_diagnostic_correlation_id(diagnostic_correlation_id)
        clean_model = _clean_model(model)
        if not isinstance(prompt, str) or not prompt.strip():
            raise ProviderError("LLM prompt must not be empty")
        if (
            isinstance(max_prompt_characters, bool)
            or not isinstance(max_prompt_characters, int)
            or max_prompt_characters < 1
            or max_prompt_characters > HARD_MAX_LLM_PROMPT_CHARACTERS
        ):
            raise ProviderError("LLM prompt budget is invalid")
        if len(prompt) > max_prompt_characters:
            raise ProviderError("LLM prompt is too large")
        if (
            not isinstance(instructions, str)
            or not instructions.strip()
            or len(instructions) > 10_000
        ):
            raise ProviderError("LLM instructions are invalid")
        if not isinstance(schema_name, str) or not re.fullmatch(
            r"[a-z][a-z0-9_]{0,63}", schema_name
        ):
            raise ProviderError("LLM schema name is invalid")
        if (
            isinstance(max_output_tokens, bool)
            or not isinstance(max_output_tokens, int)
            or max_output_tokens < 1
            or max_output_tokens > MAX_LLM_OUTPUT_TOKENS
        ):
            raise ProviderError("LLM output token budget is invalid")
        if (
            isinstance(max_output_characters, bool)
            or not isinstance(max_output_characters, int)
            or max_output_characters < 1
            or max_output_characters > HARD_MAX_LLM_OUTPUT_CHARACTERS
        ):
            raise ProviderError("LLM output character budget is invalid")
        effective_schema = response_schema or LLM_SUMMARY_JSON_SCHEMA
        config = self.ensure_text_generation_model(provider_ref, clean_model)
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if config.provider == "openai":
            secret = self._get_api_key_secret(config.id)
            if secret is None:
                raise ProviderError("OpenAI API key is not configured")
            try:
                api_key = decrypt_provider_secret(secret)
            except ProviderSecretError as exc:
                raise ProviderError("OpenAI API key could not be loaded") from exc
            headers["Authorization"] = f"Bearer {api_key}"
            payload = self._post_llm_request(
                scheme="https",
                netloc=OPENAI_API_HOST,
                path="/v1/responses",
                body={
                    "model": clean_model,
                    "instructions": instructions,
                    "input": prompt,
                    "max_output_tokens": max_output_tokens,
                    "store": False,
                    "text": {
                        "format": {
                            "type": "json_schema",
                            "name": schema_name,
                            "strict": True,
                            "schema": effective_schema,
                        }
                    },
                },
                headers=headers,
            )
            text = self._openai_response_text(
                payload,
                diagnostic_correlation_id=diagnostic_correlation_id,
            )
        else:
            if config.endpoint_url is None:
                raise ProviderError("ollama endpoint_url is required")
            _require_local_ollama_endpoint(config.endpoint_url)
            parsed = urlparse(config.endpoint_url)
            base_path = parsed.path.rstrip("/")
            path = f"{base_path}/api/generate" if base_path else "/api/generate"
            payload = self._post_llm_request(
                scheme=parsed.scheme,
                netloc=parsed.netloc,
                path=path,
                body={
                    "model": clean_model,
                    "system": instructions,
                    "prompt": prompt,
                    "format": response_schema or "json",
                    "stream": False,
                    "keep_alive": "5m",
                    "options": {
                        "temperature": 0,
                        "num_predict": max_output_tokens,
                    },
                },
                headers=headers,
            )
            text = self._ollama_generation_text(payload)
        if len(text) > max_output_characters:
            raise ProviderError("LLM response is too large")
        return text

    def _get_configuration(self, provider: str) -> ProviderConfiguration | None:
        with open_database_connection(self._settings) as connection:
            row = connection.execute(
                """
                SELECT id, provider, display_name, endpoint_url,
                       available_models,
                       embedding_models AS manual_models,
                       llm_models, api_key_secret, updated_at
                FROM provider_configurations
                WHERE provider = %s
                ORDER BY created_at ASC, id ASC
                LIMIT 1
                """,
                (provider,),
            ).fetchone()
        return _configuration_from_row(dict(row)) if row is not None else None

    def _get_configuration_by_id(
        self, provider_id: UUID
    ) -> ProviderConfiguration | None:
        with open_database_connection(self._settings) as connection:
            row = connection.execute(
                """
                SELECT id, provider, display_name, endpoint_url,
                       available_models,
                       embedding_models AS manual_models,
                       llm_models, api_key_secret, updated_at
                FROM provider_configurations
                WHERE id = %s
                """,
                (provider_id,),
            ).fetchone()
        return _configuration_from_row(dict(row)) if row is not None else None

    def _get_configuration_by_ref(
        self, provider_ref: UUID | str
    ) -> ProviderConfiguration | None:
        if isinstance(provider_ref, UUID):
            return self._get_configuration_by_id(provider_ref)
        try:
            return self._get_configuration_by_id(UUID(str(provider_ref)))
        except ValueError:
            return self._get_configuration(_provider(str(provider_ref)))

    def _get_api_key_secret(self, provider_id: UUID) -> str | None:
        with open_database_connection(self._settings) as connection:
            row = connection.execute(
                """
                SELECT api_key_secret
                FROM provider_configurations
                WHERE id = %s
                """,
                (provider_id,),
            ).fetchone()
        if row is None or row["api_key_secret"] is None:
            return None
        return str(row["api_key_secret"])

    def _next_display_name(self, connection: Any, provider: str) -> str:
        base_name = "OpenAI" if provider == "openai" else "Ollama"
        rows = connection.execute(
            """
            SELECT display_name
            FROM provider_configurations
            WHERE provider = %s
            """,
            (provider,),
        ).fetchall()
        used = {
            str(row["display_name"]) for row in rows if row["display_name"] is not None
        }
        if base_name not in used:
            return base_name
        suffix = 2
        while f"{base_name} {suffix}" in used:
            suffix += 1
        return f"{base_name} {suffix}"

    def _check_ollama(
        self, config: ProviderConfiguration, endpoint_url: str
    ) -> ProviderCheckResult:
        _require_local_ollama_endpoint(endpoint_url)
        parsed = urlparse(endpoint_url)
        connection_class = (
            HTTPSConnection if parsed.scheme == "https" else HTTPConnection
        )
        base_path = parsed.path.rstrip("/")
        path = f"{base_path}/api/tags" if base_path else "/api/tags"
        connection = connection_class(
            parsed.netloc,
            timeout=PROVIDER_CHECK_TIMEOUT_SECONDS,
        )
        try:
            connection.request("GET", path, headers={"Accept": "application/json"})
            response = connection.getresponse()
            if response.status >= 300:
                raise ProviderError(f"Ollama returned HTTP {response.status}")
            payload = json.loads(response.read(1024 * 1024).decode("utf-8"))
        except (
            HTTPException,
            ProviderError,
            TimeoutError,
            OSError,
            json.JSONDecodeError,
        ) as exc:
            return _provider_check_result(
                config=config,
                ok=False,
                models=config.available_models,
                message=f"Ollama model discovery failed: {exc.__class__.__name__}",
            )
        finally:
            connection.close()
        discovered = self._models_from_ollama_tags_payload(payload)
        return _provider_check_result(
            config=config,
            ok=bool(discovered),
            models=discovered,
            message=(
                "Ollama models discovered"
                if discovered
                else "Ollama model discovery returned no model ids"
            ),
        )

    def _pull_ollama_model(self, endpoint_url: str, model: str) -> None:
        _require_local_ollama_endpoint(endpoint_url)
        parsed = urlparse(endpoint_url)
        connection_class = (
            HTTPSConnection if parsed.scheme == "https" else HTTPConnection
        )
        base_path = parsed.path.rstrip("/")
        path = f"{base_path}/api/pull" if base_path else "/api/pull"
        body = json.dumps({"model": model, "stream": False}).encode("utf-8")
        connection = connection_class(
            parsed.netloc,
            timeout=OLLAMA_PULL_TIMEOUT_SECONDS,
        )
        try:
            connection.request(
                "POST",
                path,
                body=body,
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
            )
            response = connection.getresponse()
            payload = json.loads(response.read(1024 * 1024).decode("utf-8"))
            if response.status >= 300:
                message = (
                    payload.get("error")
                    if isinstance(payload, dict)
                    and isinstance(payload.get("error"), str)
                    else f"Ollama returned HTTP {response.status}"
                )
                raise ProviderError(message)
            if not isinstance(payload, dict) or payload.get("status") != "success":
                raise ProviderError("Ollama model pull did not report success")
        except (
            HTTPException,
            TimeoutError,
            OSError,
            json.JSONDecodeError,
        ) as exc:
            raise ProviderError(
                f"Ollama model pull failed: {exc.__class__.__name__}"
            ) from exc
        finally:
            connection.close()

    def _check_openai(
        self, config: ProviderConfiguration, api_key: str
    ) -> ProviderCheckResult:
        connection = HTTPSConnection(
            OPENAI_API_HOST,
            timeout=PROVIDER_CHECK_TIMEOUT_SECONDS,
        )
        try:
            connection.request(
                "GET",
                "/v1/models",
                headers={
                    "Accept": "application/json",
                    "Authorization": f"Bearer {api_key}",
                },
            )
            response = connection.getresponse()
            if response.status >= 300:
                raise ProviderError(f"OpenAI returned HTTP {response.status}")
            payload = json.loads(response.read(2 * 1024 * 1024).decode("utf-8"))
        except (
            HTTPException,
            ProviderError,
            TimeoutError,
            OSError,
            json.JSONDecodeError,
        ) as exc:
            return _provider_check_result(
                config=config,
                ok=False,
                models=config.available_models,
                message=f"OpenAI model discovery failed: {exc.__class__.__name__}",
            )
        finally:
            connection.close()

        discovered = self._models_from_openai_compatible_payload(payload)
        if not discovered:
            return _provider_check_result(
                config=config,
                ok=False,
                models=[],
                message="OpenAI model discovery returned no model ids",
            )
        return _provider_check_result(
            config=config,
            ok=True,
            models=discovered,
            message="OpenAI models discovered",
        )

    def _post_embedding_request(
        self,
        *,
        scheme: str,
        netloc: str,
        path: str,
        body: dict[str, object],
        headers: dict[str, str],
    ) -> Any:
        connection_class = HTTPSConnection if scheme == "https" else HTTPConnection
        connection = connection_class(
            netloc, timeout=PROVIDER_EMBEDDING_TIMEOUT_SECONDS
        )
        try:
            connection.request(
                "POST",
                path,
                body=json.dumps(body).encode("utf-8"),
                headers=headers,
            )
            response = connection.getresponse()
            raw = response.read(MAX_EMBEDDING_RESPONSE_BYTES + 1)
            if len(raw) > MAX_EMBEDDING_RESPONSE_BYTES:
                raise ProviderError("embedding provider response is too large")
            if response.status >= 300:
                raise ProviderError(_safe_embedding_http_error(response.status, raw))
            return json.loads(raw.decode("utf-8"))
        except ProviderError:
            raise
        except (
            HTTPException,
            TimeoutError,
            OSError,
            UnicodeDecodeError,
            json.JSONDecodeError,
        ) as exc:
            raise ProviderError(
                f"embedding provider request failed: {exc.__class__.__name__}"
            ) from exc
        finally:
            connection.close()

    def _post_llm_request(
        self,
        *,
        scheme: str,
        netloc: str,
        path: str,
        body: dict[str, object],
        headers: dict[str, str],
    ) -> Any:
        connection_class = HTTPSConnection if scheme == "https" else HTTPConnection
        connection = connection_class(netloc, timeout=PROVIDER_LLM_TIMEOUT_SECONDS)
        try:
            connection.request(
                "POST",
                path,
                body=json.dumps(body).encode("utf-8"),
                headers=headers,
            )
            response = connection.getresponse()
            raw = response.read(MAX_LLM_RESPONSE_BYTES + 1)
            if len(raw) > MAX_LLM_RESPONSE_BYTES:
                raise ProviderError("LLM provider response is too large")
            if response.status >= 300:
                raise ProviderError(_safe_llm_http_error(response.status, raw))
            return json.loads(raw.decode("utf-8"))
        except ProviderError:
            raise
        except (
            HTTPException,
            TimeoutError,
            OSError,
            UnicodeDecodeError,
            json.JSONDecodeError,
        ) as exc:
            raise ProviderError(
                f"LLM provider request failed: {exc.__class__.__name__}"
            ) from exc
        finally:
            connection.close()

    def _openai_response_text(
        self,
        payload: Any,
        *,
        diagnostic_correlation_id: UUID | None = None,
    ) -> str:
        if not isinstance(payload, dict):
            raise ProviderError("LLM provider returned an invalid response")
        safe_correlation_id = _safe_diagnostic_correlation_id(diagnostic_correlation_id)
        if payload.get("status") == "incomplete":
            incomplete_details = payload.get("incomplete_details")
            raw_reason = (
                incomplete_details.get("reason")
                if isinstance(incomplete_details, dict)
                else None
            )
            safe_reason = (
                raw_reason.strip()
                if isinstance(raw_reason, str)
                and raw_reason.strip() in {"max_output_tokens", "content_filter"}
                else "unspecified"
            )
            output = payload.get("output")
            output_text = payload.get("output_text")
            LLM_DIAGNOSTIC_LOGGER.warning(
                "llm_provider_response_incomplete correlation_id=%s "
                "provider=openai reason=%s output_text_characters=%d "
                "output_items=%d",
                safe_correlation_id,
                safe_reason,
                len(output_text) if isinstance(output_text, str) else 0,
                len(output) if isinstance(output, list) else 0,
            )
            if safe_reason != "unspecified":
                raise ProviderError(
                    f"LLM provider returned an incomplete response ({safe_reason})"
                )
            raise ProviderError("LLM provider returned an incomplete response")
        output_text = payload.get("output_text")
        if isinstance(output_text, str) and output_text.strip():
            return output_text.strip()
        text_parts: list[str] = []
        output = payload.get("output")
        if isinstance(output, list):
            for item in output:
                if not isinstance(item, dict):
                    continue
                content = item.get("content")
                if not isinstance(content, list):
                    continue
                for content_item in content:
                    if not isinstance(content_item, dict):
                        continue
                    text = content_item.get("text")
                    if isinstance(text, str) and text.strip():
                        text_parts.append(text.strip())
        if text_parts:
            return "\n".join(text_parts)
        raise ProviderError("LLM provider returned an empty response")

    def _ollama_generation_text(self, payload: Any) -> str:
        if not isinstance(payload, dict):
            raise ProviderError("LLM provider returned an invalid response")
        content = payload.get("response")
        if not isinstance(content, str) or not content.strip():
            raise ProviderError("LLM provider returned an empty response")
        return content.strip()

    def _openai_compatible_embeddings(
        self, payload: Any, expected_count: int
    ) -> list[object]:
        if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
            raise ProviderError("embedding provider returned an invalid response")
        data = payload["data"]
        if len(data) != expected_count:
            raise ProviderError(
                "embedding provider returned the wrong number of vectors"
            )
        indexed: list[object | None] = [None] * expected_count
        for position, item in enumerate(data):
            if not isinstance(item, dict) or "embedding" not in item:
                raise ProviderError("embedding provider returned an invalid response")
            index = item.get("index", position)
            if (
                isinstance(index, bool)
                or not isinstance(index, int)
                or index < 0
                or index >= expected_count
                or indexed[index] is not None
            ):
                raise ProviderError(
                    "embedding provider returned invalid vector indices"
                )
            indexed[index] = item["embedding"]
        if any(item is None for item in indexed):
            raise ProviderError("embedding provider returned incomplete vector indices")
        return list(indexed)

    def _ollama_embeddings(self, payload: Any, expected_count: int) -> list[object]:
        if (
            not isinstance(payload, dict)
            or not isinstance(payload.get("embeddings"), list)
            or len(payload["embeddings"]) != expected_count
        ):
            raise ProviderError(
                "embedding provider returned the wrong number of vectors"
            )
        return list(payload["embeddings"])

    def _validate_embeddings(
        self, embeddings: list[object], expected_count: int
    ) -> list[list[float]]:
        if len(embeddings) != expected_count:
            raise ProviderError(
                "embedding provider returned the wrong number of vectors"
            )
        result: list[list[float]] = []
        dimensions: int | None = None
        for embedding in embeddings:
            if not isinstance(embedding, list) or not embedding:
                raise ProviderError("embedding provider returned an invalid vector")
            if len(embedding) > MAX_EMBEDDING_DIMENSIONS:
                raise ProviderError("embedding vector has too many dimensions")
            vector: list[float] = []
            for item in embedding:
                if isinstance(item, bool) or not isinstance(item, (int, float)):
                    raise ProviderError("embedding provider returned an invalid vector")
                number = float(item)
                if not math.isfinite(number):
                    raise ProviderError(
                        "embedding provider returned a non-finite vector"
                    )
                vector.append(number)
            if dimensions is None:
                dimensions = len(vector)
            elif len(vector) != dimensions:
                raise ProviderError(
                    "embedding provider returned inconsistent dimensions"
                )
            result.append(vector)
        return result

    def _models_from_openai_compatible_payload(self, payload: Any) -> list[str]:
        if isinstance(payload, list):
            return self._models_from_openai_model_items(payload)
        if not isinstance(payload, dict):
            return []
        data = payload.get("data", payload.get("models"))
        if not isinstance(data, list):
            return []
        return self._models_from_openai_model_items(data)

    def _models_from_openai_model_items(self, data: list[Any]) -> list[str]:
        models: list[str] = []
        for item in data:
            if isinstance(item, str):
                model_id = item
            elif isinstance(item, dict) and isinstance(item.get("id"), str):
                model_id = item["id"]
            elif isinstance(item, dict) and isinstance(item.get("model"), str):
                model_id = item["model"]
            else:
                continue
            model = _clean_discovered_model(model_id)
            if model is not None:
                models.append(model)
        return _clean_models(models)

    def _models_from_ollama_tags_payload(self, payload: Any) -> list[str]:
        if not isinstance(payload, dict):
            return []
        data = payload.get("models")
        if not isinstance(data, list):
            return []
        models: list[str] = []
        for item in data:
            if isinstance(item, dict) and isinstance(item.get("name"), str):
                model_id = item["name"]
            elif isinstance(item, dict) and isinstance(item.get("model"), str):
                model_id = item["model"]
            else:
                continue
            model = _clean_discovered_model(model_id)
            if model is not None:
                models.append(model)
        return _clean_models(models)
