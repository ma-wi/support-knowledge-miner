from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

import pytest

from backend.providers import (
    ProviderConfiguration,
    ProviderError,
    ProviderService,
)
from backend.providers import service as provider_service_module


class FakeResponse:
    status = 200

    def __init__(self, payload: Any) -> None:
        self._payload = payload

    def read(self, _: int) -> bytes:
        return json.dumps(self._payload).encode("utf-8")


class FakeHTTPSConnection:
    last_headers: dict[str, str] | None = None

    def __init__(self, host: str, timeout: float) -> None:
        self.host = host
        self.timeout = timeout

    def request(self, method: str, path: str, *, headers: dict[str, str]) -> None:
        assert method == "GET"
        assert path == "/v1/models"
        FakeHTTPSConnection.last_headers = headers

    def getresponse(self) -> FakeResponse:
        return FakeResponse(
            {
                "data": [
                    {"id": "gpt-4.1-mini"},
                    {"id": "text-embedding-3-small"},
                    {"id": "text-embedding-3-large"},
                ]
            }
        )

    def close(self) -> None:
        return None


class FakeAllModelHTTPSConnection(FakeHTTPSConnection):
    def getresponse(self) -> FakeResponse:
        return FakeResponse({"data": [{"id": "gpt-4.1-mini"}, {"id": "o3-mini"}]})


class FakeAlternativePayloadHTTPSConnection(FakeHTTPSConnection):
    def getresponse(self) -> FakeResponse:
        return FakeResponse(
            {
                "models": [
                    "gpt-4.1-mini",
                    {"model": "text-embedding-3-small"},
                ]
            }
        )


class FakeEmptyModelHTTPSConnection(FakeHTTPSConnection):
    def getresponse(self) -> FakeResponse:
        return FakeResponse({"data": []})


class FakeOllamaHTTPConnection:
    last_path: str | None = None
    last_body: bytes | None = None

    def __init__(self, host: str, timeout: float) -> None:
        self.host = host
        self.timeout = timeout
        self.method = "GET"

    def request(
        self,
        method: str,
        path: str,
        body: bytes | None = None,
        *,
        headers: dict[str, str],
    ) -> None:
        self.method = method
        FakeOllamaHTTPConnection.last_path = path
        FakeOllamaHTTPConnection.last_body = body

    def getresponse(self) -> FakeResponse:
        if self.method == "POST":
            return FakeResponse({"status": "success"})
        return FakeResponse(
            {
                "models": [
                    {"name": "nomic-embed-text:latest"},
                    {"model": "mxbai-embed-large"},
                ]
            }
        )

    def close(self) -> None:
        return None


class FakeEmbeddingHTTPConnection:
    payload: Any = {"embeddings": [[0.1, 0.2], [0.3, 0.4]]}
    last_path: str | None = None
    last_body: dict[str, object] | None = None

    def __init__(self, host: str, timeout: float) -> None:
        self.host = host
        self.timeout = timeout

    def request(
        self,
        method: str,
        path: str,
        body: bytes | None = None,
        *,
        headers: dict[str, str],
    ) -> None:
        assert method == "POST"
        assert body is not None
        FakeEmbeddingHTTPConnection.last_path = path
        FakeEmbeddingHTTPConnection.last_body = json.loads(body.decode("utf-8"))

    def getresponse(self) -> FakeResponse:
        return FakeResponse(self.payload)

    def close(self) -> None:
        return None


class RecordingEmbeddingResponse:
    def __init__(self, *, status: int, payload: Any, raw: bytes | None) -> None:
        self.status = status
        self._payload = payload
        self._raw = raw

    def read(self, _: int) -> bytes:
        if self._raw is not None:
            return self._raw
        return json.dumps(self._payload).encode("utf-8")


class RecordingEmbeddingConnection:
    status = 200
    payload: Any = {}
    raw: bytes | None = None
    request_error: Exception | None = None
    requests: list[dict[str, object]] = []

    def __init__(self, host: str, timeout: float) -> None:
        self.host = host
        self.timeout = timeout

    def request(
        self,
        method: str,
        path: str,
        body: bytes | None = None,
        *,
        headers: dict[str, str],
    ) -> None:
        if self.request_error is not None:
            raise self.request_error
        self.requests.append(
            {
                "host": self.host,
                "timeout": self.timeout,
                "method": method,
                "path": path,
                "body": json.loads(body.decode("utf-8")) if body else None,
                "headers": headers,
            }
        )

    def getresponse(self) -> RecordingEmbeddingResponse:
        return RecordingEmbeddingResponse(
            status=self.status,
            payload=self.payload,
            raw=self.raw,
        )

    def close(self) -> None:
        return None

    @classmethod
    def reset(
        cls,
        *,
        payload: Any,
        status: int = 200,
        raw: bytes | None = None,
        request_error: Exception | None = None,
    ) -> None:
        cls.payload = payload
        cls.status = status
        cls.raw = raw
        cls.request_error = request_error
        cls.requests = []


def provider_configuration(
    provider: str,
    *,
    endpoint_url: str | None,
    model: str = "local-embed",
) -> ProviderConfiguration:
    return ProviderConfiguration(
        provider=provider,
        endpoint_url=endpoint_url,
        manual_models=[model],
        llm_models=[model] if provider in {"openai", "ollama"} else [],
        api_key_set=provider == "openai",
        updated_at=datetime(2026, 7, 26, tzinfo=UTC),
    )


def test_openai_check_prefers_embedding_models(monkeypatch: Any) -> None:
    monkeypatch.setattr(provider_service_module, "HTTPSConnection", FakeHTTPSConnection)

    result = ProviderService()._check_openai("sk-test", ["manual-fallback"])

    assert result.ok is True
    assert result.models == ["text-embedding-3-small", "text-embedding-3-large"]
    assert result.message == "OpenAI embedding models discovered"
    assert FakeHTTPSConnection.last_headers == {
        "Accept": "application/json",
        "Authorization": "Bearer sk-test",
    }


def test_openai_check_falls_back_to_all_models_when_no_embeddings(
    monkeypatch: Any,
) -> None:
    monkeypatch.setattr(
        provider_service_module, "HTTPSConnection", FakeAllModelHTTPSConnection
    )

    result = ProviderService()._check_openai("sk-test", ["manual-fallback"])

    assert result.ok is True
    assert result.models == ["gpt-4.1-mini", "o3-mini"]
    assert result.message == "OpenAI models discovered"


def test_openai_check_accepts_alternative_model_payload_shapes(
    monkeypatch: Any,
) -> None:
    monkeypatch.setattr(
        provider_service_module,
        "HTTPSConnection",
        FakeAlternativePayloadHTTPSConnection,
    )

    result = ProviderService()._check_openai("sk-test", [])

    assert result.ok is True
    assert result.models == ["text-embedding-3-small"]
    assert result.message == "OpenAI embedding models discovered"


def test_openai_check_reports_empty_model_discovery(monkeypatch: Any) -> None:
    monkeypatch.setattr(
        provider_service_module, "HTTPSConnection", FakeEmptyModelHTTPSConnection
    )

    result = ProviderService()._check_openai("sk-test", [])

    assert result.ok is False
    assert result.models == []
    assert result.message == "OpenAI model discovery returned no model ids"


def test_openai_model_discovery_explicitly_filters_invalid_ids() -> None:
    service = ProviderService()

    models = service._models_from_openai_model_items(
        [
            {"id": " "},
            {"id": "valid-model"},
            {"model": "x" * (provider_service_module.MAX_MODEL_LENGTH + 1)},
        ]
    )

    assert models == ["valid-model"]


def test_ollama_check_discovers_local_models(monkeypatch: Any) -> None:
    monkeypatch.setattr(
        provider_service_module, "HTTPConnection", FakeOllamaHTTPConnection
    )

    result = ProviderService()._check_ollama(
        "http://localhost:11434", ["manual-fallback"]
    )

    assert result.ok is True
    assert result.models == ["nomic-embed-text:latest", "mxbai-embed-large"]
    assert result.message == "Ollama models discovered"
    assert FakeOllamaHTTPConnection.last_path == "/api/tags"


def test_ollama_model_discovery_explicitly_filters_invalid_ids() -> None:
    service = ProviderService()

    models = service._models_from_ollama_tags_payload(
        {
            "models": [
                {"name": " "},
                {"name": "valid-model"},
                {"model": "x" * (provider_service_module.MAX_MODEL_LENGTH + 1)},
            ]
        }
    )

    assert models == ["valid-model"]


@pytest.mark.parametrize(
    "endpoint_url",
    [
        "http://example.com:11434",
        "http://localhost.example.com:11434",
        "http://attacker@example.com:11434",
    ],
)
def test_ollama_check_rejects_non_local_endpoint_before_connecting(
    monkeypatch: Any,
    endpoint_url: str,
) -> None:
    def fail_connection(*args: object, **kwargs: object) -> None:
        raise AssertionError("connection must not be attempted")

    monkeypatch.setattr(provider_service_module, "HTTPConnection", fail_connection)

    with pytest.raises(ProviderError, match="allowed local endpoint"):
        ProviderService()._check_ollama(endpoint_url, [])


def test_ollama_pull_uses_local_pull_endpoint(monkeypatch: Any) -> None:
    monkeypatch.setattr(
        provider_service_module, "HTTPConnection", FakeOllamaHTTPConnection
    )

    ProviderService()._pull_ollama_model("http://localhost:11434", "nomic-embed-text")

    assert FakeOllamaHTTPConnection.last_path == "/api/pull"
    assert FakeOllamaHTTPConnection.last_body is not None
    assert json.loads(FakeOllamaHTTPConnection.last_body.decode("utf-8")) == {
        "model": "nomic-embed-text",
        "stream": False,
    }


def test_ollama_embeddings_are_batched_and_validated(monkeypatch: Any) -> None:
    monkeypatch.setattr(
        provider_service_module, "HTTPConnection", FakeEmbeddingHTTPConnection
    )
    service = ProviderService()
    monkeypatch.setattr(
        service,
        "_get_configuration",
        lambda _: ProviderConfiguration(
            provider="ollama",
            endpoint_url="http://localhost:11434/",
            manual_models=["local-embed"],
            llm_models=[],
            api_key_set=False,
            updated_at=datetime(2026, 7, 26, tzinfo=UTC),
        ),
    )

    vectors = service.embed_texts(
        "ollama", "local-embed", ["first message", "second message"]
    )

    assert vectors == [[0.1, 0.2], [0.3, 0.4]]
    assert FakeEmbeddingHTTPConnection.last_path == "/api/embed"
    assert FakeEmbeddingHTTPConnection.last_body == {
        "model": "local-embed",
        "input": ["first message", "second message"],
        "keep_alive": "5m",
    }


def test_embedding_response_rejects_non_finite_values() -> None:
    with pytest.raises(ProviderError, match="non-finite"):
        ProviderService()._validate_embeddings([[0.1, float("nan")]], 1)


def test_openai_embeddings_use_fixed_host_and_restore_index_mapping(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    RecordingEmbeddingConnection.reset(
        payload={
            "data": [
                {"index": 1, "embedding": [0.3, 0.4]},
                {"index": 0, "embedding": [0.1, 0.2]},
            ]
        }
    )
    monkeypatch.setattr(
        provider_service_module, "HTTPSConnection", RecordingEmbeddingConnection
    )
    monkeypatch.setattr(
        provider_service_module,
        "decrypt_provider_secret",
        lambda _: "sk-adapter-test",
    )
    service = ProviderService()
    monkeypatch.setattr(
        service,
        "_get_configuration",
        lambda _: provider_configuration("openai", endpoint_url=None),
    )
    monkeypatch.setattr(service, "_get_api_key_secret", lambda _: "encrypted")

    vectors = service.embed_texts(
        "openai", "local-embed", ["first source", "second source"]
    )

    assert vectors == [[0.1, 0.2], [0.3, 0.4]]
    assert RecordingEmbeddingConnection.requests == [
        {
            "host": "api.openai.com",
            "timeout": provider_service_module.PROVIDER_EMBEDDING_TIMEOUT_SECONDS,
            "method": "POST",
            "path": "/v1/embeddings",
            "body": {
                "model": "local-embed",
                "input": ["first source", "second source"],
            },
            "headers": {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": "Bearer sk-adapter-test",
            },
        }
    ]


def test_vllm_embeddings_use_allowed_local_v1_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    RecordingEmbeddingConnection.reset(
        payload={"data": [{"index": 0, "embedding": [0.1, 0.2]}]}
    )
    monkeypatch.setattr(
        provider_service_module, "HTTPConnection", RecordingEmbeddingConnection
    )
    service = ProviderService()
    monkeypatch.setattr(
        service,
        "_get_configuration",
        lambda _: provider_configuration(
            "vllm", endpoint_url="http://vllm-cpu:8000/v1"
        ),
    )

    assert service.embed_texts("vllm", "local-embed", ["source"]) == [[0.1, 0.2]]
    assert RecordingEmbeddingConnection.requests[0]["host"] == "vllm-cpu:8000"
    assert RecordingEmbeddingConnection.requests[0]["path"] == "/v1/embeddings"


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({"embeddings": [[0.1, 0.2]]}, "wrong number"),
        ({"embeddings": [[0.1], [0.2, 0.3]]}, "inconsistent dimensions"),
        ({"embeddings": [[0.1, "bad"], [0.2, 0.3]]}, "invalid vector"),
        ({"embeddings": [[0.1, float("nan")], [0.2, 0.3]]}, "non-finite"),
    ],
)
def test_ollama_embedding_adapter_rejects_hostile_responses(
    monkeypatch: pytest.MonkeyPatch,
    payload: Any,
    message: str,
) -> None:
    RecordingEmbeddingConnection.reset(payload=payload)
    monkeypatch.setattr(
        provider_service_module, "HTTPConnection", RecordingEmbeddingConnection
    )
    service = ProviderService()
    monkeypatch.setattr(
        service,
        "_get_configuration",
        lambda _: provider_configuration(
            "ollama", endpoint_url="http://localhost:11434"
        ),
    )

    with pytest.raises(ProviderError, match=message):
        service.embed_texts("ollama", "local-embed", ["first", "second"])


def test_embedding_redirect_is_rejected_without_cloud_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    RecordingEmbeddingConnection.reset(payload={}, status=302)
    monkeypatch.setattr(
        provider_service_module, "HTTPConnection", RecordingEmbeddingConnection
    )
    monkeypatch.setattr(
        provider_service_module,
        "HTTPSConnection",
        lambda *_args, **_kwargs: pytest.fail("cloud fallback must not be attempted"),
    )
    service = ProviderService()
    monkeypatch.setattr(
        service,
        "_get_configuration",
        lambda _: provider_configuration(
            "vllm", endpoint_url="http://localhost:8000/v1"
        ),
    )

    with pytest.raises(ProviderError, match="HTTP 302"):
        service.embed_texts("vllm", "local-embed", ["source"])

    assert len(RecordingEmbeddingConnection.requests) == 1


def test_embedding_context_error_is_actionable_without_echoing_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    RecordingEmbeddingConnection.reset(
        payload={
            "error": (
                "the input length exceeds the context length: sensitive source text"
            )
        },
        status=400,
    )
    monkeypatch.setattr(
        provider_service_module, "HTTPConnection", RecordingEmbeddingConnection
    )
    service = ProviderService()
    monkeypatch.setattr(
        service,
        "_get_configuration",
        lambda _: provider_configuration(
            "ollama", endpoint_url="http://localhost:11434"
        ),
    )

    with pytest.raises(
        ProviderError,
        match="embedding input exceeds the model context window",
    ) as error:
        service.embed_texts("ollama", "local-embed", ["source"])

    assert "sensitive source text" not in str(error.value)


def test_embedding_response_size_limit_is_enforced(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    RecordingEmbeddingConnection.reset(
        payload={},
        raw=b"x" * (provider_service_module.MAX_EMBEDDING_RESPONSE_BYTES + 1),
    )
    monkeypatch.setattr(
        provider_service_module, "HTTPConnection", RecordingEmbeddingConnection
    )
    service = ProviderService()
    monkeypatch.setattr(
        service,
        "_get_configuration",
        lambda _: provider_configuration(
            "ollama", endpoint_url="http://localhost:11434"
        ),
    )

    with pytest.raises(ProviderError, match="response is too large"):
        service.embed_texts("ollama", "local-embed", ["source"])


def test_embedding_timeout_fails_safely_without_source_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    RecordingEmbeddingConnection.reset(
        payload={},
        request_error=TimeoutError("sensitive source text"),
    )
    monkeypatch.setattr(
        provider_service_module, "HTTPConnection", RecordingEmbeddingConnection
    )
    service = ProviderService()
    monkeypatch.setattr(
        service,
        "_get_configuration",
        lambda _: provider_configuration("vllm", endpoint_url="http://localhost:8000"),
    )

    with pytest.raises(ProviderError) as error:
        service.embed_texts("vllm", "local-embed", ["sensitive source text"])

    assert "TimeoutError" in str(error.value)
    assert "sensitive source text" not in str(error.value)


def test_embedding_rejects_non_local_vllm_endpoint_before_connecting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        provider_service_module,
        "HTTPConnection",
        lambda *_args, **_kwargs: pytest.fail("connection must not be attempted"),
    )
    service = ProviderService()
    monkeypatch.setattr(
        service,
        "_get_configuration",
        lambda _: provider_configuration(
            "vllm", endpoint_url="http://example.com:8000"
        ),
    )

    with pytest.raises(ProviderError, match="allowed local endpoint"):
        service.embed_texts("vllm", "local-embed", ["source"])
