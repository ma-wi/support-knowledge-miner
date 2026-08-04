from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from threading import Event
from uuid import UUID

import pytest

import backend.analysis.service as analysis_service_module
from backend.analysis import (
    AnalysisQueueFull,
    AnalysisService,
    IndexingRunInput,
)
from backend.providers import ProviderError

ACTOR_ID = UUID("11111111-1111-1111-1111-111111111111")
PROJECT_ID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
DATASET_ID = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
PAIR_ID = UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee")
NOW = datetime(2026, 7, 22, tzinfo=UTC)


class FakeResult:
    def __init__(self, rows: list[dict[str, object]] | None = None) -> None:
        self._rows = rows or []
        self._offset = 0

    def fetchone(self) -> dict[str, object] | None:
        return self._rows[0] if self._rows else None

    def fetchall(self) -> list[dict[str, object]]:
        return self._rows

    def fetchmany(self, size: int) -> list[dict[str, object]]:
        rows = self._rows[self._offset : self._offset + size]
        self._offset += len(rows)
        return rows


class FakeTransaction:
    def __enter__(self) -> FakeTransaction:
        return self

    def __exit__(self, *_: object) -> None:
        return None


class FakeServerCursor:
    def __init__(self, connection: AnalysisConnection, name: str) -> None:
        self._connection = connection
        self._name = name
        self._result: FakeResult | None = None

    def __enter__(self) -> FakeServerCursor:
        assert self._connection.active_server_cursor is None
        self._connection.active_server_cursor = self._name
        self._connection.server_cursor_events.append(("open", self._name))
        return self

    def __exit__(self, *_: object) -> None:
        assert self._connection.active_server_cursor == self._name
        self._connection.server_cursor_events.append(("close", self._name))
        self._connection.active_server_cursor = None

    def execute(
        self, query: str, params: tuple[object, ...] | None = None
    ) -> FakeServerCursor:
        self._result = self._connection.execute_server_cursor(query, params)
        return self

    def fetchmany(self, size: int) -> list[dict[str, object]]:
        assert self._result is not None
        return self._result.fetchmany(size)


class AnalysisConnection:
    def __init__(
        self,
        *,
        provider: str = "vllm",
        api_key_set: bool = False,
        endpoint_url: str | None = "http://localhost:8000/",
        message: str = "How do I reset it?",
        answer: str = "Use the reset flow.",
        messages: list[tuple[str, str]] | None = None,
    ) -> None:
        self.run: dict[str, object] | None = None
        self.embeddings: list[dict[str, object]] = []
        self.progress_updates: list[int] = []
        self.active_server_cursor: str | None = None
        self.server_cursor_events: list[tuple[str, str]] = []
        self.provider = provider
        self.api_key_secret = "encrypted" if api_key_set else None
        self.endpoint_url = endpoint_url
        self.messages = messages if messages is not None else [(message, answer)]

    def __enter__(self) -> AnalysisConnection:
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def transaction(self) -> FakeTransaction:
        return FakeTransaction()

    def cursor(self, *, name: str) -> FakeServerCursor:
        return FakeServerCursor(self, name)

    def execute_server_cursor(
        self, query: str, params: tuple[object, ...] | None = None
    ) -> FakeResult:
        assert params == (PROJECT_ID, DATASET_ID)
        normalized = " ".join(query.split())
        if normalized.startswith("SELECT message, answer FROM message_pairs"):
            return FakeResult(
                [
                    {"message": message, "answer": answer}
                    for message, answer in self.messages
                ]
            )
        if normalized.startswith(
            "SELECT id, ordinal, message, answer FROM message_pairs"
        ):
            return FakeResult(
                [
                    {
                        "id": PAIR_ID if index == 0 else UUID(int=index + 1),
                        "ordinal": index + 1,
                        "message": message,
                        "answer": answer,
                    }
                    for index, (message, answer) in enumerate(self.messages)
                ]
            )
        raise AssertionError(f"unexpected server-cursor query: {normalized}")

    def execute(
        self, query: str, params: tuple[object, ...] | None = None
    ) -> FakeResult:
        normalized = " ".join(query.split())
        if normalized.startswith("SELECT id, record_count, display_name, deleted_at"):
            return FakeResult(
                [
                    {
                        "id": DATASET_ID,
                        "record_count": len(self.messages),
                        "display_name": "Support import",
                        "deleted_at": None,
                    }
                ]
            )
        if normalized.startswith("SELECT manual_models, api_key_secret, endpoint_url"):
            assert params == (self.provider,)
            return FakeResult(
                [
                    {
                        "manual_models": ["local-embed"],
                        "api_key_secret": self.api_key_secret,
                        "endpoint_url": self.endpoint_url,
                    }
                ]
            )
        if normalized.startswith("INSERT INTO analysis_runs"):
            assert params is not None
            self.run = {
                "id": params[0],
                "project_id": params[1],
                "dataset_version_id": params[2],
                "dataset_display_name": params[7],
                "dataset_deleted_at": None,
                "status": "queued",
                "progress": 0,
                "phase": "queued",
                "provider": params[3],
                "model": params[4],
                "parameters": unwrap_json(params[5]),
                "error_code": None,
                "error_message": None,
                "diagnostics": {},
                "started_at": None,
                "completed_at": None,
                "cancel_requested_at": None,
                "deleted_at": None,
                "created_at": NOW,
                "updated_at": NOW,
            }
            return FakeResult([self.run])
        if normalized.startswith("INSERT INTO audit_events"):
            return FakeResult()
        if normalized.startswith("UPDATE analysis_runs SET status = 'running'"):
            assert self.run is not None
            self.run["status"] = "running"
            assert params is not None
            self.run["progress"] = params[0]
            self.run["phase"] = "embedding"
            self.run["started_at"] = NOW
            return FakeResult(
                [
                    {
                        "id": self.run["id"],
                        "project_id": self.run["project_id"],
                        "dataset_version_id": self.run["dataset_version_id"],
                        "provider": self.run["provider"],
                        "model": self.run["model"],
                    }
                ]
            )
        if normalized.startswith("SELECT status FROM analysis_runs WHERE id ="):
            assert self.run is not None
            return FakeResult([{"status": self.run["status"]}])
        if normalized.startswith("INSERT INTO embeddings"):
            assert params is not None
            self.embeddings.append(
                {
                    "id": params[0],
                    "project_id": params[1],
                    "analysis_run_id": params[2],
                    "dataset_version_id": params[3],
                    "source_object_id": params[4],
                    "text_variant": params[5],
                    "model": params[6],
                    "dimensions": params[7],
                    "embedding": params[8],
                    "metadata": unwrap_json(params[9]),
                }
            )
            return FakeResult()
        if normalized.startswith("UPDATE analysis_runs SET status = CASE"):
            assert params is not None
            assert self.run is not None
            if self.run["status"] == "cancelling":
                self.run["status"] = "cancelled"
                self.run["phase"] = "cancelled"
            else:
                self.run["status"] = "completed"
                self.run["progress"] = 100
                self.run["phase"] = "completed"
            self.run["completed_at"] = NOW
            existing_diagnostics = self.run["diagnostics"]
            next_diagnostics = unwrap_json(params[0])
            assert isinstance(existing_diagnostics, dict)
            assert isinstance(next_diagnostics, dict)
            self.run["diagnostics"] = {**existing_diagnostics, **next_diagnostics}
            return FakeResult()
        if normalized.startswith("UPDATE analysis_runs SET progress ="):
            assert params is not None
            assert self.run is not None
            progress = int(str(params[0]))
            if (
                self.run["status"] == "running"
                and int(str(self.run["progress"])) < progress
            ):
                self.run["progress"] = progress
                self.progress_updates.append(progress)
            return FakeResult()
        if normalized.startswith("UPDATE analysis_runs SET status = 'failed',"):
            assert params is not None
            assert self.run is not None
            self.run["status"] = "failed"
            self.run["phase"] = "failed"
            if len(params) == 2:
                self.run["error_code"] = "UNEXPECTED_ERROR"
                self.run["error_message"] = "AnalysisQueueFull"
                self.run["diagnostics"] = unwrap_json(params[0])
            else:
                self.run["error_code"] = params[0]
                self.run["error_message"] = params[1]
                self.run["diagnostics"] = unwrap_json(params[2])
            return FakeResult()
        if normalized.startswith("SELECT r.id, r.project_id, r.dataset_version_id"):
            assert self.run is not None
            return FakeResult([self.run])
        raise AssertionError(f"unexpected query: {normalized}")


def unwrap_json(value: object) -> object:
    return getattr(value, "obj", value)


class FakeEmbeddingProvider:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, list[str]]] = []

    def embed_texts(
        self, provider: str, model: str, texts: list[str]
    ) -> list[list[float]]:
        self.calls.append((provider, model, texts))
        return [[0.1, 0.2, 0.3] for _ in texts]


def test_long_unicode_text_is_split_without_exceeding_byte_bound() -> None:
    message = "ä" * 10_355 + "x"

    chunks = list(analysis_service_module._text_chunks(message))

    assert len(chunks) > 1
    assert "".join(chunks) == message
    assert max(len(chunk.encode("utf-8")) for chunk in chunks) <= 1024


def test_message_embeddings_pool_chunks_and_bound_provider_batches() -> None:
    class RecordingProvider:
        def __init__(self) -> None:
            self.calls: list[list[str]] = []

        def embed_texts(
            self, provider: str, model: str, texts: list[str]
        ) -> list[list[float]]:
            assert provider == "ollama"
            assert model == "local-embed"
            self.calls.append(texts)
            return [
                [1.0, 0.0] if text.startswith("a") else [0.0, 1.0] for text in texts
            ]

    provider = RecordingProvider()
    long_message = ("a" * 1024) + " " + ("b" * 512)
    messages = [long_message, *["short"] * 64]

    embedded = analysis_service_module._message_embeddings(
        provider,  # type: ignore[arg-type]
        "ollama",
        "local-embed",
        messages,
    )

    assert [len(call) for call in provider.calls] == [64, 2]
    pooled, chunk_count, source_bytes, pooling = embedded[0]
    assert pooled == pytest.approx([0.8944271909999159, 0.4472135954999579])
    assert chunk_count == 2
    assert source_bytes == len(long_message.encode("utf-8"))
    assert pooling == "byte_weighted_mean_l2"
    assert embedded[1] == ([0.0, 1.0], 1, 5, "none")


def test_message_chunks_are_consumed_only_as_provider_batches_need_them(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class RecordingProvider:
        def __init__(self) -> None:
            self.batch_sizes: list[int] = []

        def embed_texts(
            self, provider: str, model: str, texts: list[str]
        ) -> list[list[float]]:
            self.batch_sizes.append(len(texts))
            return [[1.0, 0.0] for _ in texts]

    provider = RecordingProvider()

    def observed_chunks(_: str) -> Iterator[str]:
        for index in range(129):
            if index == 64:
                assert provider.batch_sizes == [64]
            if index == 128:
                assert provider.batch_sizes == [64, 64]
            yield "a"

    monkeypatch.setattr(analysis_service_module, "_text_chunks", observed_chunks)

    embedded = analysis_service_module._message_embeddings(
        provider,  # type: ignore[arg-type]
        "ollama",
        "local-embed",
        ["synthetic"],
    )

    assert provider.batch_sizes == [64, 64, 1]
    assert embedded == [([1.0, 0.0], 129, 9, "byte_weighted_mean_l2")]


def test_start_indexing_returns_queued_before_batched_embedding_completes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_connection = AnalysisConnection()
    monkeypatch.setattr(
        analysis_service_module,
        "open_database_connection",
        lambda _: fake_connection,
    )

    embedding_provider = FakeEmbeddingProvider()
    service = AnalysisService(provider_service=embedding_provider)  # type: ignore[arg-type]
    run = service.start_run(
        PROJECT_ID,
        IndexingRunInput(
            dataset_version_id=DATASET_ID,
            provider="vllm",
            model="local-embed",
            parameters={},
        ),
        actor_user_id=ACTOR_ID,
    )

    assert run.status == "queued"
    assert run.progress == 0
    assert run.phase == "queued"
    assert run.provider == "vllm"
    assert run.model == "local-embed"
    assert run.parameters == {}
    assert fake_connection.embeddings == []

    service.execute_queued_run(run.id)
    completed = service.get_run(PROJECT_ID, run.id)

    assert completed is not None
    assert completed.status == "completed"
    assert completed.progress == 100
    assert completed.diagnostics["embeddings_written"] == 2
    assert completed.diagnostics["message_embeddings"] == 1
    assert completed.diagnostics["answer_embeddings"] == 1
    assert len(fake_connection.embeddings) == 2
    assert {item["text_variant"] for item in fake_connection.embeddings} == {
        "message",
        "answer",
    }
    assert all(item["dimensions"] == 3 for item in fake_connection.embeddings)
    assert (
        fake_connection.embeddings[0]["embedding"]
        == "[0.10000000000000001,0.20000000000000001,0.29999999999999999]"
    )
    assert all(
        item["source_object_id"] == PAIR_ID for item in fake_connection.embeddings
    )
    assert embedding_provider.calls == [
        ("vllm", "local-embed", ["How do I reset it?"]),
        ("vllm", "local-embed", ["Use the reset flow."]),
    ]


def test_long_message_run_persists_pooled_embeddings_with_provenance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    message = "ä" * 20_711
    fake_connection = AnalysisConnection(message=message)
    monkeypatch.setattr(
        analysis_service_module,
        "open_database_connection",
        lambda _: fake_connection,
    )
    embedding_provider = FakeEmbeddingProvider()
    service = AnalysisService(provider_service=embedding_provider)  # type: ignore[arg-type]
    run = service.start_run(
        PROJECT_ID,
        IndexingRunInput(
            dataset_version_id=DATASET_ID,
            provider="vllm",
            model="local-embed",
            parameters={},
        ),
        actor_user_id=ACTOR_ID,
    )

    service.execute_queued_run(run.id)
    completed = service.get_run(PROJECT_ID, run.id)

    assert completed is not None
    assert completed.status == "completed"
    assert len(fake_connection.embeddings) == 2
    message_embedding = next(
        item for item in fake_connection.embeddings if item["text_variant"] == "message"
    )
    metadata = message_embedding["metadata"]
    assert isinstance(metadata, dict)
    assert metadata["source_chunk_count"] == 41
    assert metadata["source_bytes"] == len(message.encode("utf-8"))
    assert metadata["pooling"] == "byte_weighted_mean_l2"
    assert completed.diagnostics["chunked_texts"] == 1
    assert completed.diagnostics["chunks_embedded"] == 42
    assert (
        max(
            len(text.encode("utf-8"))
            for _, _, batch in embedding_provider.calls
            for text in batch
        )
        <= 1024
    )


def test_provider_failure_persists_safe_actionable_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FailingProvider:
        def embed_texts(
            self, provider: str, model: str, texts: list[str]
        ) -> list[list[float]]:
            raise ProviderError("embedding provider is temporarily unavailable")

    fake_connection = AnalysisConnection()
    monkeypatch.setattr(
        analysis_service_module,
        "open_database_connection",
        lambda _: fake_connection,
    )
    service = AnalysisService(provider_service=FailingProvider())  # type: ignore[arg-type]
    run = service.start_run(
        PROJECT_ID,
        IndexingRunInput(
            dataset_version_id=DATASET_ID,
            provider="vllm",
            model="local-embed",
            parameters={},
        ),
        actor_user_id=ACTOR_ID,
    )

    service.execute_queued_run(run.id)
    failed = service.get_run(PROJECT_ID, run.id)

    assert failed is not None
    assert failed.status == "failed"
    assert failed.progress == 5
    assert failed.error_message == "embedding provider is temporarily unavailable"
    assert failed.error_code == "INDEXING_MODEL_UNAVAILABLE"
    assert failed.diagnostics["failure_type"] == "ProviderError"
    assert fake_connection.embeddings == []


def test_chunked_message_provider_batches_publish_monotone_confirmed_progress(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_connection = AnalysisConnection(message="a" * (1024 * 193))
    monkeypatch.setattr(
        analysis_service_module,
        "open_database_connection",
        lambda _: fake_connection,
    )
    service = AnalysisService(
        provider_service=FakeEmbeddingProvider(),  # type: ignore[arg-type]
    )
    run = service.start_run(
        PROJECT_ID,
        IndexingRunInput(
            dataset_version_id=DATASET_ID,
            provider="vllm",
            model="local-embed",
            parameters={},
        ),
        actor_user_id=ACTOR_ID,
    )

    service.execute_queued_run(run.id)
    completed = service.get_run(PROJECT_ID, run.id)

    assert fake_connection.progress_updates == [23, 41, 59, 77, 95]
    assert fake_connection.server_cursor_events == [
        ("open", f"indexing_count_{run.id.hex}"),
        ("close", f"indexing_count_{run.id.hex}"),
        ("open", f"indexing_embed_{run.id.hex}"),
        ("close", f"indexing_embed_{run.id.hex}"),
    ]
    assert fake_connection.active_server_cursor is None
    assert completed is not None
    assert completed.status == "completed"
    assert completed.progress == 100


def test_later_chunked_message_provider_batch_failure_preserves_progress(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class LaterFailingProvider(FakeEmbeddingProvider):
        def embed_texts(
            self, provider: str, model: str, texts: list[str]
        ) -> list[list[float]]:
            if len(self.calls) == 2:
                raise ProviderError("embedding provider is temporarily unavailable")
            return super().embed_texts(provider, model, texts)

    fake_connection = AnalysisConnection(message="a" * (1024 * 193))
    monkeypatch.setattr(
        analysis_service_module,
        "open_database_connection",
        lambda _: fake_connection,
    )
    service = AnalysisService(
        provider_service=LaterFailingProvider(),  # type: ignore[arg-type]
    )
    run = service.start_run(
        PROJECT_ID,
        IndexingRunInput(
            dataset_version_id=DATASET_ID,
            provider="vllm",
            model="local-embed",
            parameters={},
        ),
        actor_user_id=ACTOR_ID,
    )

    service.execute_queued_run(run.id)
    failed = service.get_run(PROJECT_ID, run.id)

    assert fake_connection.progress_updates == [23, 41]
    assert failed is not None
    assert failed.status == "failed"
    assert failed.progress == 41
    assert failed.error_message == "embedding provider is temporarily unavailable"


def test_start_indexing_rejects_removed_profile_parameters_before_insert(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_connection = AnalysisConnection()
    monkeypatch.setattr(
        analysis_service_module,
        "open_database_connection",
        lambda _: fake_connection,
    )

    with pytest.raises(
        analysis_service_module.AnalysisError,
        match="profile",
    ):
        AnalysisService().start_run(
            PROJECT_ID,
            IndexingRunInput(
                dataset_version_id=DATASET_ID,
                provider="vllm",
                model="local-embed",
                parameters={"analysis_profile_id": "legacy"},
            ),
            actor_user_id=ACTOR_ID,
        )

    assert fake_connection.run is None


def test_start_indexing_rejects_any_indexing_parameters_before_insert(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_connection = AnalysisConnection()
    monkeypatch.setattr(
        analysis_service_module,
        "open_database_connection",
        lambda _: fake_connection,
    )

    with pytest.raises(
        analysis_service_module.AnalysisError,
        match="parameters",
    ) as error:
        AnalysisService().start_run(
            PROJECT_ID,
            IndexingRunInput(
                dataset_version_id=DATASET_ID,
                provider="vllm",
                model="local-embed",
                parameters={"algorithm_settings": {"algorithm": "agglomerative"}},
            ),
            actor_user_id=ACTOR_ID,
        )

    assert error.value.status_code == 422
    assert fake_connection.run is None


def test_execute_queued_run_finalizes_late_cancellation_as_cancelled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_connection = AnalysisConnection()
    monkeypatch.setattr(
        analysis_service_module,
        "open_database_connection",
        lambda _: fake_connection,
    )
    service = AnalysisService(provider_service=FakeEmbeddingProvider())  # type: ignore[arg-type]
    original_insert = service._insert_embedding

    def request_cancel_after_embeddings(*args: object, **kwargs: object) -> None:
        original_insert(*args, **kwargs)  # type: ignore[arg-type]
        if len(fake_connection.embeddings) == 2:
            assert fake_connection.run is not None
            fake_connection.run["status"] = "cancelling"

    monkeypatch.setattr(service, "_insert_embedding", request_cancel_after_embeddings)
    run = service.start_run(
        PROJECT_ID,
        IndexingRunInput(
            dataset_version_id=DATASET_ID,
            provider="vllm",
            model="local-embed",
            parameters={},
        ),
        actor_user_id=ACTOR_ID,
    )

    service.execute_queued_run(run.id)
    cancelled = service.get_run(PROJECT_ID, run.id)

    assert cancelled is not None
    assert cancelled.status == "cancelled"
    assert cancelled.phase == "cancelled"
    assert cancelled.progress == 95
    assert cancelled.diagnostics["embeddings_written"] == 2


def test_openai_indexing_requires_explicit_cloud_confirmation_before_insert(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_connection = AnalysisConnection(
        provider="openai",
        api_key_set=True,
        endpoint_url=None,
    )
    monkeypatch.setattr(
        analysis_service_module,
        "open_database_connection",
        lambda _: fake_connection,
    )

    with pytest.raises(
        analysis_service_module.AnalysisError,
        match="cloud confirmation",
    ) as error:
        AnalysisService().start_run(
            PROJECT_ID,
            IndexingRunInput(
                dataset_version_id=DATASET_ID,
                provider="openai",
                model="local-embed",
                parameters={},
            ),
            actor_user_id=ACTOR_ID,
        )

    assert error.value.code == "INDEXING_CLOUD_CONFIRMATION_REQUIRED"
    assert fake_connection.run is None


def test_background_runner_caps_concurrency_and_releases_queue_capacity() -> None:
    runner = analysis_service_module.LocalBackgroundJobRunner(
        worker_count=1,
        queue_capacity=1,
    )
    first_started = Event()
    release_first = Event()
    first_finished = Event()
    second_started = Event()
    third_finished = Event()

    def first_task() -> None:
        first_started.set()
        assert release_first.wait(timeout=2)
        first_finished.set()

    runner.submit(first_task)
    assert first_started.wait(timeout=2)
    runner.submit(second_started.set)

    with pytest.raises(AnalysisQueueFull, match="capacity is exhausted"):
        runner.submit(lambda: None)

    assert second_started.is_set() is False
    release_first.set()
    assert first_finished.wait(timeout=2)
    assert second_started.wait(timeout=2)

    runner.submit(third_finished.set)
    assert third_finished.wait(timeout=2)


def test_enqueue_overload_marks_queued_run_failed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FullRunner:
        def submit(self, _: object) -> None:
            raise AnalysisQueueFull("local indexing capacity is exhausted; retry later")

    fake_connection = AnalysisConnection()
    monkeypatch.setattr(
        analysis_service_module,
        "open_database_connection",
        lambda _: fake_connection,
    )
    service = AnalysisService(
        job_runner=FullRunner(),  # type: ignore[arg-type]
        provider_service=FakeEmbeddingProvider(),  # type: ignore[arg-type]
    )
    run = service.start_run(
        PROJECT_ID,
        IndexingRunInput(
            dataset_version_id=DATASET_ID,
            provider="vllm",
            model="local-embed",
            parameters={},
        ),
        actor_user_id=ACTOR_ID,
    )

    with pytest.raises(AnalysisQueueFull):
        service.enqueue_run(run.id)

    assert fake_connection.run is not None
    assert fake_connection.run["status"] == "failed"
    assert fake_connection.run["progress"] == 0
    assert fake_connection.run["diagnostics"] == {"failure_type": "AnalysisQueueFull"}
