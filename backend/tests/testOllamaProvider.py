import json
from io import BytesIO
from http.client import IncompleteRead
from unittest.mock import patch
import pytest
from app.emailSchemas import EmailRequest
from app.main import getProvider, app
from app.providers.ollamaProvider import OllamaProvider, readEmailResponse
from app.providers.modelProvider import ProviderUnavailable
from fastapi.testclient import TestClient

request = EmailRequest(originalDraft="Version 2.4.1 is on staging.", audience={"group":"Mixed team","technicalBackground":"Mixed proficiency","preferences":"Concise"})

def completedResponse(content="Improved email."):
    return {"done":True,"done_reason":"stop","message":{"role":"assistant","content":content}}

def testDefaultAndOverrideModel(monkeypatch):
    monkeypatch.setenv("COMMUNICATION_PROVIDER", "ollama")
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)
    assert getProvider().model == "qwen3.5:4b"
    monkeypatch.setenv("OLLAMA_MODEL", "anotherLocalModel")
    assert getProvider().model == "anotherLocalModel"

def testPayloadAndSeparateThinking():
    response = completedResponse()
    response["message"]["thinking"] = "Private reasoning must never become the email."
    with patch("app.providers.ollamaProvider.openLocalRequest", return_value=BytesIO(json.dumps(response).encode())) as openRequest:
        assert OllamaProvider("http://127.0.0.1:11434", "qwen3.5:4b").improve(request) == "Improved email."
    payload = json.loads(openRequest.call_args.args[0].data)
    assert payload["think"] is False
    assert payload["stream"] is False
    assert payload["model"] == "qwen3.5:4b"
    assert [message["role"] for message in payload["messages"]] == ["system","user"]
    assert json.loads(payload["messages"][1]["content"]) == request.model_dump()
    assert "exactly one" in payload["messages"][0]["content"]

@pytest.mark.parametrize("response", [None, [], {}, {"error":"model missing"}, {"done":False},
    {"done":True,"message":None}, {"done":True,"message":[]},
    {"done":True,"message":{"role":"user","content":"email"}},
    {"done":True,"message":{"role":"assistant","content":"email","tool_calls":[{}]}},
    completedResponse(""), completedResponse(" "), completedResponse(5), completedResponse("x"*20001),
    completedResponse("<think>reasoning</think>Email"), completedResponse("<THINKING>reasoning"),
    {**completedResponse(),"done_reason":"length"}, {**completedResponse(),"done_reason":[]}])
def testInvalidResponseBecomesProviderFailure(response):
    with patch("app.providers.ollamaProvider.openLocalRequest", return_value=BytesIO(json.dumps(response).encode())):
        with pytest.raises(ProviderUnavailable):
            OllamaProvider("http://127.0.0.1:11434", "qwen3.5:4b").improve(request)

@pytest.mark.parametrize("body", [b"not json", b"[]\n{}", b"\xff", b"x"*200001])
def testInvalidWireResponse(body):
    with patch("app.providers.ollamaProvider.openLocalRequest", return_value=BytesIO(body)):
        with pytest.raises(ProviderUnavailable):
            OllamaProvider("http://127.0.0.1:11434", "qwen3.5:4b").improve(request)

@pytest.mark.parametrize("failure", [TimeoutError("slow"), IncompleteRead(b"part")])
def testTransportFailure(failure, monkeypatch):
    monkeypatch.setenv("COMMUNICATION_PROVIDER", "ollama")
    with patch("app.providers.ollamaProvider.openLocalRequest", side_effect=failure):
        response = TestClient(app).post("/api/improve", json=request.model_dump())
    assert response.status_code == 503
    assert "No fallback" in response.json()["detail"]

def testThinkingOnlyIsNotEmail():
    with pytest.raises(ValueError):
        readEmailResponse({"done":True,"message":{"role":"assistant","thinking":"reasoning"}})
