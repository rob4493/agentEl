import json
from urllib.request import Request, build_opener, HTTPRedirectHandler, ProxyHandler
from http.client import HTTPException
import re
from urllib.error import URLError
from urllib.parse import urlparse
from ..emailSchemas import EmailRequest, ValidationRequest, SemanticReport
from .modelProvider import ProviderUnavailable
from ..agentInstructions import sharedEmailInstructions, semanticReviewInstructions

class LocalOnlyRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # urllib's required override name is an external-interface naming exception.
        # Never let a local endpoint redirect email data toward an external service.
        raise ProviderUnavailable("Ollama redirects are disabled.")

def openLocalRequest(httpRequest: Request):
    # System proxy settings must never forward local draft inference elsewhere.
    return build_opener(ProxyHandler({}), LocalOnlyRedirectHandler()).open(httpRequest, timeout=60)

def readEmailResponse(result: object) -> str:
    if not isinstance(result, dict) or result.get("error") or result.get("done") is not True:
        raise ValueError("Incomplete or invalid Ollama response")
    message = result.get("message")
    if not isinstance(message, dict) or message.get("role") != "assistant" or message.get("tool_calls"):
        raise ValueError("Expected an assistant email response")
    if result.get("done_reason") not in (None, "stop"):
        raise ValueError("Model response was truncated or interrupted")
    draft = message.get("content")
    if not isinstance(draft, str) or not draft.strip() or len(draft) > 20000:
        raise ValueError("Invalid email content")
    # Consume content only, never message.thinking. Reject leaked tags rather than guessing how to strip them.
    if re.search(r"</?think(?:ing)?\b", draft, re.I):
        raise ValueError("Reasoning tags found in email content")
    return draft.strip()

class OllamaProvider:
    name = "ollama"
    isMock = False

    def __init__(self, baseUrl: str, model: str):
        # Remote inference is intentionally excluded from this local MVP.
        parsed = urlparse(baseUrl)
        if parsed.scheme != "http" or parsed.hostname not in {"localhost", "127.0.0.1", "::1"} or parsed.username or parsed.password:
            raise ValueError("Ollama URL must use HTTP on a loopback host.")
        self.baseUrl = baseUrl.rstrip("/")
        self.model = model

    def improve(self, request: EmailRequest) -> str:
        return self.chat(sharedEmailInstructions, request.model_dump_json())

    def reviewMeaning(self, request: ValidationRequest) -> SemanticReport:
        try:
            content = self.chat(semanticReviewInstructions, request.model_dump_json(), SemanticReport.model_json_schema())
            return SemanticReport.model_validate_json(content)
        except ValueError as error:
            raise ProviderUnavailable("Local semantic review returned invalid structured output.") from error

    def chat(self, instructions: str, requestData: str, responseFormat: dict | None = None) -> str:
        payload = {"model": self.model, "stream": False, "think": False, "messages": [{"role": "system", "content": instructions}, {"role": "user", "content": requestData}]}
        if responseFormat is not None:
            payload["format"] = responseFormat
        try:
            httpRequest = Request(self.baseUrl + "/api/chat", data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
            with openLocalRequest(httpRequest) as response:
                responseBody = response.read(200001)
            if len(responseBody) > 200000:
                raise ValueError("Model response exceeded size limit")
            return readEmailResponse(json.loads(responseBody))
        except (URLError, TimeoutError, ValueError, HTTPException, OSError) as error:
            raise ProviderUnavailable("Local Ollama unavailable or returned invalid output. No fallback was used.") from error
