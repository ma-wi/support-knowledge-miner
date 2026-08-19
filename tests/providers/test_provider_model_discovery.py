from __future__ import annotations

import json
from datetime import UTC, datetime
import logging
from typing import Any
from uuid import UUID

import pytest

from backend.providers import (
    ProviderConfiguration,
    ProviderError,
    ProviderService,
)
from backend.providers import service as provider_service_module

PROVIDER_ID = UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")


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


class RecordingLLMConnection:
    status = 200
    payload: Any = {"output_text": '{"title":"Reset"}'}
    raw: bytes | None = None
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
    ) -> None:
        cls.payload = payload
        cls.status = status
        cls.raw = raw
        cls.requests = []


def provider_configuration(
    provider: str,
    *,
    endpoint_url: str | None,
    model: str = "local-embed",
) -> ProviderConfiguration:
    return ProviderConfiguration(
        id=PROVIDER_ID,
        provider=provider,
        display_name="OpenAI" if provider == "openai" else "Ollama",
        endpoint_url=endpoint_url,
        available_models=[model],
        manual_models=[model],
        llm_models=[model] if provider in {"openai", "ollama"} else [],
        api_key_set=provider == "openai",
        updated_at=datetime(2026, 7, 26, tzinfo=UTC),
    )


def test_openai_check_returns_embedding_and_llm_models(monkeypatch: Any) -> None:
    monkeypatch.setattr(provider_service_module, "HTTPSConnection", FakeHTTPSConnection)

    result = ProviderService()._check_openai(
        provider_configuration("openai", endpoint_url=None, model="manual-fallback"),
        "sk-test",
    )

    assert result.ok is True
    assert result.models == [
        "text-embedding-3-small",
        "text-embedding-3-large",
        "gpt-4.1-mini",
    ]
    assert result.embedding_models == [
        "text-embedding-3-small",
        "text-embedding-3-large",
    ]
    assert result.llm_models == ["gpt-4.1-mini"]
    assert result.message == "OpenAI models discovered"
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

    result = ProviderService()._check_openai(
        provider_configuration("openai", endpoint_url=None, model="manual-fallback"),
        "sk-test",
    )

    assert result.ok is True
    assert result.models == ["gpt-4.1-mini"]
    assert result.embedding_models == []
    assert result.llm_models == ["gpt-4.1-mini"]
    assert result.message == "OpenAI models discovered"


def test_openai_check_accepts_alternative_model_payload_shapes(
    monkeypatch: Any,
) -> None:
    monkeypatch.setattr(
        provider_service_module,
        "HTTPSConnection",
        FakeAlternativePayloadHTTPSConnection,
    )

    result = ProviderService()._check_openai(
        ProviderConfiguration(
            id=PROVIDER_ID,
            provider="openai",
            display_name="OpenAI",
            endpoint_url=None,
            available_models=[],
            manual_models=[],
            llm_models=[],
            api_key_set=True,
            updated_at=datetime(2026, 7, 26, tzinfo=UTC),
        ),
        "sk-test",
    )

    assert result.ok is True
    assert result.models == ["text-embedding-3-small", "gpt-4.1-mini"]
    assert result.embedding_models == ["text-embedding-3-small"]
    assert result.llm_models == ["gpt-4.1-mini"]
    assert result.message == "OpenAI models discovered"


def test_openai_check_reports_empty_model_discovery(monkeypatch: Any) -> None:
    monkeypatch.setattr(
        provider_service_module, "HTTPSConnection", FakeEmptyModelHTTPSConnection
    )

    result = ProviderService()._check_openai(
        ProviderConfiguration(
            id=PROVIDER_ID,
            provider="openai",
            display_name="OpenAI",
            endpoint_url=None,
            available_models=[],
            manual_models=[],
            llm_models=[],
            api_key_set=True,
            updated_at=datetime(2026, 7, 26, tzinfo=UTC),
        ),
        "sk-test",
    )

    assert result.ok is False
    assert result.models == []
    assert result.embedding_models == []
    assert result.llm_models == []
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


def test_openai_configuration_filters_purpose_allow_lists_from_database_row() -> None:
    configuration = provider_service_module._configuration_from_row(
        {
            "id": PROVIDER_ID,
            "provider": "openai",
            "display_name": "OpenAI",
            "endpoint_url": None,
            "available_models": ["text-embedding-3-small", "gpt-4.1-mini"],
            "manual_models": ["text-embedding-3-small", "gpt-4.1-mini"],
            "llm_models": ["text-embedding-3-small", "gpt-4.1-mini"],
            "api_key_secret": "fernet:redacted",
            "updated_at": datetime(2026, 7, 26, tzinfo=UTC),
        }
    )

    assert configuration.manual_models == ["text-embedding-3-small"]
    assert configuration.llm_models == ["gpt-4.1-mini"]


def test_ollama_check_discovers_local_models(monkeypatch: Any) -> None:
    monkeypatch.setattr(
        provider_service_module, "HTTPConnection", FakeOllamaHTTPConnection
    )

    result = ProviderService()._check_ollama(
        provider_configuration(
            "ollama", endpoint_url="http://localhost:11434", model="manual-fallback"
        ),
        "http://localhost:11434",
    )

    assert result.ok is True
    assert result.models == ["nomic-embed-text:latest", "mxbai-embed-large"]
    assert result.embedding_models == ["nomic-embed-text:latest", "mxbai-embed-large"]
    assert result.llm_models == ["nomic-embed-text:latest", "mxbai-embed-large"]
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
        ProviderService()._check_ollama(
            provider_configuration("ollama", endpoint_url=endpoint_url),
            endpoint_url,
        )


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
            id=PROVIDER_ID,
            provider="ollama",
            display_name="Ollama",
            endpoint_url="http://localhost:11434/",
            available_models=["local-embed"],
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


def test_vllm_embedding_provider_is_rejected_before_connecting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        provider_service_module,
        "HTTPConnection",
        lambda *_args, **_kwargs: pytest.fail("connection must not be attempted"),
    )

    with pytest.raises(ProviderError, match="provider must be openai or ollama"):
        ProviderService().embed_texts("vllm", "local-embed", ["source"])


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
            "ollama", endpoint_url="http://localhost:11434"
        ),
    )

    with pytest.raises(ProviderError, match="HTTP 302"):
        service.embed_texts("ollama", "local-embed", ["source"])

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
        lambda _: provider_configuration(
            "ollama", endpoint_url="http://localhost:11434"
        ),
    )

    with pytest.raises(ProviderError) as error:
        service.embed_texts("ollama", "local-embed", ["sensitive source text"])

    assert "TimeoutError" in str(error.value)
    assert "sensitive source text" not in str(error.value)


def test_embedding_rejects_non_local_ollama_endpoint_before_connecting(
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
            "ollama", endpoint_url="http://example.com:11434"
        ),
    )

    with pytest.raises(ProviderError, match="allowed local endpoint"):
        service.embed_texts("ollama", "local-embed", ["source"])


def test_openai_responses_text_is_parsed_from_output_text() -> None:
    text = ProviderService()._openai_response_text(
        {
            "id": "resp-1",
            "output_text": (
                '{"title":"Reset","category":"Account",'
                '"question":"How?","answer":"Use link","rationale":null}'
            ),
        }
    )

    assert '"title":"Reset"' in text


def test_openai_llm_request_uses_structured_outputs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    RecordingLLMConnection.reset(
        payload={
            "output_text": (
                '{"title":"Reset","category":"Account",'
                '"question":"How?","answer":"Use link","rationale":null}'
            )
        }
    )
    monkeypatch.setattr(
        provider_service_module, "HTTPSConnection", RecordingLLMConnection
    )
    service = ProviderService()
    monkeypatch.setattr(
        service,
        "_get_configuration_by_ref",
        lambda _ref: provider_configuration(
            "openai", endpoint_url=None, model="gpt-4.1-mini"
        ),
    )
    monkeypatch.setattr(service, "_get_api_key_secret", lambda _id: "encrypted")
    monkeypatch.setattr(
        provider_service_module, "decrypt_provider_secret", lambda _: "sk-test"
    )

    text = service.generate_text("openai", "gpt-4.1-mini", "Prompt")

    assert '"title":"Reset"' in text
    assert len(RecordingLLMConnection.requests) == 1
    request = RecordingLLMConnection.requests[0]
    assert request["timeout"] == provider_service_module.PROVIDER_LLM_TIMEOUT_SECONDS
    body = request["body"]
    assert isinstance(body, dict)
    assert body["store"] is False
    assert (
        body["max_output_tokens"] == provider_service_module.LLM_SUMMARY_OUTPUT_TOKENS
    )
    text_config = body["text"]
    assert isinstance(text_config, dict)
    format_config = text_config["format"]
    assert isinstance(format_config, dict)
    assert format_config["type"] == "json_schema"
    assert format_config["strict"] is True
    assert format_config["name"] == "cluster_summary"


def test_openai_llm_request_accepts_bounded_custom_schema(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    RecordingLLMConnection.reset(payload={"output_text": '{"items":[]}'})
    monkeypatch.setattr(
        provider_service_module, "HTTPSConnection", RecordingLLMConnection
    )
    service = ProviderService()
    monkeypatch.setattr(
        service,
        "_get_configuration_by_ref",
        lambda _ref: provider_configuration(
            "openai", endpoint_url=None, model="gpt-4.1-mini"
        ),
    )
    monkeypatch.setattr(service, "_get_api_key_secret", lambda _id: "encrypted")
    monkeypatch.setattr(
        provider_service_module, "decrypt_provider_secret", lambda _: "sk-test"
    )
    schema: dict[str, object] = {
        "type": "object",
        "properties": {"items": {"type": "array"}},
        "required": ["items"],
        "additionalProperties": False,
    }

    text = service.generate_text(
        "openai",
        "gpt-4.1-mini",
        "Prompt",
        instructions="Return the requested object.",
        response_schema=schema,
        schema_name="cluster_taxonomy",
        max_output_tokens=1234,
    )

    assert text == '{"items":[]}'
    body = RecordingLLMConnection.requests[0]["body"]
    assert isinstance(body, dict)
    assert body["instructions"] == "Return the requested object."
    assert body["max_output_tokens"] == 1234
    text_config = body["text"]
    assert isinstance(text_config, dict)
    format_config = text_config["format"]
    assert isinstance(format_config, dict)
    assert format_config["name"] == "cluster_taxonomy"
    assert format_config["schema"] == schema


def test_openai_llm_request_accepts_taxonomy_prompt_and_output_hard_caps(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    RecordingLLMConnection.reset(payload={"output_text": '{"items":[]}'})
    monkeypatch.setattr(
        provider_service_module, "HTTPSConnection", RecordingLLMConnection
    )
    service = ProviderService()
    monkeypatch.setattr(
        service,
        "_get_configuration_by_ref",
        lambda _ref: provider_configuration(
            "openai", endpoint_url=None, model="gpt-4.1-mini"
        ),
    )
    monkeypatch.setattr(service, "_get_api_key_secret", lambda _id: "encrypted")
    monkeypatch.setattr(
        provider_service_module, "decrypt_provider_secret", lambda _: "sk-test"
    )
    prompt = "x" * 500_000

    text = service.generate_text(
        "openai",
        "gpt-4.1-mini",
        prompt,
        max_prompt_characters=500_000,
        max_output_tokens=128_000,
        max_output_characters=1_000_000,
    )

    assert text == '{"items":[]}'
    body = RecordingLLMConnection.requests[0]["body"]
    assert isinstance(body, dict)
    assert body["input"] == prompt
    assert body["max_output_tokens"] == 128_000


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"max_prompt_characters": 500_001}, "prompt budget"),
        ({"max_output_tokens": 128_001}, "output token budget"),
        ({"max_output_characters": 1_000_001}, "output character budget"),
    ],
)
def test_llm_request_rejects_taxonomy_budgets_above_hard_caps(
    kwargs: dict[str, Any],
    message: str,
) -> None:
    with pytest.raises(ProviderError, match=message):
        ProviderService().generate_text(
            "openai",
            "gpt-4.1-mini",
            "Prompt",
            **kwargs,
        )


def test_openai_llm_raw_response_accepts_exact_byte_cap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base = json.dumps({"output_text": "ok"}).encode("utf-8")
    raw = base + b" " * (provider_service_module.MAX_LLM_RESPONSE_BYTES - len(base))
    RecordingLLMConnection.reset(payload={}, raw=raw)
    monkeypatch.setattr(
        provider_service_module, "HTTPSConnection", RecordingLLMConnection
    )
    service = ProviderService()
    monkeypatch.setattr(
        service,
        "_get_configuration_by_ref",
        lambda _ref: provider_configuration(
            "openai", endpoint_url=None, model="gpt-4.1-mini"
        ),
    )
    monkeypatch.setattr(service, "_get_api_key_secret", lambda _id: "encrypted")
    monkeypatch.setattr(
        provider_service_module, "decrypt_provider_secret", lambda _: "sk-test"
    )

    assert service.generate_text("openai", "gpt-4.1-mini", "Prompt") == "ok"


def test_openai_llm_raw_response_rejects_above_byte_cap_without_echo(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sensitive = b"SECRET_PROVIDER_PAYLOAD"
    RecordingLLMConnection.reset(
        payload={},
        raw=sensitive + b"x" * (provider_service_module.MAX_LLM_RESPONSE_BYTES + 1),
    )
    monkeypatch.setattr(
        provider_service_module, "HTTPSConnection", RecordingLLMConnection
    )
    service = ProviderService()
    monkeypatch.setattr(
        service,
        "_get_configuration_by_ref",
        lambda _ref: provider_configuration(
            "openai", endpoint_url=None, model="gpt-4.1-mini"
        ),
    )
    monkeypatch.setattr(service, "_get_api_key_secret", lambda _id: "encrypted")
    monkeypatch.setattr(
        provider_service_module, "decrypt_provider_secret", lambda _: "sk-test"
    )

    with pytest.raises(ProviderError, match="response is too large") as error:
        service.generate_text("openai", "gpt-4.1-mini", "Prompt")

    assert sensitive.decode() not in str(error.value)


def test_openai_llm_text_rejects_above_character_cap_without_echo(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sensitive = "SECRET_OUTPUT_TEXT"
    RecordingLLMConnection.reset(payload={"output_text": sensitive + "x" * 1_000_000})
    monkeypatch.setattr(
        provider_service_module, "HTTPSConnection", RecordingLLMConnection
    )
    service = ProviderService()
    monkeypatch.setattr(
        service,
        "_get_configuration_by_ref",
        lambda _ref: provider_configuration(
            "openai", endpoint_url=None, model="gpt-4.1-mini"
        ),
    )
    monkeypatch.setattr(service, "_get_api_key_secret", lambda _id: "encrypted")
    monkeypatch.setattr(
        provider_service_module, "decrypt_provider_secret", lambda _: "sk-test"
    )

    with pytest.raises(ProviderError, match="response is too large") as error:
        service.generate_text(
            "openai",
            "gpt-4.1-mini",
            "Prompt",
            max_output_characters=1_000_000,
        )

    assert sensitive not in str(error.value)


def test_ollama_llm_request_uses_json_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    RecordingLLMConnection.reset(
        payload={
            "response": (
                '{"title":"Reset","category":"Account",'
                '"question":"How?","answer":"Use link","rationale":null}'
            )
        }
    )
    monkeypatch.setattr(
        provider_service_module, "HTTPConnection", RecordingLLMConnection
    )
    service = ProviderService()
    monkeypatch.setattr(
        service,
        "_get_configuration_by_ref",
        lambda _ref: provider_configuration(
            "ollama", endpoint_url="http://localhost:11434", model="qwen2.5:7b"
        ),
    )

    text = service.generate_text("ollama", "qwen2.5:7b", "Prompt")

    assert '"title":"Reset"' in text
    assert len(RecordingLLMConnection.requests) == 1
    request = RecordingLLMConnection.requests[0]
    assert request["path"] == "/api/generate"
    assert request["timeout"] == provider_service_module.PROVIDER_LLM_TIMEOUT_SECONDS
    body = request["body"]
    assert isinstance(body, dict)
    assert body["format"] == "json"
    assert body["keep_alive"] == "5m"
    options = body["options"]
    assert isinstance(options, dict)
    assert options["temperature"] == 0
    assert options["num_predict"] == 700


def test_openai_incomplete_response_reports_safe_reason() -> None:
    with pytest.raises(ProviderError, match="max_output_tokens"):
        ProviderService()._openai_response_text(
            {
                "id": "resp-1",
                "status": "incomplete",
                "incomplete_details": {"reason": "max_output_tokens"},
                "output": [],
            }
        )


def test_openai_incomplete_partial_response_logs_metadata_without_content(
    caplog: pytest.LogCaptureFixture,
) -> None:
    sensitive_fragment = "VERTRAULICHER UNVOLLSTÄNDIGER PROVIDERTEXT"
    caplog.set_level(
        logging.INFO,
        logger=provider_service_module.LLM_DIAGNOSTIC_LOGGER.name,
    )

    with pytest.raises(ProviderError, match="max_output_tokens") as error:
        ProviderService()._openai_response_text(
            {
                "id": "resp-1",
                "status": "incomplete",
                "incomplete_details": {"reason": "max_output_tokens"},
                "output_text": sensitive_fragment,
                "output": [{"type": "message"}],
            },
            diagnostic_correlation_id=PROVIDER_ID,
        )

    assert "llm_provider_response_incomplete" in caplog.text
    assert f"correlation_id={PROVIDER_ID}" in caplog.text
    assert "provider=openai" in caplog.text
    assert "reason=max_output_tokens" in caplog.text
    assert f"output_text_characters={len(sensitive_fragment)}" in caplog.text
    assert "output_items=1" in caplog.text
    assert sensitive_fragment not in caplog.text
    assert sensitive_fragment not in str(error.value)


def test_openai_incomplete_response_redacts_untrusted_reason_from_log_and_error(
    caplog: pytest.LogCaptureFixture,
) -> None:
    malicious_reason = "SECRET_REASON\nFORGED_LOG_ENTRY"
    caplog.set_level(
        logging.INFO,
        logger=provider_service_module.LLM_DIAGNOSTIC_LOGGER.name,
    )

    with pytest.raises(ProviderError) as error:
        ProviderService()._openai_response_text(
            {
                "id": "resp-1",
                "status": "incomplete",
                "incomplete_details": {"reason": malicious_reason},
                "output": [],
            }
        )

    assert str(error.value) == "LLM provider returned an incomplete response"
    assert "reason=unspecified" in caplog.text
    assert malicious_reason not in caplog.text
    assert "FORGED_LOG_ENTRY" not in caplog.text


def test_llm_diagnostic_correlation_rejects_log_injection_before_provider_call(
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    malicious_correlation = "secret\nFORGED_LOG_ENTRY"
    caplog.set_level(
        logging.INFO,
        logger=provider_service_module.LLM_DIAGNOSTIC_LOGGER.name,
    )
    service = ProviderService()
    monkeypatch.setattr(
        service,
        "ensure_text_generation_model",
        lambda *_args, **_kwargs: pytest.fail("provider access must not be attempted"),
    )

    with pytest.raises(ProviderError) as error:
        service.generate_text(
            "openai",
            "gpt-5.4-mini",
            "Prompt",
            diagnostic_correlation_id=malicious_correlation,  # type: ignore[arg-type]
        )

    assert str(error.value) == "LLM diagnostic correlation is invalid"
    assert malicious_correlation not in caplog.text
    assert "FORGED_LOG_ENTRY" not in caplog.text

    with pytest.raises(ProviderError) as parser_error:
        service._openai_response_text(
            {
                "status": "incomplete",
                "incomplete_details": {"reason": "max_output_tokens"},
                "output": [],
            },
            diagnostic_correlation_id=malicious_correlation,  # type: ignore[arg-type]
        )

    assert str(parser_error.value) == "LLM diagnostic correlation is invalid"
    assert malicious_correlation not in caplog.text
    assert "FORGED_LOG_ENTRY" not in caplog.text
