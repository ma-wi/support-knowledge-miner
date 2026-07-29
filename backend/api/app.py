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
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field
from starlette.concurrency import run_in_threadpool
from starlette.requests import ClientDisconnect

from backend.analysis import (
    AnalysisError,
    AnalysisQueueFull,
    AnalysisRun,
    AnalysisRunInput,
    AnalysisService,
    EmbeddingRecord,
)
from backend.auth import AuthService, CurrentUser
from backend.auth.service import AuthenticationError
from backend.candidates import (
    Candidate,
    CandidateError,
    CandidateManualUpdate,
    CandidateService,
    CandidateSource,
)
from backend.clusters import (
    Cluster,
    ClusterError,
    ClusterManualUpdate,
    ClusterService,
    ClusterSource,
)
from backend.config import DatabaseSettings
from backend.exports import ExportError, ExportLog, ExportResult, ExportService
from backend.imports import (
    ImportError,
    ImportLog,
    ImportLogEntry,
    ImportResult,
    ImportService,
)
from backend.imports.service import MAX_IMPORT_BYTES
from backend.providers import (
    AnalysisProfile,
    AnalysisProfileInput,
    ProviderCheckResult,
    ProviderConfiguration,
    ProviderError,
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
    dataset_version_id: UUID | None
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
    created_at: datetime


class ImportResultResponse(BaseModel):
    log: ImportLogResponse
    dataset_version: DatasetVersionResponse | None
    skipped_entries: list[ImportLogEntryResponse]
    skipped_entries_truncated: bool


class ProviderSettingsRequest(BaseModel):
    endpoint_url: str | None = None
    manual_models: list[str] = Field(default_factory=list)
    api_key: str | None = None
    remove_api_key: bool = False


class ProviderConfigurationResponse(BaseModel):
    provider: str
    endpoint_url: str | None
    manual_models: list[str]
    api_key_set: bool
    updated_at: datetime


class ProviderCheckResponse(BaseModel):
    provider: str
    ok: bool
    models: list[str]
    message: str


class OllamaPullRequest(BaseModel):
    model: str = Field(min_length=1)


class AnalysisProfileRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    provider: str = Field(min_length=1)
    model: str = Field(min_length=1)
    thresholds: dict[str, object] = Field(default_factory=dict)
    algorithm_settings: dict[str, object] = Field(default_factory=dict)
    prompt_template: str | None = None


class AnalysisProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    name: str
    provider: str
    model: str
    is_cloud_provider: bool
    thresholds: dict[str, object]
    algorithm_settings: dict[str, object]
    prompt_template: str | None
    created_at: datetime
    updated_at: datetime


class AnalysisRunRequest(BaseModel):
    dataset_version_id: UUID
    analysis_profile_id: UUID
    parameters: dict[str, object] = Field(default_factory=dict)


class AnalysisRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    dataset_version_id: UUID
    analysis_profile_id: UUID
    status: str
    progress: int
    profile_snapshot: dict[str, object]
    provider: str
    model: str
    parameters: dict[str, object]
    error_message: str | None
    diagnostics: dict[str, object]
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class EmbeddingRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    analysis_run_id: UUID
    dataset_version_id: UUID
    analysis_profile_id: UUID
    source_object_type: str
    source_object_id: UUID
    text_variant: str
    model: str
    dimensions: int
    metadata: dict[str, object]
    created_at: datetime


class ClusterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    analysis_run_id: UUID
    dataset_version_id: UUID
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


class CandidateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    dataset_version_id: UUID
    analysis_run_id: UUID | None
    source_cluster_id: UUID | None
    candidate_type: str
    auto_status: str
    manual_status: str | None
    effective_status: str
    language: str
    auto_category_path: str | None
    manual_category_path: str | None
    effective_category_path: str | None
    auto_title: str
    manual_title: str | None
    effective_title: str
    auto_canonical_question: str
    manual_canonical_question: str | None
    effective_canonical_question: str
    auto_canonical_answer: str
    manual_canonical_answer: str | None
    effective_canonical_answer: str
    auto_alternative_questions: list[str]
    manual_alternative_questions: list[str] | None
    effective_alternative_questions: list[str]
    auto_parameters: dict[str, object]
    manual_parameters: dict[str, object] | None
    effective_parameters: dict[str, object]
    auto_external_data_dependencies: list[str]
    manual_external_data_dependencies: list[str] | None
    effective_external_data_dependencies: list[str]
    quality_score: float
    faq_suitability_score: float
    dynamicity_score: float
    contradiction_score: float
    source_pair_count: int
    source_cluster_ids: list[UUID]
    notes: str | None
    metadata: dict[str, object]
    created_at: datetime
    updated_at: datetime


class CandidateUpdateRequest(BaseModel):
    candidate_type: str | None = None
    manual_status: str | None = None
    manual_category_path: str | None = None
    manual_title: str | None = None
    manual_canonical_question: str | None = None
    manual_canonical_answer: str | None = None
    manual_alternative_questions: list[str] | None = None
    manual_parameters: dict[str, object] | None = None
    manual_external_data_dependencies: list[str] | None = None
    notes: str | None = None


class CandidateSourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    candidate_id: UUID
    cluster_id: UUID | None
    message_pair_id: UUID
    ticket_id: str
    message_group_id: str
    message: str
    answer: str
    message_segment_id: str | None
    source_language: str
    normalized_customer_message: str | None
    normalized_support_answer: str | None
    assignment_type: str
    membership_score: float
    is_multi_intent: bool
    intent_label: str | None
    dataset_version_id: UUID
    analysis_run_id: UUID | None


class ExportRequest(BaseModel):
    include_original_text: bool = False


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
    output_filename: str
    output_path: str | None
    row_count: int
    created_at: datetime


class ExportResultResponse(BaseModel):
    export: ExportLogResponse
    csv_content: str
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
        provider=configuration.provider,
        endpoint_url=configuration.endpoint_url,
        manual_models=configuration.manual_models,
        api_key_set=configuration.api_key_set,
        updated_at=configuration.updated_at,
    )


def _provider_check_response(result: ProviderCheckResult) -> ProviderCheckResponse:
    return ProviderCheckResponse(
        provider=result.provider,
        ok=result.ok,
        models=result.models,
        message=result.message,
    )


def _analysis_profile_response(profile: AnalysisProfile) -> AnalysisProfileResponse:
    return AnalysisProfileResponse.model_validate(profile)


def _analysis_run_response(run: AnalysisRun) -> AnalysisRunResponse:
    return AnalysisRunResponse.model_validate(run)


def _embedding_response(record: EmbeddingRecord) -> EmbeddingRecordResponse:
    return EmbeddingRecordResponse.model_validate(record)


def _cluster_response(cluster: Cluster) -> ClusterResponse:
    return ClusterResponse.model_validate(cluster)


def _cluster_source_response(source: ClusterSource) -> ClusterSourceResponse:
    return ClusterSourceResponse.model_validate(source)


def _candidate_response(candidate: Candidate) -> CandidateResponse:
    return CandidateResponse.model_validate(candidate)


def _candidate_source_response(source: CandidateSource) -> CandidateSourceResponse:
    return CandidateSourceResponse.model_validate(source)


def _export_log_response(log: ExportLog) -> ExportLogResponse:
    return ExportLogResponse.model_validate(log)


def _export_result_response(result: ExportResult) -> ExportResultResponse:
    return ExportResultResponse(
        export=_export_log_response(result.log),
        csv_content=result.csv_content,
        warning=result.warning,
    )


def _analysis_profile_input(payload: AnalysisProfileRequest) -> AnalysisProfileInput:
    return AnalysisProfileInput(
        name=payload.name,
        provider=payload.provider,
        model=payload.model,
        thresholds=payload.thresholds,
        algorithm_settings=payload.algorithm_settings,
        prompt_template=payload.prompt_template,
    )


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
    candidate_service: CandidateService | None = None,
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
    cluster_service = cluster_service or ClusterService(settings)
    candidate_service = candidate_service or CandidateService(settings)
    export_service = export_service or ExportService(settings)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        if migration_runner is not None:
            migration_runner()
        auth_service.seed_initial_user_from_env()
        provider_service.seed_ollama_provider_from_env()
        yield

    app = FastAPI(title="Support Knowledge Miner API", lifespan=lifespan)

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

    @app.get("/api/providers", response_model=list[ProviderConfigurationResponse])
    def list_providers(
        _: CurrentUser = Depends(current_user),
    ) -> list[ProviderConfigurationResponse]:
        return [
            _provider_response(configuration)
            for configuration in provider_service.list_configurations()
        ]

    @app.put(
        "/api/providers/{provider}",
        response_model=ProviderConfigurationResponse,
    )
    def upsert_provider(
        provider: str,
        payload: ProviderSettingsRequest,
        actor: CurrentUser = Depends(current_user),
    ) -> ProviderConfigurationResponse:
        try:
            configuration = provider_service.upsert_configuration(
                ProviderSettingsInput(
                    provider=provider,
                    endpoint_url=payload.endpoint_url,
                    manual_models=payload.manual_models,
                    api_key=payload.api_key,
                    remove_api_key=payload.remove_api_key,
                ),
                actor_user_id=actor.id,
            )
        except ProviderError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
            ) from exc
        return _provider_response(configuration)

    @app.post(
        "/api/providers/{provider}/check",
        response_model=ProviderCheckResponse,
    )
    def check_provider(
        provider: str,
        _: CurrentUser = Depends(current_user),
    ) -> ProviderCheckResponse:
        try:
            result = provider_service.check_provider(provider)
        except ProviderError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
            ) from exc
        return _provider_check_response(result)

    @app.post(
        "/api/providers/ollama/pull",
        response_model=ProviderConfigurationResponse,
    )
    def pull_ollama_model(
        payload: OllamaPullRequest,
        actor: CurrentUser = Depends(current_user),
    ) -> ProviderConfigurationResponse:
        try:
            configuration = provider_service.pull_ollama_model(
                payload.model,
                actor_user_id=actor.id,
            )
        except ProviderError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
            ) from exc
        return _provider_response(configuration)

    @app.get(
        "/api/projects/{project_id}/analysis-profiles",
        response_model=list[AnalysisProfileResponse],
    )
    def list_analysis_profiles(
        project_id: UUID,
        _: CurrentUser = Depends(current_user),
    ) -> list[AnalysisProfileResponse]:
        return [
            _analysis_profile_response(profile)
            for profile in provider_service.list_profiles(project_id)
        ]

    @app.post(
        "/api/projects/{project_id}/analysis-profiles",
        response_model=AnalysisProfileResponse,
        status_code=status.HTTP_201_CREATED,
    )
    def create_analysis_profile(
        project_id: UUID,
        payload: AnalysisProfileRequest,
        actor: CurrentUser = Depends(current_user),
    ) -> AnalysisProfileResponse:
        try:
            profile = provider_service.create_profile(
                project_id,
                _analysis_profile_input(payload),
                actor_user_id=actor.id,
            )
        except ProviderError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
            ) from exc
        return _analysis_profile_response(profile)

    @app.patch(
        "/api/projects/{project_id}/analysis-profiles/{profile_id}",
        response_model=AnalysisProfileResponse,
    )
    def update_analysis_profile(
        project_id: UUID,
        profile_id: UUID,
        payload: AnalysisProfileRequest,
        actor: CurrentUser = Depends(current_user),
    ) -> AnalysisProfileResponse:
        try:
            profile = provider_service.update_profile(
                project_id,
                profile_id,
                _analysis_profile_input(payload),
                actor_user_id=actor.id,
            )
        except ProviderError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
            ) from exc
        return _analysis_profile_response(profile)

    @app.post(
        "/api/projects/{project_id}/analysis-runs",
        response_model=AnalysisRunResponse,
        status_code=status.HTTP_201_CREATED,
    )
    def start_analysis_run(
        project_id: UUID,
        payload: AnalysisRunRequest,
        actor: CurrentUser = Depends(current_user),
    ) -> AnalysisRunResponse:
        try:
            run = analysis_service.start_run(
                project_id,
                AnalysisRunInput(
                    dataset_version_id=payload.dataset_version_id,
                    analysis_profile_id=payload.analysis_profile_id,
                    parameters=payload.parameters,
                ),
                actor_user_id=actor.id,
            )
            analysis_service.enqueue_run(run.id)
        except AnalysisQueueFull as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
            ) from exc
        except AnalysisError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
            ) from exc
        return _analysis_run_response(run)

    @app.get(
        "/api/projects/{project_id}/analysis-runs",
        response_model=list[AnalysisRunResponse],
    )
    def list_analysis_runs(
        project_id: UUID,
        _: CurrentUser = Depends(current_user),
    ) -> list[AnalysisRunResponse]:
        return [
            _analysis_run_response(run)
            for run in analysis_service.list_runs(project_id)
        ]

    @app.get(
        "/api/projects/{project_id}/analysis-runs/{run_id}",
        response_model=AnalysisRunResponse,
    )
    def get_analysis_run(
        project_id: UUID,
        run_id: UUID,
        _: CurrentUser = Depends(current_user),
    ) -> AnalysisRunResponse:
        run = analysis_service.get_run(project_id, run_id)
        if run is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="analysis run not found",
            )
        return _analysis_run_response(run)

    @app.get(
        "/api/projects/{project_id}/analysis-runs/{run_id}/embeddings",
        response_model=list[EmbeddingRecordResponse],
    )
    def list_analysis_run_embeddings(
        project_id: UUID,
        run_id: UUID,
        _: CurrentUser = Depends(current_user),
    ) -> list[EmbeddingRecordResponse]:
        return [
            _embedding_response(record)
            for record in analysis_service.list_embeddings(project_id, run_id)
        ]

    @app.post(
        "/api/projects/{project_id}/analysis-runs/{run_id}/clusters/generate",
        response_model=list[ClusterResponse],
    )
    def generate_clusters(
        project_id: UUID,
        run_id: UUID,
        actor: CurrentUser = Depends(current_user),
    ) -> list[ClusterResponse]:
        try:
            clusters = cluster_service.generate_for_run(
                project_id, run_id, actor_user_id=actor.id
            )
        except ClusterError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
            ) from exc
        return [_cluster_response(cluster) for cluster in clusters]

    @app.get(
        "/api/projects/{project_id}/analysis-runs/{run_id}/clusters",
        response_model=list[ClusterResponse],
    )
    def list_clusters(
        project_id: UUID,
        run_id: UUID,
        _: CurrentUser = Depends(current_user),
    ) -> list[ClusterResponse]:
        return [
            _cluster_response(cluster)
            for cluster in cluster_service.list_clusters(project_id, run_id)
        ]

    @app.patch(
        "/api/projects/{project_id}/clusters/{cluster_id}",
        response_model=ClusterResponse,
    )
    def update_cluster(
        project_id: UUID,
        cluster_id: UUID,
        payload: ClusterUpdateRequest,
        actor: CurrentUser = Depends(current_user),
    ) -> ClusterResponse:
        try:
            cluster = cluster_service.update_cluster(
                project_id,
                cluster_id,
                ClusterManualUpdate(
                    manual_title=payload.manual_title,
                    manual_category=payload.manual_category,
                    manual_status=payload.manual_status,
                ),
                actor_user_id=actor.id,
            )
        except ClusterError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
            ) from exc
        return _cluster_response(cluster)

    @app.get(
        "/api/projects/{project_id}/clusters/{cluster_id}/sources",
        response_model=list[ClusterSourceResponse],
    )
    def list_cluster_sources(
        project_id: UUID,
        cluster_id: UUID,
        _: CurrentUser = Depends(current_user),
    ) -> list[ClusterSourceResponse]:
        return [
            _cluster_source_response(source)
            for source in cluster_service.list_sources(project_id, cluster_id)
        ]

    @app.post(
        "/api/projects/{project_id}/clusters/{cluster_id}/candidates",
        response_model=CandidateResponse,
        status_code=status.HTTP_201_CREATED,
    )
    def create_candidate_from_cluster(
        project_id: UUID,
        cluster_id: UUID,
        actor: CurrentUser = Depends(current_user),
    ) -> CandidateResponse:
        try:
            candidate = candidate_service.create_from_cluster(
                project_id, cluster_id, actor_user_id=actor.id
            )
        except CandidateError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
            ) from exc
        return _candidate_response(candidate)

    @app.get(
        "/api/projects/{project_id}/candidates",
        response_model=list[CandidateResponse],
    )
    def list_candidates(
        project_id: UUID,
        _: CurrentUser = Depends(current_user),
    ) -> list[CandidateResponse]:
        return [
            _candidate_response(candidate)
            for candidate in candidate_service.list_candidates(project_id)
        ]

    @app.patch(
        "/api/projects/{project_id}/candidates/{candidate_id}",
        response_model=CandidateResponse,
    )
    def update_candidate(
        project_id: UUID,
        candidate_id: UUID,
        payload: CandidateUpdateRequest,
        actor: CurrentUser = Depends(current_user),
    ) -> CandidateResponse:
        fields_to_update = frozenset(payload.model_fields_set)
        try:
            candidate = candidate_service.update_candidate(
                project_id,
                candidate_id,
                CandidateManualUpdate(
                    candidate_type=payload.candidate_type,
                    manual_status=payload.manual_status,
                    manual_category_path=payload.manual_category_path,
                    manual_title=payload.manual_title,
                    manual_canonical_question=payload.manual_canonical_question,
                    manual_canonical_answer=payload.manual_canonical_answer,
                    manual_alternative_questions=payload.manual_alternative_questions,
                    manual_parameters=payload.manual_parameters,
                    manual_external_data_dependencies=(
                        payload.manual_external_data_dependencies
                    ),
                    notes=payload.notes,
                    fields_to_update=fields_to_update,
                ),
                actor_user_id=actor.id,
            )
        except CandidateError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
            ) from exc
        return _candidate_response(candidate)

    @app.get(
        "/api/projects/{project_id}/candidates/{candidate_id}/sources",
        response_model=list[CandidateSourceResponse],
    )
    def list_candidate_sources(
        project_id: UUID,
        candidate_id: UUID,
        _: CurrentUser = Depends(current_user),
    ) -> list[CandidateSourceResponse]:
        return [
            _candidate_source_response(source)
            for source in candidate_service.list_sources(project_id, candidate_id)
        ]

    @app.post(
        "/api/projects/{project_id}/exports/candidates",
        response_model=ExportResultResponse,
        status_code=status.HTTP_201_CREATED,
    )
    def export_candidates(
        project_id: UUID,
        payload: ExportRequest,
        actor: CurrentUser = Depends(current_user),
    ) -> ExportResultResponse:
        try:
            result = export_service.export_candidates(
                project_id,
                include_original_text=payload.include_original_text,
                actor_user_id=actor.id,
            )
        except ExportError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
            ) from exc
        return _export_result_response(result)

    @app.post(
        "/api/projects/{project_id}/exports/source-assignments",
        response_model=ExportResultResponse,
        status_code=status.HTTP_201_CREATED,
    )
    def export_source_assignments(
        project_id: UUID,
        payload: ExportRequest,
        actor: CurrentUser = Depends(current_user),
    ) -> ExportResultResponse:
        try:
            result = export_service.export_source_assignments(
                project_id,
                include_original_text=payload.include_original_text,
                actor_user_id=actor.id,
            )
        except ExportError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
            ) from exc
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
