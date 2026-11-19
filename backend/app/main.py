import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .emailSchemas import EmailRequest, AnalysisResult, ImprovementResult, ValidationRequest, ValidationResult, SemanticReviewResult
from .meaningValidator import extractFacts, validateMeaning
from .agentWorkflow import improveEmail, ClarificationRequired
from .semanticReview import reviewMeaning
from .providers.mockProvider import MockProvider
from .providers.ollamaProvider import OllamaProvider
from .providers.modelProvider import ProviderUnavailable

app = FastAPI(title="Agent EL", description="Human-centered English email communication for mixed professional audiences, with local AI generation and explicit human review.", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], allow_methods=["GET", "POST"], allow_headers=["Content-Type"])

def getProvider():
    providerName = os.getenv("COMMUNICATION_PROVIDER", "mock")
    if providerName == "mock":
        return MockProvider()
    if providerName == "ollama":
        return OllamaProvider(os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434"), os.getenv("OLLAMA_MODEL", "qwen3.5:4b"))
    raise ValueError("Unsupported provider configuration")

@app.get("/api/health")
def health():
    return {"status": "ok", "provider": os.getenv("COMMUNICATION_PROVIDER", "mock"), "modelConnection": "notChecked", "semanticValidation": "unavailable"}

@app.post("/api/analyze", response_model=AnalysisResult)
def analyze(request: EmailRequest):
    try:
        return extractFacts(request.originalDraft, request.audience, request.clarifications)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

@app.post("/api/improve", response_model=ImprovementResult)
def improve(request: EmailRequest):
    try:
        provider = getProvider()
    except ValueError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    try:
        return improveEmail(request, provider)
    except ClarificationRequired as error:
        raise HTTPException(status_code=409, detail={"code":"clarificationRequired", "questions":[question.model_dump() for question in error.questions]}) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except ProviderUnavailable as error:
        raise HTTPException(status_code=503, detail=str(error)) from error

@app.post("/api/validate", response_model=ValidationResult)
def validate(request: ValidationRequest):
    try:
        return validateMeaning(request.originalDraft, request.improvedDraft, request.audience, request.clarifications)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

@app.post("/api/review", response_model=SemanticReviewResult)
def semanticReview(request: ValidationRequest):
    try:
        provider = getProvider()
        return reviewMeaning(request, provider if isinstance(provider, OllamaProvider) else None)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
