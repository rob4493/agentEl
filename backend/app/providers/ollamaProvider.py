import json
import logging
from time import perf_counter as perfCounter
from urllib.request import Request, build_opener, HTTPRedirectHandler, ProxyHandler
from http.client import HTTPException
import re
from urllib.error import URLError
from urllib.parse import urlparse
from ..emailSchemas import EmailRequest, ValidationRequest, SemanticReport
from .modelProvider import ProviderUnavailable
from ..agentInstructions import sharedEmailInstructions, semanticReviewInstructions

logger = logging.getLogger(__name__)

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

    def analyzeReader(self, request):
        from ..readerAnalysis import ReaderReport, readerModelSchema
        from ..readerReference import buildReaderInstructions
        try:
            content = self.chat(buildReaderInstructions(), request.model_dump_json(), readerModelSchema(), readerDiagnostics=True)
            schemaStarted = perfCounter()
            try:
                report = ReaderReport.model_validate_json(content)
            except ValueError:
                logger.debug('readerSchema %s', {'outcome':'invalid', 'elapsedMilliseconds':round((perfCounter()-schemaStarted)*1000,3)})
                raise
            logger.debug('readerSchema %s', {'outcome':'valid', 'elapsedMilliseconds':round((perfCounter()-schemaStarted)*1000,3)})
            return report
        except ValueError as error:
            raise ProviderUnavailable("Local writing analysis returned invalid structured output. No fallback was used.") from error

    def chat(self, instructions: str, requestData: str, responseFormat: dict | None = None, readerDiagnostics: bool = False) -> str:
        payload = {"model": self.model, "stream": False, "think": False, "messages": [{"role": "system", "content": instructions}, {"role": "user", "content": requestData}]}
        if responseFormat is not None:
            payload["format"] = responseFormat
        started = perfCounter()
        phase = 'openResponse'
        diagnostics = {'model':self.model, 'systemCharacters':len(instructions), 'userDataCharacters':len(requestData), 'schemaCharacters':len(json.dumps(responseFormat)) if responseFormat else 0, 'socketTimeoutSeconds':60}
        try:
            httpRequest = Request(self.baseUrl + "/api/chat", data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
            # With stream:false, waiting for response headers may include Ollama queue/load/
            # prompt evaluation/generation. This phase alone cannot attribute server compute time.
            with openLocalRequest(httpRequest) as response:
                diagnostics['headersMilliseconds'] = round((perfCounter()-started)*1000,3)
                phase = 'readResponse'
                responseBody = response.read(200001)
            diagnostics['bodyMilliseconds'] = round((perfCounter()-started)*1000,3)
            diagnostics['responseBytes'] = len(responseBody)
            if len(responseBody) > 200000:
                raise ValueError("Model response exceeded size limit")
            phase = 'decodeJson'
            result = json.loads(responseBody)
            phase = 'validateContent'
            content = readEmailResponse(result)
            # Allowlisted numeric counters only: no message, thinking, error body or excerpts.
            if readerDiagnostics:
                for key in ['prompt_eval_count','eval_count','total_duration','load_duration','prompt_eval_duration','eval_duration']:
                    value = result.get(key)
                    if isinstance(value, (int,float)) and not isinstance(value,bool):
                        diagnostics[key] = value
            phase = 'completed'
            return content
        except (URLError, TimeoutError, ValueError, HTTPException, OSError) as error:
            diagnostics['errorType'] = type(error).__name__
            reason = getattr(error, 'reason', None)
            if reason is not None:
                diagnostics['reasonType'] = type(reason).__name__
            raise ProviderUnavailable("Local Ollama unavailable or returned invalid output. No fallback was used.") from error
        finally:
            if readerDiagnostics:
                diagnostics['phase'] = phase
                diagnostics['elapsedMilliseconds'] = round((perfCounter()-started)*1000,3)
                logger.debug('readerTransport %s', diagnostics, extra={'readerTransportDiagnostics':diagnostics})
