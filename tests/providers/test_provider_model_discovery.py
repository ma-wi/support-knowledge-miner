from __future__ import annotations

import json
from typing import Any

import pytest

from backend.providers import ProviderError, ProviderService
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
