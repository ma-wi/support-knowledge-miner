"""FastAPI boundary for local authentication and user management."""

from __future__ import annotations

import asyncio
import os
import tempfile
import threading
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from datetime import datetime
from email.message import Message
from pathlib import Path
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.exception_handlers import (
    request_validation_exception_handler as default_request_validation_exception_handler,
)
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field, StrictInt
from starlette.concurrency import run_in_threadpool
from starlette.requests import ClientDisconnect

from backend.analysis import (
    AnalysisError,
    AnalysisQueueFull,
    AnalysisService,
    EmbeddingRecord,
    IndexingRun,
    IndexingRunInput,
)
from backend.auth import AuthService, CurrentUser
from backend.auth.service import AuthenticationError
from backend.clusters import (
    Cluster,
    ClusterError,
    ClusterManualUpdate,
    ClusterSet,
    ClusterSetEvent,
    ClusterSetInput,
    ClusterSetQueueFull,
    ClusterSetSummaryInput,
    ClusterService,
    ClusterSource,
    ClusterSourcePage,
)
from backend.clusters.service import DEFAULT_CLUSTER_SOURCE_PAGE_SIZE
from backend.config import DatabaseSettings
from backend.exports import (
    ExplorerExportInput,
    ExportError,
    ExportLog,
    ExportResult,
    ExportService,
)
from backend.imports import (
    ImportError,
    ImportLog,
    ImportLogEntry,
    ImportResult,
    ImportService,
)
from backend.imports.service import MAX_IMPORT_BYTES
from backend.providers import (
    ProviderCheckResult,
    ProviderConfiguration,
    ProviderDeleteBlocked,
    ProviderError,
    ProviderPullInProgress,
    ProviderService,
    ProviderSettingsInput,
)
from backend.projects import ProjectError, ProjectService, PublicProject
from backend.users import CreateUserInput, UpdateUserInput, UserService
from backend.users.service import PublicUser, UserError

_bearer = HTTPBearer(auto_error=False)
MAX_CONCURRENT_IMPORTS = 2
IMPORT_CHUNK_IDLE_TIMEOUT_SECONDS = 30.0
IMPORT_TOTAL_TIMEOUT_SECONDS = 30.0 * 60.0


class ImportCapacity:
    """Process-local capacity guard for upload and import work."""

    def __init__(self, limit: int = MAX_CONCURRENT_IMPORTS) -> None:
        if limit < 1:
            raise ValueError("import capacity limit must be positive")
        self._limit = limit
        self._active = 0
        self._lock = threading.Lock()

    def try_acquire(self) -> bool:
        with self._lock:
            if self._active >= self._limit:
                return False
            self._active += 1
            return True

    def release(self) -> None:
        with self._lock:
            if self._active < 1:
                raise RuntimeError("import capacity released without active import")
            self._active -= 1


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    first_name: str
    last_name: str
    email: str
    created_at: datetime
    updated_at: datetime


class SignInRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=1)
    password: str = Field(min_length=1)


class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_at: datetime
    user: UserResponse


class CreateUserRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    first_name: str = Field(min_length=1)
    last_name: str = Field(min_length=1)
    email: str = Field(min_length=1)
    password: str = Field(min_length=1)


class UpdateUserRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    first_name: str | None = Field(default=None, min_length=1)
    last_name: str | None = Field(default=None, min_length=1)
    email: str | None = Field(default=None, min_length=1)


class SetPasswordRequest(BaseModel):
    password: str = Field(min_length=1)


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    lifecycle_state: str
    created_at: datetime
    updated_at: datetime


class CreateProjectRequest(BaseModel):
    name: str = Field(min_length=1)


class RenameProjectRequest(BaseModel):
    name: str = Field(min_length=1)


class DeleteProjectRequest(BaseModel):
    confirmation_name: str = Field(min_length=1)


class ImportLogEntryResponse(BaseModel):
    source_location: str
    reason: str
    context: dict[str, object]


class ImportLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    source_type: str
    source_name: str
    status: str
    failure_reason: str | None
    total_records: int
    valid_records: int
    skipped_records: int
    skipped_detail_count: int
    dataset_version_id: UUID | None
    dataset_display_name: str | None
    dataset_deleted_at: datetime | None
    started_at: datetime
    completed_at: datetime


class DatasetVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    version_number: int
    import_log_id: UUID
    record_count: int
    source_type: str
    source_name: str
    display_name: str
    deleted_at: datetime | None
    created_at: datetime


class RenameDatasetVersionRequest(BaseModel):
    display_name: str = Field(min_length=1)


class ImportResultResponse(BaseModel):
    log: ImportLogResponse
    dataset_version: DatasetVersionResponse | None
    skipped_entries: list[ImportLogEntryResponse]
    skipped_entries_truncated: bool


class ProviderSettingsRequest(BaseModel):
    provider: str | None = None
    display_name: str | None = None
    endpoint_url: str | None = None
    available_models: list[str] | None = None
    manual_models: list[str] | None = None
    llm_models: list[str] | None = None
    api_key: str | None = None
    remove_api_key: bool = False


class ProviderCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str = Field(min_length=1)


class LlmProviderSettingsRequest(BaseModel):
    endpoint_url: str | None = None
    llm_models: list[str] = Field(default_factory=list)
    api_key: str | None = None
    remove_api_key: bool = False


class ProviderConfigurationResponse(BaseModel):
    id: UUID
    provider: str
    display_name: str
    endpoint_url: str | None
    available_models: list[str]
    manual_models: list[str]
    llm_models: list[str]
    api_key_set: bool
    updated_at: datetime


class ProviderCheckResponse(BaseModel):
    id: UUID
    provider: str
    ok: bool
    models: list[str]
    embedding_models: list[str]
    llm_models: list[str]
    message: str


class OllamaPullRequest(BaseModel):
    model: str = Field(min_length=1)


class IndexingRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dataset_version_id: UUID
    provider_id: UUID | None = None
    provider: str | None = Field(default=None, min_length=1)
    model: str = Field(min_length=1)
    parameters: dict[str, object] | None = None
    cloud_use_confirmed: bool = False


class IndexingRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    dataset_version_id: UUID
    dataset_display_name: str | None
    dataset_deleted_at: datetime | None
    status: str
    progress: int
    phase: str
    provider: str
    provider_configuration_id: UUID | None
    provider_display_name: str | None
    model: str
    parameters: dict[str, object]
    error_code: str | None
    error_message: str | None
    diagnostics: dict[str, object]
    started_at: datetime | None
    completed_at: datetime | None
    cancel_requested_at: datetime | None
    deleted_at: datetime | None
    created_at: datetime
    updated_at: datetime


class EmbeddingRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    indexing_run_id: UUID
    dataset_version_id: UUID
    source_object_type: str
    source_object_id: UUID
    text_variant: str
    model: str
    dimensions: int
    metadata: dict[str, object]
    created_at: datetime


class ClusterSetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    indexing_run_id: UUID
    display_name: str | None = Field(default=None, min_length=1)
    parent_cluster_set_id: UUID | None = None
    derivation_type: str = "root"
    vector_basis: str = "message"
    message_weight: float = 0.5
    answer_weight: float = 0.5
    algorithm_settings: dict[str, object] = Field(
        default_factory=lambda: {"algorithm": "hdbscan", "min_cluster_size": 2}
    )
    source_cluster_ids: list[UUID] = Field(default_factory=list)
    source_pair_ids: list[UUID] = Field(default_factory=list)
    outlier_threshold: float | None = None
    llm_provider_id: UUID | None = None
    llm_provider: str | None = None
    llm_model: str | None = None
    llm_sample_count: StrictInt | None = 10
    llm_sample_all: bool = False
    llm_cloud_use_confirmed: bool = False


class ClusterSetRenameRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: str = Field(min_length=1)


class ClusterSetSummaryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    llm_provider_id: UUID | None = None
    llm_provider: str | None = None
    llm_model: str | None = None
    llm_sample_count: StrictInt | None = 10
    llm_sample_all: bool = False
    llm_cloud_use_confirmed: bool = False


class ClusterSetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    indexing_run_id: UUID
    dataset_version_id: UUID
    dataset_display_name: str | None
    indexing_deleted_at: datetime | None
    parent_cluster_set_id: UUID | None
    display_name: str
    status: str
    progress: int
    phase: str
    derivation_type: str
    vector_basis: str
    message_weight: float
    answer_weight: float
    algorithm: str
    parameters: dict[str, object]
    source_snapshot: dict[str, object]
    llm_provider: str | None
    llm_provider_configuration_id: UUID | None
    llm_provider_display_name: str | None
    llm_model: str | None
    llm_parameters: dict[str, object]
    llm_sample_strategy: dict[str, object]
    error_code: str | None
    error_message: str | None
    diagnostics: dict[str, object]
    started_at: datetime | None
    completed_at: datetime | None
    cancel_requested_at: datetime | None
    deleted_at: datetime | None
    created_at: datetime
    updated_at: datetime
    cluster_count: int


class ClusterSetEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    cluster_set_id: UUID
    event_type: str
    metadata: dict[str, object]
    created_at: datetime


class ActiveJobsResponse(BaseModel):
    indexing_active: bool
    cluster_set_active: bool


class ClusterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    analysis_run_id: UUID
    dataset_version_id: UUID
    cluster_set_id: UUID | None = None
    auto_title: str
    manual_title: str | None
    effective_title: str
    auto_category: str | None
    manual_category: str | None
    effective_category: str | None
    auto_status: str
    manual_status: str | None
    effective_status: str
    score: float
    is_outlier: bool
    algorithm: str
    member_count: int
    metadata: dict[str, object]
    created_at: datetime
    updated_at: datetime
    auto_summary_question: str | None = None
    auto_summary_answer: str | None = None


class ClusterUpdateRequest(BaseModel):
    manual_title: str | None = None
    manual_category: str | None = None
    manual_status: str | None = None


class ClusterSourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    cluster_id: UUID
    message_pair_id: UUID
    ticket_id: str
    message_group_id: str
    message: str
    answer: str
    membership_score: float
    is_outlier: bool
    assignment_type: str


class ClusterSourcePageResponse(BaseModel):
    sources: list[ClusterSourceResponse]
    limit: int
    offset: int
    next_offset: int | None
    has_more: bool


class ExplorerExportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cluster_set_id: UUID
    export_format: str = "csv"
    search_query: str | None = None
    category: str | None = None
    include_excluded: bool = False
    include_outliers: bool = True
    cluster_ids: list[UUID] = Field(default_factory=list)


class ExportLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    export_type: str
    include_original_text: bool
    filters: dict[str, object]
    selection: dict[str, object]
    dataset_version_id: UUID | None
    analysis_run_id: UUID | None
    cluster_set_id: UUID | None
    output_filename: str
    output_path: str | None
    row_count: int
    created_at: datetime


class ExportResultResponse(BaseModel):
    export: ExportLogResponse
    content: str
    content_type: str
    warning: str | None


def _user_response(user: PublicUser) -> UserResponse:
    return UserResponse.model_validate(user)


def _project_response(project: PublicProject) -> ProjectResponse:
    return ProjectResponse.model_validate(project)


def _import_log_response(log: ImportLog) -> ImportLogResponse:
    return ImportLogResponse.model_validate(log)


def _import_entry_response(entry: ImportLogEntry) -> ImportLogEntryResponse:
    return ImportLogEntryResponse(
        source_location=entry.source_location,
        reason=entry.reason,
        context=entry.context,
    )


def _import_result_response(result: ImportResult) -> ImportResultResponse:
    return ImportResultResponse(
        log=_import_log_response(result.log),
        dataset_version=(
            DatasetVersionResponse.model_validate(result.dataset_version)
            if result.dataset_version is not None
            else None
        ),
        skipped_entries=[
            _import_entry_response(entry) for entry in result.skipped_entries
        ],
        skipped_entries_truncated=result.skipped_entries_truncated,
    )


def _import_metadata(request: Request) -> tuple[str, str]:
    media_type = request.headers.get("content-type", "").split(";", 1)[0].lower()
    source_type_by_media = {
        "text/csv": "csv",
        "application/json": "json",
    }
    source_type = source_type_by_media.get(media_type)
    if source_type is None:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                "Nicht unterstützter Dateityp. Erlaubt sind CSV "
                "(text/csv) und JSON (application/json)."
            ),
        )

    content_disposition = request.headers.get("content-disposition", "")
    disposition = Message()
    disposition["content-disposition"] = content_disposition
    source_name = disposition.get_filename()
    if (
        "filename*=" not in content_disposition.casefold()
        or source_name is None
        or not source_name.strip()
        or len(source_name) > 255
        or any(character in source_name for character in ("/", "\\"))
        or any(ord(character) < 32 for character in source_name)
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Dateiname fehlt oder ist ungültig. "
                "Content-Disposition mit RFC-5987-Dateiname verwenden."
            ),
        )
    source_name = source_name.strip()
    expected_extension = f".{source_type}"
    if not source_name.lower().endswith(expected_extension):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                f"Dateiendung und Medientyp passen nicht zusammen: "
                f"{expected_extension} erwartet."
            ),
        )
    return source_type, source_name


async def _spool_import_body(request: Request) -> Path:
    content_length = request.headers.get("content-length")
    if content_length is not None:
        try:
            declared_bytes = int(content_length)
        except ValueError:
            declared_bytes = -1
        if declared_bytes < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Content-Length ist ungültig.",
            )
        if declared_bytes > MAX_IMPORT_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail=(
                    f"Datei ist zu groß ({declared_bytes} Byte). "
                    "Maximal erlaubt sind 536870912 Byte (512 MiB)."
                ),
            )

    descriptor, raw_path = tempfile.mkstemp(prefix="skm-import-", suffix=".upload")
    source_path = Path(raw_path)
    received_bytes = 0
    try:
        with os.fdopen(descriptor, "wb") as destination:
            chunks = request.stream().__aiter__()
            event_loop = asyncio.get_running_loop()
            idle_deadline = event_loop.time() + IMPORT_CHUNK_IDLE_TIMEOUT_SECONDS
            total_deadline = event_loop.time() + IMPORT_TOTAL_TIMEOUT_SECONDS
            while True:
                try:
                    chunk = await asyncio.wait_for(
                        anext(chunks),
                        timeout=max(
                            0,
                            min(idle_deadline, total_deadline) - event_loop.time(),
                        ),
                    )
                except StopAsyncIteration:
                    break
                except TimeoutError as exc:
                    total_time_exceeded = event_loop.time() >= total_deadline
                    raise HTTPException(
                        status_code=status.HTTP_408_REQUEST_TIMEOUT,
                        detail=(
                            "Maximale Uploaddauer von 30 Minuten wurde überschritten."
                            if total_time_exceeded
                            else (
                                "Upload hat zu lange keine Daten geliefert "
                                "und wurde abgebrochen."
                            )
                        ),
                    ) from exc
                if not chunk:
                    continue
                idle_deadline = event_loop.time() + IMPORT_CHUNK_IDLE_TIMEOUT_SECONDS
                received_bytes += len(chunk)
                if received_bytes > MAX_IMPORT_BYTES:
                    raise HTTPException(
                        status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                        detail=(
                            f"Datei ist zu groß ({received_bytes} Byte). "
                            "Maximal erlaubt sind "
                            "536870912 Byte (512 MiB)."
                        ),
                    )
                destination.write(chunk)
        if received_bytes == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Importdatei ist leer.",
            )
        return source_path
    except BaseException:
        source_path.unlink(missing_ok=True)
        raise


def _provider_response(
    configuration: ProviderConfiguration,
) -> ProviderConfigurationResponse:
    return ProviderConfigurationResponse(
        id=configuration.id,
        provider=configuration.provider,
        display_name=configuration.display_name,
        endpoint_url=configuration.endpoint_url,
        available_models=configuration.available_models,
        manual_models=configuration.manual_models,
        llm_models=configuration.llm_models,
        api_key_set=configuration.api_key_set,
        updated_at=configuration.updated_at,
    )


def _provider_check_response(result: ProviderCheckResult) -> ProviderCheckResponse:
    return ProviderCheckResponse(
        id=result.id,
        provider=result.provider,
        ok=result.ok,
        models=result.models,
        embedding_models=result.embedding_models,
        llm_models=result.llm_models,
        message=result.message,
    )


def _provider_problem_response(
    *,
    code: str,
    status_code: int,
    retryable: bool,
    suggested_action: str,
    field_errors: dict[str, str] | None = None,
) -> JSONResponse:
    contracts = {
        "PROVIDER_MODEL_PULL_IN_PROGRESS": {
            "title": "Ein Modell-Download läuft bereits.",
            "detail": "Ein Ollama-Modell wird bereits geladen.",
        },
        "PROVIDER_DELETE_FAILED": {
            "title": "Provider konnte nicht entfernt werden.",
            "detail": "Der Provider konnte nicht aus der aktiven Konfiguration entfernt werden.",
        },
        "PROVIDER_DELETE_BLOCKED": {
            "title": "Provider wird noch verwendet.",
            "detail": "Der Provider kann erst entfernt werden, wenn aktive Jobs abgeschlossen oder abgebrochen sind.",
        },
        "VALIDATION_FAILED": {
            "title": "Provider-Eingaben sind ungültig.",
            "detail": "Die Provider-Konfiguration konnte mit diesen Eingaben nicht gespeichert werden.",
        },
    }
    contract = contracts.get(
        code,
        {
            "title": "Die Provider-Aktion konnte nicht abgeschlossen werden.",
            "detail": "Die Provider-Aktion ist unerwartet fehlgeschlagen.",
        },
    )
    return JSONResponse(
        status_code=status_code,
        content={
            "type": f"urn:skm:error:{code}",
            "title": contract["title"],
            "status": status_code,
            "detail": contract["detail"],
            "code": code,
            "correlationId": None,
            "retryable": retryable,
            "suggestedAction": suggested_action,
            "fieldErrors": [
                {"field": field, "message": message}
                for field, message in (field_errors or {}).items()
            ],
        },
    )


def _indexing_run_response(run: IndexingRun) -> IndexingRunResponse:
    return IndexingRunResponse.model_validate(run)


def _embedding_response(record: EmbeddingRecord) -> EmbeddingRecordResponse:
    return EmbeddingRecordResponse.model_validate(record)


def _cluster_response(cluster: Cluster) -> ClusterResponse:
    return ClusterResponse.model_validate(cluster)


def _cluster_set_response(cluster_set: ClusterSet) -> ClusterSetResponse:
    return ClusterSetResponse.model_validate(cluster_set)


def _cluster_set_event_response(event: ClusterSetEvent) -> ClusterSetEventResponse:
    return ClusterSetEventResponse.model_validate(event)


def _cluster_source_response(source: ClusterSource) -> ClusterSourceResponse:
    return ClusterSourceResponse.model_validate(source)


def _cluster_source_page_response(page: ClusterSourcePage) -> ClusterSourcePageResponse:
    return ClusterSourcePageResponse(
        sources=[_cluster_source_response(source) for source in page.sources],
        limit=page.limit,
        offset=page.offset,
        next_offset=page.next_offset,
        has_more=page.has_more,
    )


def _export_log_response(log: ExportLog) -> ExportLogResponse:
    return ExportLogResponse.model_validate(log)


def _export_result_response(result: ExportResult) -> ExportResultResponse:
    return ExportResultResponse(
        export=_export_log_response(result.log),
        content=result.content,
        content_type=result.content_type,
        warning=result.warning,
    )


def _analysis_problem_contract(code: str) -> dict[str, str]:
    return {
        "UNEXPECTED_ERROR": {
            "title": "Die Aktion konnte nicht abgeschlossen werden.",
            "detail": (
                "Ein unerwarteter Fehler ist aufgetreten; die Eingaben bleiben "
                "soweit sicher erhalten."
            ),
            "suggested_action": "retry",
        },
        "INDEXING_MODEL_UNAVAILABLE": {
            "title": "Die Indizierung wurde nicht gestartet.",
            "detail": "Das gewählte Embedding-Modell ist nicht verfügbar.",
            "suggested_action": (
                "Provider-Einstellungen prüfen oder ein anderes Modell wählen."
            ),
        },
        "INDEXING_CLOUD_CONFIRMATION_REQUIRED": {
            "title": "Cloud-Nutzung muss bestätigt werden.",
            "detail": "Diese Indizierung würde Originaltexte an OpenAI senden.",
            "suggested_action": (
                "Cloud-Nutzung bestätigen oder ein lokales Modell wählen."
            ),
        },
        "INDEXING_CANCEL_NOT_AVAILABLE": {
            "title": "Die Indizierung kann nicht abgebrochen werden.",
            "detail": (
                "Die Indizierung ist bereits fertig, fehlgeschlagen oder abgebrochen."
            ),
            "suggested_action": "Liste aktualisieren und den aktuellen Status prüfen.",
        },
    }.get(
        code,
        {
            "title": "Die Aktion konnte nicht abgeschlossen werden.",
            "detail": (
                "Ein unerwarteter Fehler ist aufgetreten; die Eingaben bleiben "
                "soweit sicher erhalten."
            ),
            "suggested_action": (
                "Bitte erneut versuchen oder den aktuellen Stand neu laden."
            ),
        },
    )


def _analysis_problem_response(error: AnalysisError) -> JSONResponse:
    status_code = error.status_code
    contract = _analysis_problem_contract(error.code)
    return JSONResponse(
        status_code=status_code,
        content={
            "type": f"urn:skm:error:{error.code}",
            "title": contract["title"],
            "status": status_code,
            "detail": contract["detail"],
            "code": error.code,
            "correlationId": None,
            "retryable": error.retryable,
            "suggestedAction": contract["suggested_action"],
            "fieldErrors": [
                {"field": field, "message": message}
                for field, message in error.field_errors.items()
            ],
        },
    )


def _cluster_problem_contract(code: str) -> dict[str, str]:
    return {
        "UNEXPECTED_ERROR": {
            "title": "Die Aktion konnte nicht abgeschlossen werden.",
            "detail": (
                "Ein unerwarteter Fehler ist aufgetreten; die Eingaben bleiben "
                "soweit sicher erhalten."
            ),
            "suggested_action": "retry",
        },
        "INDEXING_NOT_COMPLETE": {
            "title": "Das Cluster-Set wurde nicht gestartet.",
            "detail": "Diese Indizierung ist noch nicht abgeschlossen.",
            "suggested_action": "choose-completed-indexing",
        },
        "CLUSTER_VECTOR_BASIS_UNAVAILABLE": {
            "title": "Die Vektor-Basis ist nicht verfügbar.",
            "detail": (
                "Für diese Vektor-Basis fehlen Embeddings oder die Gewichtung ist ungültig."
            ),
            "suggested_action": "choose-vector-basis",
        },
        "CLUSTER_SUMMARY_SAMPLE_COUNT_INVALID": {
            "title": "Die Beispielanzahl ist ungültig.",
            "detail": (
                "Die Beispielanzahl für Zusammenfassungen muss mindestens 1 sein."
            ),
            "suggested_action": "correct-input",
        },
        "CLUSTER_BUDGET_EXCEEDED": {
            "title": "Das Summary-Budget ist überschritten.",
            "detail": (
                "Die Zusammenfassung überschreitet das erlaubte Text- oder Aufruflimit."
            ),
            "suggested_action": "reduce-scope",
        },
        "LLM_CLOUD_CONFIRMATION_REQUIRED": {
            "title": "Cloud-Nutzung muss bestätigt werden.",
            "detail": "Diese Zusammenfassung würde Originaltexte an OpenAI senden.",
            "suggested_action": "confirm-cloud-use",
        },
        "LLM_PROVIDER_UNAVAILABLE": {
            "title": "Der LLM-Provider ist nicht verfügbar.",
            "detail": "Der konfigurierte LLM-Provider oder das Modell ist nicht verfügbar.",
            "suggested_action": "check-provider",
        },
        "CLUSTER_SUMMARY_FAILED": {
            "title": "Die Zusammenfassung konnte nicht erstellt werden.",
            "detail": (
                "Die Clusterbildung ist abgeschlossen, aber die Zusammenfassung ist fehlgeschlagen."
            ),
            "suggested_action": "retry-summary",
        },
        "CLUSTER_SET_CANCEL_NOT_AVAILABLE": {
            "title": "Das Cluster-Set kann nicht abgebrochen werden.",
            "detail": "Der Job ist bereits abgeschlossen, fehlgeschlagen oder abgebrochen.",
            "suggested_action": "reload",
        },
        "CLUSTER_SET_NOT_FOUND": {
            "title": "Cluster-Set nicht gefunden.",
            "detail": "Das Cluster-Set wurde nicht gefunden oder ist nicht mehr verfügbar.",
            "suggested_action": "reload",
        },
        "CLUSTER_SET_NOT_COMPLETE": {
            "title": "Das Cluster-Set ist noch nicht fertig.",
            "detail": "Dieses Cluster-Set kann erst nach Abschluss geladen werden.",
            "suggested_action": "wait",
        },
        "CLUSTER_SOURCE_NOT_FOUND": {
            "title": "Die Quellen konnten nicht geladen werden.",
            "detail": (
                "Der Cluster wurde nicht gefunden oder gehört nicht zum geladenen Set."
            ),
            "suggested_action": "reload",
        },
        "CLUSTER_SOURCE_PAGE_INVALID": {
            "title": "Die Quellen-Seite ist ungültig.",
            "detail": (
                "Die Quellen konnten mit diesen Seitenparametern nicht geladen werden."
            ),
            "suggested_action": "correct-input",
        },
        "CLUSTER_MANUAL_UPDATE_INVALID": {
            "title": "Die Cluster-Änderung ist ungültig.",
            "detail": "Die manuelle Cluster-Änderung konnte nicht gespeichert werden.",
            "suggested_action": "correct-input",
        },
        "CLUSTER_RUN_BOUND_API_REPLACED": {
            "title": "Run-bound Clustering wurde ersetzt.",
            "detail": "Cluster werden jetzt ausschließlich über Cluster-Sets erzeugt und geladen.",
            "suggested_action": "create-cluster-set",
        },
        "CLUSTER_REFINEMENT_EMPTY_SOURCE": {
            "title": "Die Quelle ist leer.",
            "detail": "Die gewählte Quelle enthält keine nutzbaren Zeilen.",
            "suggested_action": "select-sources",
        },
        "CLUSTER_OUTLIER_EMPTY_RESULT": {
            "title": "Die Ausreißer-Einstellung ist zu streng.",
            "detail": "Die Ausreißer-Einstellung würde keine Zeilen übrig lassen.",
            "suggested_action": "adjust-threshold",
        },
        "CLUSTER_OUTLIER_RECALCULATION_FAILED": {
            "title": "Ausreißer konnten nicht neu berechnet werden.",
            "detail": "Die Ausreißer-Neuberechnung konnte nicht abgeschlossen werden.",
            "suggested_action": "retry",
        },
        "CLUSTER_REDUCTION_UNAVAILABLE": {
            "title": "Dimensionsreduzierung ist nicht verfügbar.",
            "detail": "Die gewählte Dimensionsreduzierung ist lokal nicht verfügbar.",
            "suggested_action": "adjust-clustering-parameters",
        },
        "CLUSTER_ACCELERATOR_UNAVAILABLE": {
            "title": "GPU-Beschleunigung ist nicht verfügbar.",
            "detail": "cuML/RAPIDS ist in dieser lokalen Laufzeit nicht verfügbar.",
            "suggested_action": "choose-cpu-backend",
        },
        "CLUSTER_SET_LINEAGE_UNAVAILABLE": {
            "title": "Die Analyse-Historie ist unvollständig.",
            "detail": "Die Cluster-Set-Historie konnte nicht vollständig geladen werden.",
            "suggested_action": "retry",
        },
    }.get(
        code,
        {
            "title": "Die Aktion konnte nicht abgeschlossen werden.",
            "detail": (
                "Ein unerwarteter Fehler ist aufgetreten; die Eingaben bleiben "
                "soweit sicher erhalten."
            ),
            "suggested_action": "retry",
        },
    )


def _cluster_problem_response(error: ClusterError) -> JSONResponse:
    status_code = error.status_code
    contract = _cluster_problem_contract(error.code)
    return JSONResponse(
        status_code=status_code,
        content={
            "type": f"urn:skm:error:{error.code}",
            "title": contract["title"],
            "status": status_code,
            "detail": contract["detail"],
            "code": error.code,
            "correlationId": None,
            "retryable": error.retryable,
            "suggestedAction": contract["suggested_action"],
            "fieldErrors": [
                {"field": field, "message": message}
                for field, message in error.field_errors.items()
            ],
        },
    )


def _export_problem_contract(code: str) -> dict[str, str]:
    return {
        "EXPLORER_EXPORT_EMPTY": {
            "title": "Es gibt nichts zu exportieren.",
            "detail": "Im aktuellen Filterstand gibt es keine exportierbaren Zeilen.",
            "suggested_action": "adjust-filter",
        },
        "EXPLORER_EXPORT_FORMAT_INVALID": {
            "title": "Das Exportformat ist ungültig.",
            "detail": "Der Explorer kann nur als CSV oder JSON exportiert werden.",
            "suggested_action": "choose-format",
        },
        "EXPLORER_EXPORT_SELECTION_TOO_LARGE": {
            "title": "Die Exportauswahl ist zu groß.",
            "detail": "Die aktuelle Explorer-Auswahl enthält zu viele Cluster.",
            "suggested_action": "reduce-scope",
        },
        "EXPLORER_EXPORT_FAILED": {
            "title": "Der Export konnte nicht erstellt werden.",
            "detail": (
                "Die gefilterte Explorer-Ansicht konnte nicht als Datei erzeugt werden."
            ),
            "suggested_action": "retry",
        },
        "CLUSTER_SET_NOT_FOUND": {
            "title": "Cluster-Set nicht gefunden.",
            "detail": "Das Cluster-Set wurde nicht gefunden oder ist nicht mehr verfügbar.",
            "suggested_action": "reload",
        },
        "CLUSTER_SET_NOT_COMPLETE": {
            "title": "Das Cluster-Set ist noch nicht fertig.",
            "detail": "Dieses Cluster-Set kann erst nach Abschluss exportiert werden.",
            "suggested_action": "wait",
        },
    }.get(
        code,
        {
            "title": "Der Export konnte nicht erstellt werden.",
            "detail": (
                "Die gefilterte Explorer-Ansicht konnte nicht als Datei erzeugt werden."
            ),
            "suggested_action": "retry",
        },
    )


def _export_problem_response(error: ExportError) -> JSONResponse:
    status_code = error.status_code
    contract = _export_problem_contract(error.code)
    return JSONResponse(
        status_code=status_code,
        content={
            "type": f"urn:skm:error:{error.code}",
            "title": contract["title"],
            "status": status_code,
            "detail": contract["detail"],
            "code": error.code,
            "correlationId": None,
            "retryable": error.retryable,
            "suggestedAction": contract["suggested_action"],
            "fieldErrors": [
                {"field": field, "message": message}
                for field, message in error.field_errors.items()
            ],
        },
    )


def _is_cluster_set_create_request(request: Request) -> bool:
    path_parts = [part for part in request.url.path.split("/") if part]
    return (
        request.method == "POST"
        and len(path_parts) == 4
        and path_parts[0] == "api"
        and path_parts[1] == "projects"
        and path_parts[3] == "cluster-sets"
    )


def _is_cluster_set_summary_request(request: Request) -> bool:
    path_parts = [part for part in request.url.path.split("/") if part]
    return (
        request.method == "POST"
        and len(path_parts) == 6
        and path_parts[0] == "api"
        and path_parts[1] == "projects"
        and path_parts[3] == "cluster-sets"
        and path_parts[5] == "summaries"
    )


def _is_cluster_source_request(request: Request) -> bool:
    path_parts = [part for part in request.url.path.split("/") if part]
    return (
        request.method == "GET"
        and len(path_parts) == 6
        and path_parts[0] == "api"
        and path_parts[1] == "projects"
        and path_parts[3] == "clusters"
        and path_parts[5] == "sources"
    )


def _validation_error_has_body_field(
    error: RequestValidationError, field_name: str
) -> bool:
    for item in error.errors():
        location = item.get("loc")
        if isinstance(location, (tuple, list)) and tuple(location) == (
            "body",
            field_name,
        ):
            return True
    return False


def _validation_error_has_query_field(
    error: RequestValidationError, field_name: str
) -> bool:
    for item in error.errors():
        location = item.get("loc")
        if isinstance(location, (tuple, list)) and tuple(location) == (
            "query",
            field_name,
        ):
            return True
    return False


def create_app(
    settings: DatabaseSettings | None = None,
    *,
    auth_service: AuthService | None = None,
    user_service: UserService | None = None,
    project_service: ProjectService | None = None,
    import_service: ImportService | None = None,
    import_capacity: ImportCapacity | None = None,
    provider_service: ProviderService | None = None,
    analysis_service: AnalysisService | None = None,
    cluster_service: ClusterService | None = None,
    export_service: ExportService | None = None,
    migration_runner: Callable[[], object] | None = None,
) -> FastAPI:
    auth_service = auth_service or AuthService(settings)
    user_service = user_service or UserService(settings)
    project_service = project_service or ProjectService(settings)
    import_service = import_service or ImportService(settings)
    import_capacity = import_capacity or ImportCapacity()
    provider_service = provider_service or ProviderService(settings)
    analysis_service = analysis_service or AnalysisService(
        settings,
        provider_service=provider_service,  # type: ignore[arg-type]
    )
    cluster_service = cluster_service or ClusterService(
        settings,
        provider_service=provider_service,  # type: ignore[arg-type]
    )
    export_service = export_service or ExportService(settings)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        if migration_runner is not None:
            migration_runner()
        auth_service.seed_initial_user_from_env()
        provider_service.seed_ollama_provider_from_env()
        yield

    app = FastAPI(title="Support Knowledge Miner API", lifespan=lifespan)

    @app.exception_handler(RequestValidationError)
    async def request_validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> Response:
        if (
            _is_cluster_set_create_request(request)
            or _is_cluster_set_summary_request(request)
        ) and _validation_error_has_body_field(
            exc,
            "llm_sample_count",
        ):
            return _cluster_problem_response(
                ClusterError(
                    "LLM summary sample count must be a positive integer",
                    code="CLUSTER_SUMMARY_SAMPLE_COUNT_INVALID",
                    status_code=422,
                    retryable=True,
                    suggested_action="correct-input",
                    field_errors={
                        "llm_sample_count": (
                            "LLM summary sample count must be a positive integer"
                        )
                    },
                )
            )
        if _is_cluster_source_request(request) and (
            _validation_error_has_query_field(exc, "limit")
            or _validation_error_has_query_field(exc, "offset")
        ):
            return _cluster_problem_response(
                ClusterError(
                    "cluster source page parameters are invalid",
                    code="CLUSTER_SOURCE_PAGE_INVALID",
                    status_code=422,
                    retryable=True,
                    suggested_action="correct-input",
                    field_errors={
                        "limit": "limit must be a positive integer",
                        "offset": "offset must be zero or a positive integer",
                    },
                )
            )
        return await default_request_validation_exception_handler(request, exc)

    def current_user(
        credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    ) -> CurrentUser:
        if credentials is None or credentials.scheme.lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="authentication required",
            )
        try:
            return auth_service.authenticate_token(credentials.credentials)
        except AuthenticationError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="authentication required",
            ) from exc

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/api/auth/sign-in", response_model=AuthTokenResponse)
    def sign_in(payload: SignInRequest) -> AuthTokenResponse:
        try:
            token = auth_service.sign_in(payload.email, payload.password)
        except AuthenticationError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="invalid credentials",
            ) from exc
        return AuthTokenResponse(
            access_token=token.access_token,
            token_type=token.token_type,
            expires_at=token.expires_at,
            user=_user_response(token.user),
        )

    @app.post("/api/auth/sign-out", status_code=status.HTTP_204_NO_CONTENT)
    def sign_out(
        response: Response,
        credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
        user: CurrentUser = Depends(current_user),
    ) -> Response:
        if credentials is not None:
            auth_service.sign_out(credentials.credentials, actor_user_id=user.id)
        response.status_code = status.HTTP_204_NO_CONTENT
        return response

    @app.get("/api/auth/me", response_model=UserResponse)
    def me(user: CurrentUser = Depends(current_user)) -> UserResponse:
        return _user_response(user)

    @app.get("/api/projects", response_model=list[ProjectResponse])
    def list_projects(_: CurrentUser = Depends(current_user)) -> list[ProjectResponse]:
        return [
            _project_response(project) for project in project_service.list_projects()
        ]

    @app.post(
        "/api/projects",
        response_model=ProjectResponse,
        status_code=status.HTTP_201_CREATED,
    )
    def create_project(
        payload: CreateProjectRequest,
        actor: CurrentUser = Depends(current_user),
    ) -> ProjectResponse:
        try:
            project = project_service.create_project(
                payload.name, actor_user_id=actor.id
            )
        except ProjectError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
            ) from exc
        return _project_response(project)

    @app.get("/api/projects/{project_id}", response_model=ProjectResponse)
    def get_project(
        project_id: UUID,
        _: CurrentUser = Depends(current_user),
    ) -> ProjectResponse:
        project = project_service.get_project(project_id)
        if project is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="project not found"
            )
        return _project_response(project)

    @app.patch("/api/projects/{project_id}", response_model=ProjectResponse)
    def rename_project(
        project_id: UUID,
        payload: RenameProjectRequest,
        actor: CurrentUser = Depends(current_user),
    ) -> ProjectResponse:
        try:
            project = project_service.rename_project(
                project_id, payload.name, actor_user_id=actor.id
            )
        except ProjectError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
            ) from exc
        return _project_response(project)

    @app.api_route(
        "/api/projects/{project_id}",
        methods=["DELETE"],
        status_code=status.HTTP_204_NO_CONTENT,
    )
    def delete_project(
        project_id: UUID,
        payload: DeleteProjectRequest,
        response: Response,
        actor: CurrentUser = Depends(current_user),
    ) -> Response:
        try:
            project_service.delete_project(
                project_id,
                actor_user_id=actor.id,
                confirmation_name=payload.confirmation_name,
            )
        except ProjectError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
            ) from exc
        response.status_code = status.HTTP_204_NO_CONTENT
        return response

    @app.post(
        "/api/projects/{project_id}/imports",
        response_model=ImportResultResponse,
        status_code=status.HTTP_201_CREATED,
    )
    async def import_project_content(
        project_id: UUID,
        request: Request,
        actor: CurrentUser = Depends(current_user),
    ) -> ImportResultResponse:
        source_type, source_name = _import_metadata(request)
        if not import_capacity.try_acquire():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(
                    "Importkapazität ist ausgelastet. "
                    "Bitte den Import später erneut versuchen."
                ),
                headers={"Retry-After": "5"},
            )
        source_path: Path | None = None
        try:
            source_path = await _spool_import_body(request)
            result = await run_in_threadpool(
                import_service.import_file,
                project_id,
                source_type=source_type,
                source_name=source_name,
                source_path=source_path,
                actor_user_id=actor.id,
            )
        except ClientDisconnect as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Upload wurde vorzeitig abgebrochen.",
            ) from exc
        except ImportError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
            ) from exc
        finally:
            if source_path is not None:
                source_path.unlink(missing_ok=True)
            import_capacity.release()
        return _import_result_response(result)

    @app.get(
        "/api/projects/{project_id}/imports", response_model=list[ImportLogResponse]
    )
    def list_project_imports(
        project_id: UUID,
        _: CurrentUser = Depends(current_user),
    ) -> list[ImportLogResponse]:
        return [
            _import_log_response(log) for log in import_service.list_logs(project_id)
        ]

    @app.get(
        "/api/projects/{project_id}/imports/{import_log_id}/entries",
        response_model=list[ImportLogEntryResponse],
    )
    def list_project_import_log_entries(
        project_id: UUID,
        import_log_id: UUID,
        _: CurrentUser = Depends(current_user),
    ) -> list[ImportLogEntryResponse]:
        return [
            _import_entry_response(entry)
            for entry in import_service.get_log_entries(project_id, import_log_id)
        ]

    @app.patch(
        "/api/projects/{project_id}/dataset-versions/{dataset_version_id}",
        response_model=DatasetVersionResponse,
    )
    def rename_dataset_version(
        project_id: UUID,
        dataset_version_id: UUID,
        payload: RenameDatasetVersionRequest,
        actor: CurrentUser = Depends(current_user),
    ) -> DatasetVersionResponse:
        try:
            dataset = import_service.rename_dataset_version(
                project_id,
                dataset_version_id,
                payload.display_name,
                actor_user_id=actor.id,
            )
        except ImportError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
            ) from exc
        return DatasetVersionResponse.model_validate(dataset)

    @app.delete(
        "/api/projects/{project_id}/dataset-versions/{dataset_version_id}",
        response_model=DatasetVersionResponse,
    )
    def delete_dataset_version(
        project_id: UUID,
        dataset_version_id: UUID,
        actor: CurrentUser = Depends(current_user),
    ) -> DatasetVersionResponse:
        try:
            dataset = import_service.delete_dataset_version(
                project_id,
                dataset_version_id,
                actor_user_id=actor.id,
            )
        except ImportError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
            ) from exc
        return DatasetVersionResponse.model_validate(dataset)

    @app.get("/api/providers", response_model=list[ProviderConfigurationResponse])
    def list_providers(
        _: CurrentUser = Depends(current_user),
    ) -> list[ProviderConfigurationResponse]:
        return [
            _provider_response(configuration)
            for configuration in provider_service.list_configurations()
        ]

    @app.post(
        "/api/providers",
        response_model=ProviderConfigurationResponse,
        status_code=status.HTTP_201_CREATED,
    )
    def create_provider(
        payload: ProviderCreateRequest,
        actor: CurrentUser = Depends(current_user),
    ) -> ProviderConfigurationResponse | JSONResponse:
        try:
            configuration = provider_service.create_configuration(
                payload.provider,
                actor_user_id=actor.id,
            )
        except ProviderError:
            return _provider_problem_response(
                code="VALIDATION_FAILED",
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                retryable=True,
                suggested_action="correct-input",
                field_errors={"provider": "provider must be openai or ollama"},
            )
        return _provider_response(configuration)

    @app.get("/api/llm-providers", response_model=list[ProviderConfigurationResponse])
    def list_llm_providers(
        _: CurrentUser = Depends(current_user),
    ) -> list[ProviderConfigurationResponse]:
        return [
            _provider_response(configuration)
            for configuration in provider_service.list_llm_configurations()
        ]

    @app.put(
        "/api/providers/{provider_ref}",
        response_model=ProviderConfigurationResponse,
    )
    def upsert_provider(
        provider_ref: str,
        payload: ProviderSettingsRequest,
        actor: CurrentUser = Depends(current_user),
    ) -> ProviderConfigurationResponse | JSONResponse:
        try:
            provider_id = UUID(provider_ref)
        except ValueError:
            return _provider_problem_response(
                code="VALIDATION_FAILED",
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                retryable=True,
                suggested_action="reload",
                field_errors={"provider": "provider update requires provider id"},
            )
        try:
            settings = ProviderSettingsInput(
                provider=payload.provider or "",
                display_name=payload.display_name,
                endpoint_url=payload.endpoint_url,
                preserve_endpoint_url="endpoint_url" not in payload.model_fields_set,
                available_models=payload.available_models,
                manual_models=payload.manual_models,
                llm_models=payload.llm_models,
                api_key=payload.api_key,
                remove_api_key=payload.remove_api_key,
            )
            configuration = provider_service.update_configuration(
                provider_id,
                settings,
                actor_user_id=actor.id,
            )
        except ProviderError:
            return _provider_problem_response(
                code="VALIDATION_FAILED",
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                retryable=True,
                suggested_action="correct-input",
            )
        return _provider_response(configuration)

    @app.delete("/api/providers/{provider_id}", response_model=None)
    def delete_provider(
        provider_id: UUID,
        actor: CurrentUser = Depends(current_user),
    ) -> Response | JSONResponse:
        try:
            provider_service.delete_configuration(
                provider_id,
                actor_user_id=actor.id,
            )
        except ProviderDeleteBlocked:
            return _provider_problem_response(
                code="PROVIDER_DELETE_BLOCKED",
                status_code=status.HTTP_409_CONFLICT,
                retryable=True,
                suggested_action="wait",
            )
        except ProviderError:
            return _provider_problem_response(
                code="PROVIDER_DELETE_FAILED",
                status_code=status.HTTP_404_NOT_FOUND,
                retryable=True,
                suggested_action="reload",
            )
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @app.put(
        "/api/llm-providers/{provider}",
        response_model=ProviderConfigurationResponse,
    )
    def upsert_llm_provider(
        provider: str,
        payload: LlmProviderSettingsRequest,
        actor: CurrentUser = Depends(current_user),
    ) -> ProviderConfigurationResponse | JSONResponse:
        _ = provider, payload, actor
        return _provider_problem_response(
            code="VALIDATION_FAILED",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            retryable=True,
            suggested_action="correct-input",
            field_errors={"provider": "provider update requires provider id"},
        )

    @app.post(
        "/api/providers/{provider_ref}/check",
        response_model=ProviderCheckResponse,
    )
    def check_provider(
        provider_ref: str,
        _: CurrentUser = Depends(current_user),
    ) -> ProviderCheckResponse | JSONResponse:
        try:
            provider_id = UUID(provider_ref)
        except ValueError:
            return _provider_problem_response(
                code="VALIDATION_FAILED",
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                retryable=True,
                suggested_action="reload",
                field_errors={"provider": "provider check requires provider id"},
            )
        try:
            result = provider_service.check_provider(provider_id)
        except ProviderError:
            return _provider_problem_response(
                code="VALIDATION_FAILED",
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                retryable=True,
                suggested_action="correct-input",
            )
        return _provider_check_response(result)

    @app.post(
        "/api/providers/{provider_ref}/ollama/pull",
        response_model=ProviderConfigurationResponse,
    )
    def pull_ollama_model_for_provider(
        provider_ref: str,
        payload: OllamaPullRequest,
        actor: CurrentUser = Depends(current_user),
    ) -> ProviderConfigurationResponse | JSONResponse:
        try:
            provider_id = UUID(provider_ref)
        except ValueError:
            return _provider_problem_response(
                code="VALIDATION_FAILED",
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                retryable=True,
                suggested_action="reload",
                field_errors={"provider": "model pull requires provider id"},
            )
        try:
            configuration = provider_service.pull_ollama_model(
                provider_id,
                payload.model,
                actor_user_id=actor.id,
            )
        except ProviderPullInProgress:
            return _provider_problem_response(
                code="PROVIDER_MODEL_PULL_IN_PROGRESS",
                status_code=status.HTTP_409_CONFLICT,
                retryable=False,
                suggested_action="wait",
            )
        except ProviderError:
            return _provider_problem_response(
                code="VALIDATION_FAILED",
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                retryable=True,
                suggested_action="correct-input",
            )
        return _provider_response(configuration)

    @app.post(
        "/api/providers/ollama/pull",
        response_model=ProviderConfigurationResponse,
    )
    def pull_ollama_model(
        payload: OllamaPullRequest,
        actor: CurrentUser = Depends(current_user),
    ) -> ProviderConfigurationResponse | JSONResponse:
        _ = payload, actor
        return _provider_problem_response(
            code="VALIDATION_FAILED",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            retryable=True,
            suggested_action="correct-input",
            field_errors={"provider": "model pull requires provider id"},
        )

    @app.get("/api/jobs/active", response_model=ActiveJobsResponse)
    def active_jobs(
        _: CurrentUser = Depends(current_user),
    ) -> ActiveJobsResponse:
        return ActiveJobsResponse(
            indexing_active=analysis_service.has_active_run(),
            cluster_set_active=cluster_service.has_active_cluster_set(),
        )

    @app.post(
        "/api/projects/{project_id}/indexing-runs",
        response_model=IndexingRunResponse,
        status_code=status.HTTP_201_CREATED,
    )
    def start_indexing_run(
        project_id: UUID,
        payload: IndexingRunRequest,
        actor: CurrentUser = Depends(current_user),
    ) -> IndexingRunResponse | JSONResponse:
        try:
            run = analysis_service.start_run(
                project_id,
                IndexingRunInput(
                    dataset_version_id=payload.dataset_version_id,
                    provider_id=payload.provider_id,
                    provider=payload.provider,
                    model=payload.model,
                    parameters=payload.parameters or {},
                    cloud_use_confirmed=payload.cloud_use_confirmed,
                ),
                actor_user_id=actor.id,
            )
            analysis_service.enqueue_run(run.id)
        except AnalysisQueueFull as exc:
            return _analysis_problem_response(exc)
        except AnalysisError as exc:
            return _analysis_problem_response(exc)
        return _indexing_run_response(run)

    @app.get(
        "/api/projects/{project_id}/indexing-runs",
        response_model=list[IndexingRunResponse],
    )
    def list_indexing_runs(
        project_id: UUID,
        _: CurrentUser = Depends(current_user),
    ) -> list[IndexingRunResponse]:
        return [
            _indexing_run_response(run)
            for run in analysis_service.list_runs(project_id)
        ]

    @app.get(
        "/api/projects/{project_id}/indexing-runs/{run_id}",
        response_model=IndexingRunResponse,
    )
    def get_indexing_run(
        project_id: UUID,
        run_id: UUID,
        _: CurrentUser = Depends(current_user),
    ) -> IndexingRunResponse:
        run = analysis_service.get_run(project_id, run_id)
        if run is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="indexing run not found",
            )
        return _indexing_run_response(run)

    @app.get(
        "/api/projects/{project_id}/indexing-runs/{run_id}/embeddings",
        response_model=list[EmbeddingRecordResponse],
    )
    def list_indexing_run_embeddings(
        project_id: UUID,
        run_id: UUID,
        _: CurrentUser = Depends(current_user),
    ) -> list[EmbeddingRecordResponse]:
        return [
            _embedding_response(record)
            for record in analysis_service.list_embeddings(project_id, run_id)
        ]

    @app.post(
        "/api/projects/{project_id}/indexing-runs/{run_id}/cancel",
        response_model=IndexingRunResponse,
    )
    def cancel_indexing_run(
        project_id: UUID,
        run_id: UUID,
        actor: CurrentUser = Depends(current_user),
    ) -> IndexingRunResponse | JSONResponse:
        try:
            run = analysis_service.cancel_run(
                project_id, run_id, actor_user_id=actor.id
            )
        except AnalysisError as exc:
            return _analysis_problem_response(exc)
        return _indexing_run_response(run)

    @app.delete(
        "/api/projects/{project_id}/indexing-runs/{run_id}",
        status_code=status.HTTP_204_NO_CONTENT,
        response_model=None,
    )
    def delete_indexing_run(
        project_id: UUID,
        run_id: UUID,
        response: Response,
        actor: CurrentUser = Depends(current_user),
    ) -> Response | JSONResponse:
        try:
            analysis_service.delete_run(project_id, run_id, actor_user_id=actor.id)
        except AnalysisError as exc:
            return _analysis_problem_response(exc)
        response.status_code = status.HTTP_204_NO_CONTENT
        return response

    @app.post(
        "/api/projects/{project_id}/cluster-sets",
        response_model=ClusterSetResponse,
        status_code=status.HTTP_201_CREATED,
    )
    def create_cluster_set(
        project_id: UUID,
        payload: ClusterSetRequest,
        actor: CurrentUser = Depends(current_user),
    ) -> ClusterSetResponse | JSONResponse:
        try:
            cluster_set = cluster_service.start_cluster_set(
                project_id,
                ClusterSetInput(
                    indexing_run_id=payload.indexing_run_id,
                    display_name=payload.display_name,
                    parent_cluster_set_id=payload.parent_cluster_set_id,
                    derivation_type=payload.derivation_type,
                    vector_basis=payload.vector_basis,
                    message_weight=payload.message_weight,
                    answer_weight=payload.answer_weight,
                    algorithm_settings=payload.algorithm_settings,
                    source_cluster_ids=payload.source_cluster_ids,
                    source_pair_ids=payload.source_pair_ids,
                    outlier_threshold=payload.outlier_threshold,
                    llm_provider_id=payload.llm_provider_id,
                    llm_provider=payload.llm_provider,
                    llm_model=payload.llm_model,
                    llm_sample_count=payload.llm_sample_count,
                    llm_sample_all=payload.llm_sample_all,
                    llm_cloud_use_confirmed=payload.llm_cloud_use_confirmed,
                ),
                actor_user_id=actor.id,
            )
            cluster_service.enqueue_cluster_set(cluster_set.id)
        except ClusterSetQueueFull as exc:
            return _cluster_problem_response(exc)
        except ClusterError as exc:
            return _cluster_problem_response(exc)
        return _cluster_set_response(cluster_set)

    @app.get(
        "/api/projects/{project_id}/cluster-sets",
        response_model=list[ClusterSetResponse],
    )
    def list_cluster_sets(
        project_id: UUID,
        _: CurrentUser = Depends(current_user),
    ) -> list[ClusterSetResponse]:
        return [
            _cluster_set_response(cluster_set)
            for cluster_set in cluster_service.list_cluster_sets(project_id)
        ]

    @app.get(
        "/api/projects/{project_id}/cluster-sets/{cluster_set_id}",
        response_model=ClusterSetResponse,
    )
    def get_cluster_set(
        project_id: UUID,
        cluster_set_id: UUID,
        _: CurrentUser = Depends(current_user),
    ) -> ClusterSetResponse | JSONResponse:
        cluster_set = cluster_service.get_cluster_set(project_id, cluster_set_id)
        if cluster_set is None:
            return _cluster_problem_response(
                ClusterError(
                    "Cluster-Set not found",
                    code="CLUSTER_SET_NOT_FOUND",
                    status_code=404,
                )
            )
        return _cluster_set_response(cluster_set)

    @app.patch(
        "/api/projects/{project_id}/cluster-sets/{cluster_set_id}",
        response_model=ClusterSetResponse,
    )
    def rename_cluster_set(
        project_id: UUID,
        cluster_set_id: UUID,
        payload: ClusterSetRenameRequest,
        actor: CurrentUser = Depends(current_user),
    ) -> ClusterSetResponse | JSONResponse:
        try:
            cluster_set = cluster_service.rename_cluster_set(
                project_id,
                cluster_set_id,
                payload.display_name,
                actor_user_id=actor.id,
            )
        except ClusterError as exc:
            return _cluster_problem_response(exc)
        return _cluster_set_response(cluster_set)

    @app.post(
        "/api/projects/{project_id}/cluster-sets/{cluster_set_id}/cancel",
        response_model=ClusterSetResponse,
    )
    def cancel_cluster_set(
        project_id: UUID,
        cluster_set_id: UUID,
        actor: CurrentUser = Depends(current_user),
    ) -> ClusterSetResponse | JSONResponse:
        try:
            cluster_set = cluster_service.cancel_cluster_set(
                project_id, cluster_set_id, actor_user_id=actor.id
            )
        except ClusterError as exc:
            return _cluster_problem_response(exc)
        return _cluster_set_response(cluster_set)

    @app.post(
        "/api/projects/{project_id}/cluster-sets/{cluster_set_id}/summaries",
        response_model=ClusterSetResponse,
        status_code=status.HTTP_202_ACCEPTED,
    )
    def regenerate_cluster_set_summaries(
        project_id: UUID,
        cluster_set_id: UUID,
        payload: ClusterSetSummaryRequest,
        actor: CurrentUser = Depends(current_user),
    ) -> ClusterSetResponse | JSONResponse:
        try:
            cluster_set = cluster_service.start_cluster_set_summary_regeneration(
                project_id,
                cluster_set_id,
                ClusterSetSummaryInput(
                    llm_provider_id=payload.llm_provider_id,
                    llm_provider=payload.llm_provider,
                    llm_model=payload.llm_model,
                    llm_sample_count=payload.llm_sample_count,
                    llm_sample_all=payload.llm_sample_all,
                    llm_cloud_use_confirmed=payload.llm_cloud_use_confirmed,
                ),
                actor_user_id=actor.id,
            )
            cluster_service.enqueue_cluster_set_summary_regeneration(cluster_set.id)
        except ClusterSetQueueFull as exc:
            return _cluster_problem_response(exc)
        except ClusterError as exc:
            return _cluster_problem_response(exc)
        return _cluster_set_response(cluster_set)

    @app.delete(
        "/api/projects/{project_id}/cluster-sets/{cluster_set_id}",
        status_code=status.HTTP_204_NO_CONTENT,
        response_model=None,
    )
    def delete_cluster_set(
        project_id: UUID,
        cluster_set_id: UUID,
        response: Response,
        actor: CurrentUser = Depends(current_user),
    ) -> Response | JSONResponse:
        try:
            cluster_service.delete_cluster_set(
                project_id, cluster_set_id, actor_user_id=actor.id
            )
        except ClusterError as exc:
            return _cluster_problem_response(exc)
        response.status_code = status.HTTP_204_NO_CONTENT
        return response

    @app.get(
        "/api/projects/{project_id}/cluster-sets/{cluster_set_id}/clusters",
        response_model=list[ClusterResponse],
    )
    def list_cluster_set_clusters(
        project_id: UUID,
        cluster_set_id: UUID,
        _: CurrentUser = Depends(current_user),
    ) -> list[ClusterResponse] | JSONResponse:
        try:
            return [
                _cluster_response(cluster)
                for cluster in cluster_service.list_clusters_for_set(
                    project_id, cluster_set_id
                )
            ]
        except ClusterError as exc:
            return _cluster_problem_response(exc)

    @app.get(
        "/api/projects/{project_id}/cluster-sets/{cluster_set_id}/events",
        response_model=list[ClusterSetEventResponse],
    )
    def list_cluster_set_events(
        project_id: UUID,
        cluster_set_id: UUID,
        _: CurrentUser = Depends(current_user),
    ) -> list[ClusterSetEventResponse] | JSONResponse:
        try:
            events = cluster_service.list_cluster_set_events(project_id, cluster_set_id)
        except ClusterError as exc:
            return _cluster_problem_response(exc)
        return [_cluster_set_event_response(event) for event in events]

    @app.post(
        "/api/projects/{project_id}/analysis-runs/{run_id}/clusters/generate",
        response_model=list[ClusterResponse],
    )
    def generate_clusters(
        project_id: UUID,
        run_id: UUID,
        actor: CurrentUser = Depends(current_user),
    ) -> JSONResponse:
        del project_id, run_id, actor
        return _cluster_problem_response(
            ClusterError(
                "run-bound clustering has been replaced by Cluster-Sets",
                code="CLUSTER_RUN_BOUND_API_REPLACED",
                status_code=status.HTTP_410_GONE,
                suggested_action="create-cluster-set",
            )
        )

    @app.get(
        "/api/projects/{project_id}/analysis-runs/{run_id}/clusters",
        response_model=list[ClusterResponse],
    )
    def list_clusters(
        project_id: UUID,
        run_id: UUID,
        actor: CurrentUser = Depends(current_user),
    ) -> JSONResponse:
        del project_id, run_id, actor
        return _cluster_problem_response(
            ClusterError(
                "run-bound cluster loading has been replaced by Cluster-Sets",
                code="CLUSTER_RUN_BOUND_API_REPLACED",
                status_code=status.HTTP_410_GONE,
                suggested_action="create-cluster-set",
            )
        )

    @app.patch(
        "/api/projects/{project_id}/clusters/{cluster_id}",
        response_model=ClusterResponse,
    )
    def update_cluster(
        project_id: UUID,
        cluster_id: UUID,
        payload: ClusterUpdateRequest,
        actor: CurrentUser = Depends(current_user),
    ) -> ClusterResponse | JSONResponse:
        try:
            cluster = cluster_service.update_cluster(
                project_id,
                cluster_id,
                ClusterManualUpdate(
                    manual_title=payload.manual_title,
                    manual_category=payload.manual_category,
                    manual_status=payload.manual_status,
                    fields_to_update=frozenset(payload.model_fields_set),
                ),
                actor_user_id=actor.id,
            )
        except ClusterError as exc:
            return _cluster_problem_response(exc)
        return _cluster_response(cluster)

    @app.get(
        "/api/projects/{project_id}/clusters/{cluster_id}/sources",
        response_model=ClusterSourcePageResponse,
    )
    def list_cluster_sources(
        project_id: UUID,
        cluster_id: UUID,
        limit: int = DEFAULT_CLUSTER_SOURCE_PAGE_SIZE,
        offset: int = 0,
        _: CurrentUser = Depends(current_user),
    ) -> ClusterSourcePageResponse | JSONResponse:
        try:
            return _cluster_source_page_response(
                cluster_service.list_sources(
                    project_id,
                    cluster_id,
                    limit=limit,
                    offset=offset,
                )
            )
        except ClusterError as exc:
            return _cluster_problem_response(exc)

    @app.post(
        "/api/projects/{project_id}/exports/explorer",
        response_model=ExportResultResponse,
        status_code=status.HTTP_201_CREATED,
    )
    def export_explorer(
        project_id: UUID,
        payload: ExplorerExportRequest,
        actor: CurrentUser = Depends(current_user),
    ) -> ExportResultResponse | JSONResponse:
        try:
            result = export_service.export_explorer(
                project_id,
                ExplorerExportInput(
                    cluster_set_id=payload.cluster_set_id,
                    export_format=payload.export_format,
                    search_query=payload.search_query,
                    category=payload.category,
                    include_excluded=payload.include_excluded,
                    include_outliers=payload.include_outliers,
                    cluster_ids=payload.cluster_ids,
                ),
                actor_user_id=actor.id,
            )
        except ExportError as exc:
            return _export_problem_response(exc)
        return _export_result_response(result)

    @app.get(
        "/api/projects/{project_id}/exports",
        response_model=list[ExportLogResponse],
    )
    def list_exports(
        project_id: UUID,
        _: CurrentUser = Depends(current_user),
    ) -> list[ExportLogResponse]:
        return [
            _export_log_response(log) for log in export_service.list_exports(project_id)
        ]

    @app.get("/api/users", response_model=list[UserResponse])
    def list_users(_: CurrentUser = Depends(current_user)) -> list[UserResponse]:
        return [_user_response(user) for user in user_service.list_users()]

    @app.post(
        "/api/users",
        response_model=UserResponse,
        status_code=status.HTTP_201_CREATED,
    )
    def create_user(
        payload: CreateUserRequest,
        actor: CurrentUser = Depends(current_user),
    ) -> UserResponse:
        try:
            user = user_service.create_user(
                CreateUserInput(
                    first_name=payload.first_name,
                    last_name=payload.last_name,
                    email=payload.email,
                    password=payload.password,
                ),
                actor_user_id=actor.id,
            )
        except UserError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
            ) from exc
        return _user_response(user)

    @app.patch("/api/users/{user_id}", response_model=UserResponse)
    def update_user(
        user_id: UUID,
        payload: UpdateUserRequest,
        actor: CurrentUser = Depends(current_user),
    ) -> UserResponse:
        try:
            user = user_service.update_user(
                user_id,
                UpdateUserInput(
                    first_name=payload.first_name,
                    last_name=payload.last_name,
                    email=payload.email,
                ),
                actor_user_id=actor.id,
            )
        except UserError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
            ) from exc
        return _user_response(user)

    @app.post("/api/users/{user_id}/password", status_code=status.HTTP_204_NO_CONTENT)
    def set_password(
        user_id: UUID,
        payload: SetPasswordRequest,
        response: Response,
        actor: CurrentUser = Depends(current_user),
    ) -> Response:
        try:
            user_service.set_password(user_id, payload.password, actor_user_id=actor.id)
        except UserError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
            ) from exc
        response.status_code = status.HTTP_204_NO_CONTENT
        return response

    @app.delete("/api/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_user(
        user_id: UUID,
        response: Response,
        actor: CurrentUser = Depends(current_user),
    ) -> Response:
        try:
            user_service.delete_user(user_id, actor_user_id=actor.id)
        except UserError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
            ) from exc
        response.status_code = status.HTTP_204_NO_CONTENT
        return response

    return app
