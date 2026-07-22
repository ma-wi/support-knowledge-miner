"""FastAPI boundary for local authentication and user management."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field

from backend.auth import AuthService, CurrentUser
from backend.auth.service import AuthenticationError
from backend.config import DatabaseSettings
from backend.imports import (
    ImportError,
    ImportLog,
    ImportLogEntry,
    ImportResult,
    ImportService,
)
from backend.projects import ProjectError, ProjectService, PublicProject
from backend.users import CreateUserInput, UpdateUserInput, UserService
from backend.users.service import PublicUser, UserError

_bearer = HTTPBearer(auto_error=False)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    first_name: str
    last_name: str
    email: str
    created_at: datetime
    updated_at: datetime


class SignInRequest(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_at: datetime
    user: UserResponse


class CreateUserRequest(BaseModel):
    username: str = Field(min_length=1)
    first_name: str = Field(min_length=1)
    last_name: str = Field(min_length=1)
    email: str = Field(min_length=1)
    password: str = Field(min_length=1)


class UpdateUserRequest(BaseModel):
    username: str | None = Field(default=None, min_length=1)
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


class ImportRequest(BaseModel):
    source_type: str = Field(min_length=1)
    source_name: str = Field(min_length=1)
    content: str = Field(min_length=1)


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
    )


def create_app(
    settings: DatabaseSettings | None = None,
    *,
    auth_service: AuthService | None = None,
    user_service: UserService | None = None,
    project_service: ProjectService | None = None,
    import_service: ImportService | None = None,
) -> FastAPI:
    auth_service = auth_service or AuthService(settings)
    user_service = user_service or UserService(settings)
    project_service = project_service or ProjectService(settings)
    import_service = import_service or ImportService(settings)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        auth_service.seed_initial_user_from_env()
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
            token = auth_service.sign_in(payload.username, payload.password)
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
    def import_project_content(
        project_id: UUID,
        payload: ImportRequest,
        actor: CurrentUser = Depends(current_user),
    ) -> ImportResultResponse:
        try:
            result = import_service.import_content(
                project_id,
                source_type=payload.source_type,
                source_name=payload.source_name,
                content=payload.content,
                actor_user_id=actor.id,
            )
        except ImportError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
            ) from exc
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
                    username=payload.username,
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
                    username=payload.username,
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
