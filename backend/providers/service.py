"""Provider configuration and analysis-profile persistence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from http.client import HTTPConnection, HTTPSConnection, HTTPException
import json
import math
import os
from typing import Any
from urllib.parse import urlparse
from uuid import UUID, uuid4

from psycopg.types.json import Jsonb

from backend.audit import AuditService
from backend.clusters.service import ClusterError, validate_algorithm_settings
from backend.config import DatabaseSettings
from backend.db.connection import open_database_connection
from backend.providers.secrets import (
    ProviderSecretError,
    decrypt_provider_secret,
    encrypt_provider_secret,
)

SUPPORTED_PROVIDERS = {"openai", "ollama", "vllm"}
MAX_MODELS = 200
MAX_MODEL_LENGTH = 160
MAX_ENDPOINT_LENGTH = 500
PROVIDER_CHECK_TIMEOUT_SECONDS = 2.0
PROVIDER_EMBEDDING_TIMEOUT_SECONDS = 60.0
MAX_EMBEDDING_BATCH_SIZE = 64
MAX_EMBEDDING_TEXT_LENGTH = 100_000
MAX_EMBEDDING_BATCH_CHARACTERS = 500_000
MAX_EMBEDDING_RESPONSE_BYTES = 16 * 1024 * 1024
MAX_EMBEDDING_DIMENSIONS = 8_192
OLLAMA_PULL_TIMEOUT_SECONDS = 1800.0
OPENAI_API_HOST = "api.openai.com"
DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"
LOCAL_PROVIDER_HOSTS = {
    "localhost",
    "127.0.0.1",
    "::1",
    "ollama",
    "vllm-cpu",
    "vllm-gpu",
}


class ProviderError(ValueError):
    """Raised when provider/profile input is invalid."""


@dataclass(frozen=True)
class ProviderSettingsInput:
    provider: str
    endpoint_url: str | None = None
    manual_models: list[str] | None = None
    api_key: str | None = None
    remove_api_key: bool = False


@dataclass(frozen=True)
class ProviderConfiguration:
    provider: str
    endpoint_url: str | None
    manual_models: list[str]
    api_key_set: bool
    updated_at: datetime


@dataclass(frozen=True)
class ProviderCheckResult:
    provider: str
    ok: bool
    models: list[str]
    message: str


@dataclass(frozen=True)
class AnalysisProfileInput:
    name: str
    provider: str
    model: str
    thresholds: dict[str, Any]
    algorithm_settings: dict[str, Any]
    prompt_template: str | None = None


@dataclass(frozen=True)
class AnalysisProfile:
    id: UUID
    project_id: UUID
    name: str
    provider: str
    model: str
    is_cloud_provider: bool
    thresholds: dict[str, Any]
    algorithm_settings: dict[str, Any]
    prompt_template: str | None
    created_at: datetime
    updated_at: datetime


def _provider(provider: str) -> str:
    cleaned = provider.strip().lower()
    if cleaned not in SUPPORTED_PROVIDERS:
        raise ProviderError("provider must be openai, ollama, or vllm")
    return cleaned


def _clean_model(value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ProviderError("model must not be empty")
    if len(cleaned) > MAX_MODEL_LENGTH:
        raise ProviderError("model is too long")
    return cleaned


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


def _object(value: dict[str, Any], field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ProviderError(f"{field} must be an object")
    return value


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


def _configuration_from_row(row: dict[str, object]) -> ProviderConfiguration:
    manual_models = row["manual_models"]
    return ProviderConfiguration(
        provider=str(row["provider"]),
        endpoint_url=(
            str(row["endpoint_url"]) if row["endpoint_url"] is not None else None
        ),
        manual_models=list(manual_models) if isinstance(manual_models, list) else [],
        api_key_set=row["api_key_secret"] is not None,
        updated_at=row["updated_at"],  # type: ignore[arg-type]
    )


def _profile_from_row(row: dict[str, object]) -> AnalysisProfile:
    thresholds = row["thresholds"]
    algorithm_settings = row["algorithm_settings"]
    return AnalysisProfile(
        id=UUID(str(row["id"])),
        project_id=UUID(str(row["project_id"])),
        name=str(row["name"]),
        provider=str(row["provider"]),
        model=str(row["model"]),
        is_cloud_provider=bool(row["is_cloud_provider"]),
        thresholds=dict(thresholds) if isinstance(thresholds, dict) else {},
        algorithm_settings=(
            dict(algorithm_settings) if isinstance(algorithm_settings, dict) else {}
        ),
        prompt_template=(
            str(row["prompt_template"]) if row["prompt_template"] is not None else None
        ),
        created_at=row["created_at"],  # type: ignore[arg-type]
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
                SELECT provider, endpoint_url, manual_models, api_key_secret, updated_at
                FROM provider_configurations
                ORDER BY provider ASC
                """
            ).fetchall()
        return [_configuration_from_row(dict(row)) for row in rows]

    def seed_ollama_provider_from_env(self) -> None:
        models = _clean_models(_split_env_models(os.environ.get("SKM_OLLAMA_MODELS")))
        endpoint_url = _clean_endpoint(
            os.environ.get("SKM_OLLAMA_BASE_URL")
            or (DEFAULT_OLLAMA_BASE_URL if models else None)
        )
        if endpoint_url is not None:
            _require_local_ollama_endpoint(endpoint_url)
        if endpoint_url is None and not models:
            return
        with open_database_connection(self._settings) as connection:
            with connection.transaction():
                connection.execute(
                    """
                    INSERT INTO provider_configurations (
                        provider, endpoint_url, manual_models
                    )
                    VALUES ('ollama', %s, %s)
                    ON CONFLICT (provider) DO NOTHING
                    """,
                    (endpoint_url, Jsonb(models)),
                )

    def upsert_configuration(
        self,
        payload: ProviderSettingsInput,
        *,
        actor_user_id: UUID,
    ) -> ProviderConfiguration:
        provider = _provider(payload.provider)
        endpoint_url = _clean_endpoint(payload.endpoint_url)
        if provider in {"ollama", "vllm"} and endpoint_url is not None:
            _require_local_endpoint(provider, endpoint_url)
        manual_models = _clean_models(payload.manual_models)
        clean_api_key = payload.api_key.strip() if payload.api_key is not None else None
        if clean_api_key == "":
            clean_api_key = None
        if provider in {"ollama", "vllm"} and clean_api_key is not None:
            raise ProviderError(f"{provider} does not accept an api_key")
        if payload.remove_api_key and clean_api_key is not None:
            raise ProviderError("api_key and remove_api_key cannot be used together")
        encrypted_api_key: str | None = None
        if clean_api_key is not None:
            try:
                encrypted_api_key = encrypt_provider_secret(clean_api_key)
            except ProviderSecretError as exc:
                raise ProviderError(str(exc)) from exc

        with open_database_connection(self._settings) as connection:
            with connection.transaction():
                row = connection.execute(
                    """
                    INSERT INTO provider_configurations (
                        provider, endpoint_url, api_key_secret, manual_models,
                        created_by_user_id, updated_by_user_id
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (provider) DO UPDATE
                    SET endpoint_url = EXCLUDED.endpoint_url,
                        api_key_secret = CASE
                            WHEN %s THEN NULL
                            WHEN %s::text IS NOT NULL THEN %s
                            ELSE provider_configurations.api_key_secret
                        END,
                        manual_models = EXCLUDED.manual_models,
                        updated_by_user_id = EXCLUDED.updated_by_user_id,
                        updated_at = now()
                    RETURNING provider, endpoint_url, manual_models,
                              api_key_secret, updated_at
                    """,
                    (
                        provider,
                        endpoint_url,
                        encrypted_api_key,
                        Jsonb(manual_models),
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
                    target_id=provider,
                    metadata={
                        "provider": provider,
                        "endpoint_set": endpoint_url is not None,
                        "manual_model_count": len(manual_models),
                        "api_key_set": clean_api_key is not None,
                        "api_key_removed": payload.remove_api_key,
                    },
                )
        return _configuration_from_row(dict(row))

    def check_provider(self, provider: str) -> ProviderCheckResult:
        clean_provider = _provider(provider)
        config = self._get_configuration(clean_provider)
        if config is None:
            raise ProviderError("provider is not configured")
        if clean_provider == "openai":
            api_key_secret = self._get_api_key_secret(clean_provider)
            if api_key_secret is None:
                return ProviderCheckResult(
                    provider=clean_provider,
                    ok=False,
                    models=config.manual_models,
                    message="OpenAI API key is not configured",
                )
            try:
                api_key = decrypt_provider_secret(api_key_secret)
            except ProviderSecretError as exc:
                return ProviderCheckResult(
                    provider=clean_provider,
                    ok=False,
                    models=config.manual_models,
                    message=f"OpenAI model discovery failed: {exc}",
                )
            return self._check_openai(api_key, config.manual_models)
        if config.endpoint_url is None:
            raise ProviderError(f"{clean_provider} endpoint_url is required")
        if clean_provider == "ollama":
            return self._check_ollama(config.endpoint_url, config.manual_models)
        return self._check_vllm(config.endpoint_url, config.manual_models)

    def pull_ollama_model(
        self, model: str, *, actor_user_id: UUID
    ) -> ProviderConfiguration:
        clean_model = _clean_model(model)
        config = self._get_configuration("ollama")
        if config is None:
            raise ProviderError("ollama provider is not configured")
        if config.endpoint_url is None:
            raise ProviderError("ollama endpoint_url is required")
        self._pull_ollama_model(config.endpoint_url, clean_model)
        manual_models = _clean_models([*config.manual_models, clean_model])
        return self.upsert_configuration(
            ProviderSettingsInput(
                provider="ollama",
                endpoint_url=config.endpoint_url,
                manual_models=manual_models,
            ),
            actor_user_id=actor_user_id,
        )

    def embed_texts(
        self, provider: str, model: str, texts: list[str]
    ) -> list[list[float]]:
        """Generate exactly one validated embedding per input without fallback."""
        clean_provider = _provider(provider)
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

        config = self._get_configuration(clean_provider)
        if config is None or clean_model not in config.manual_models:
            raise ProviderError("model is not configured for provider")
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if clean_provider == "openai":
            secret = self._get_api_key_secret(clean_provider)
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
                raise ProviderError(f"{clean_provider} endpoint_url is required")
            _require_local_endpoint(clean_provider, config.endpoint_url)
            parsed = urlparse(config.endpoint_url)
            base_path = parsed.path.rstrip("/")
            path = (
                f"{base_path}/api/embed"
                if clean_provider == "ollama"
                else _openai_compatible_path(parsed.path, "embeddings")
            )
            payload = self._post_embedding_request(
                scheme=parsed.scheme,
                netloc=parsed.netloc,
                path=path,
                body={
                    "model": clean_model,
                    "input": texts,
                    **({"keep_alive": "5m"} if clean_provider == "ollama" else {}),
                },
                headers=headers,
            )
            embeddings = (
                self._ollama_embeddings(payload, len(texts))
                if clean_provider == "ollama"
                else self._openai_compatible_embeddings(payload, len(texts))
            )
        return self._validate_embeddings(embeddings, len(texts))

    def list_profiles(self, project_id: UUID) -> list[AnalysisProfile]:
        with open_database_connection(self._settings) as connection:
            rows = connection.execute(
                """
                SELECT id, project_id, name, provider, model, is_cloud_provider,
                       thresholds, algorithm_settings, prompt_template,
                       created_at, updated_at
                FROM analysis_profiles
                WHERE project_id = %s
                ORDER BY updated_at DESC, name ASC
                """,
                (project_id,),
            ).fetchall()
        return [_profile_from_row(dict(row)) for row in rows]

    def create_profile(
        self,
        project_id: UUID,
        payload: AnalysisProfileInput,
        *,
        actor_user_id: UUID,
    ) -> AnalysisProfile:
        clean_payload = self._clean_profile_input(payload)
        profile_id = uuid4()
        with open_database_connection(self._settings) as connection:
            with connection.transaction():
                self._require_project(connection, project_id)
                self._require_configured_model(
                    connection, clean_payload.provider, clean_payload.model
                )
                row = connection.execute(
                    """
                    INSERT INTO analysis_profiles (
                        id, project_id, name, provider, model, is_cloud_provider,
                        thresholds, algorithm_settings, prompt_template,
                        created_by_user_id, updated_by_user_id
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id, project_id, name, provider, model,
                              is_cloud_provider, thresholds, algorithm_settings,
                              prompt_template, created_at, updated_at
                    """,
                    (
                        profile_id,
                        project_id,
                        clean_payload.name,
                        clean_payload.provider,
                        clean_payload.model,
                        _is_cloud_provider(clean_payload.provider),
                        Jsonb(clean_payload.thresholds),
                        Jsonb(clean_payload.algorithm_settings),
                        clean_payload.prompt_template,
                        actor_user_id,
                        actor_user_id,
                    ),
                ).fetchone()
                if row is None:
                    raise RuntimeError("analysis profile insert returned no row")
                self._audit.record_event(
                    connection,
                    actor_user_id=actor_user_id,
                    action="analysis_profile.create",
                    target_type="analysis_profile",
                    target_id=profile_id,
                    metadata={
                        "project_id": str(project_id),
                        "provider": clean_payload.provider,
                        "model": clean_payload.model,
                        "cloud": _is_cloud_provider(clean_payload.provider),
                    },
                )
        return _profile_from_row(dict(row))

    def update_profile(
        self,
        project_id: UUID,
        profile_id: UUID,
        payload: AnalysisProfileInput,
        *,
        actor_user_id: UUID,
    ) -> AnalysisProfile:
        clean_payload = self._clean_profile_input(payload)
        with open_database_connection(self._settings) as connection:
            with connection.transaction():
                self._require_configured_model(
                    connection, clean_payload.provider, clean_payload.model
                )
                row = connection.execute(
                    """
                    UPDATE analysis_profiles
                    SET name = %s,
                        provider = %s,
                        model = %s,
                        is_cloud_provider = %s,
                        thresholds = %s,
                        algorithm_settings = %s,
                        prompt_template = %s,
                        updated_by_user_id = %s,
                        updated_at = now()
                    WHERE id = %s AND project_id = %s
                    RETURNING id, project_id, name, provider, model,
                              is_cloud_provider, thresholds, algorithm_settings,
                              prompt_template, created_at, updated_at
                    """,
                    (
                        clean_payload.name,
                        clean_payload.provider,
                        clean_payload.model,
                        _is_cloud_provider(clean_payload.provider),
                        Jsonb(clean_payload.thresholds),
                        Jsonb(clean_payload.algorithm_settings),
                        clean_payload.prompt_template,
                        actor_user_id,
                        profile_id,
                        project_id,
                    ),
                ).fetchone()
                if row is None:
                    raise ProviderError("analysis profile not found")
                self._audit.record_event(
                    connection,
                    actor_user_id=actor_user_id,
                    action="analysis_profile.update",
                    target_type="analysis_profile",
                    target_id=profile_id,
                    metadata={
                        "project_id": str(project_id),
                        "provider": clean_payload.provider,
                        "model": clean_payload.model,
                        "cloud": _is_cloud_provider(clean_payload.provider),
                    },
                )
        return _profile_from_row(dict(row))

    def _get_configuration(self, provider: str) -> ProviderConfiguration | None:
        with open_database_connection(self._settings) as connection:
            row = connection.execute(
                """
                SELECT provider, endpoint_url, manual_models, api_key_secret, updated_at
                FROM provider_configurations
                WHERE provider = %s
                """,
                (provider,),
            ).fetchone()
        return _configuration_from_row(dict(row)) if row is not None else None

    def _get_api_key_secret(self, provider: str) -> str | None:
        with open_database_connection(self._settings) as connection:
            row = connection.execute(
                """
                SELECT api_key_secret
                FROM provider_configurations
                WHERE provider = %s
                """,
                (provider,),
            ).fetchone()
        if row is None or row["api_key_secret"] is None:
            return None
        return str(row["api_key_secret"])

    def _clean_profile_input(
        self, payload: AnalysisProfileInput
    ) -> AnalysisProfileInput:
        name = payload.name.strip()
        if not name:
            raise ProviderError("profile name must not be empty")
        algorithm_settings = _object(payload.algorithm_settings, "algorithm_settings")
        try:
            normalized_algorithm = validate_algorithm_settings(
                algorithm_settings
            ).as_settings()
        except ClusterError as exc:
            raise ProviderError(str(exc)) from exc
        return AnalysisProfileInput(
            name=name,
            provider=_provider(payload.provider),
            model=_clean_model(payload.model),
            thresholds=_object(payload.thresholds, "thresholds"),
            algorithm_settings=normalized_algorithm,
            prompt_template=(
                payload.prompt_template.strip()
                if payload.prompt_template is not None
                and payload.prompt_template.strip()
                else None
            ),
        )

    def _require_project(self, connection: Any, project_id: UUID) -> None:
        row = connection.execute(
            "SELECT id FROM projects WHERE id = %s AND deleted_at IS NULL",
            (project_id,),
        ).fetchone()
        if row is None:
            raise ProviderError("project not found")

    def _require_configured_model(
        self, connection: Any, provider: str, model: str
    ) -> None:
        row = connection.execute(
            """
            SELECT manual_models, api_key_secret, endpoint_url
            FROM provider_configurations
            WHERE provider = %s
            """,
            (provider,),
        ).fetchone()
        if row is None:
            raise ProviderError("provider is not configured")
        models = row["manual_models"]
        manual_models = list(models) if isinstance(models, list) else []
        if model not in manual_models:
            raise ProviderError("model is not configured for provider")
        if provider == "openai" and row["api_key_secret"] is None:
            raise ProviderError("OpenAI API key is not configured")
        if provider in {"ollama", "vllm"} and row["endpoint_url"] is None:
            raise ProviderError(f"{provider} endpoint_url is required")

    def _check_ollama(
        self, endpoint_url: str, manual_models: list[str]
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
            return ProviderCheckResult(
                provider="ollama",
                ok=False,
                models=manual_models,
                message=f"Ollama model discovery failed: {exc.__class__.__name__}",
            )
        finally:
            connection.close()
        discovered = self._models_from_ollama_tags_payload(payload)
        return ProviderCheckResult(
            provider="ollama",
            ok=bool(discovered or manual_models),
            models=discovered or manual_models,
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

    def _check_vllm(
        self, endpoint_url: str, manual_models: list[str]
    ) -> ProviderCheckResult:
        _require_local_endpoint("vllm", endpoint_url)
        parsed = urlparse(endpoint_url)
        connection_class = (
            HTTPSConnection if parsed.scheme == "https" else HTTPConnection
        )
        path = _openai_compatible_path(parsed.path, "models")
        connection = connection_class(
            parsed.netloc,
            timeout=PROVIDER_CHECK_TIMEOUT_SECONDS,
        )
        try:
            connection.request("GET", path, headers={"Accept": "application/json"})
            response = connection.getresponse()
            if response.status >= 300:
                raise ProviderError(f"vLLM returned HTTP {response.status}")
            payload = json.loads(response.read(1024 * 1024).decode("utf-8"))
        except (
            HTTPException,
            ProviderError,
            TimeoutError,
            OSError,
            json.JSONDecodeError,
        ) as exc:
            return ProviderCheckResult(
                provider="vllm",
                ok=False,
                models=manual_models,
                message=f"vLLM model discovery failed: {exc.__class__.__name__}",
            )
        finally:
            connection.close()
        discovered = self._models_from_openai_compatible_payload(payload)
        return ProviderCheckResult(
            provider="vllm",
            ok=True,
            models=discovered or manual_models,
            message="vLLM endpoint reachable",
        )

    def _check_openai(
        self, api_key: str, manual_models: list[str]
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
            return ProviderCheckResult(
                provider="openai",
                ok=False,
                models=manual_models,
                message=f"OpenAI model discovery failed: {exc.__class__.__name__}",
            )
        finally:
            connection.close()

        discovered = self._models_from_openai_compatible_payload(payload)
        if not discovered:
            return ProviderCheckResult(
                provider="openai",
                ok=False,
                models=manual_models,
                message="OpenAI model discovery returned no model ids",
            )
        embedding_models = [
            model for model in discovered if "embedding" in model.lower()
        ]
        if embedding_models:
            return ProviderCheckResult(
                provider="openai",
                ok=True,
                models=embedding_models,
                message="OpenAI embedding models discovered",
            )
        models = discovered or manual_models
        return ProviderCheckResult(
            provider="openai",
            ok=bool(models),
            models=models,
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
            try:
                models.append(_clean_model(model_id))
            except ProviderError:
                continue
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
            try:
                models.append(_clean_model(model_id))
            except ProviderError:
                continue
        return _clean_models(models)


def _is_cloud_provider(provider: str) -> bool:
    return provider == "openai"
