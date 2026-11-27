import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from .betaSecurity import BetaSettings, BetaControl, BetaBoundary, GuardedOllamaProvider, betaContext
from .emailSchemas import EmailRequest, AnalysisResult, ImprovementResult, ValidationRequest, ValidationResult, SemanticReviewResult
from .meaningValidator import extractFacts, validateMeaning
from .agentWorkflow import improveEmail, ClarificationRequired
from .semanticReview import reviewMeaning
from .providers.mockProvider import MockProvider
from .providers.ollamaProvider import OllamaProvider
from .providers.modelProvider import ProviderUnavailable
from .readerAnalysis import ReaderRequest, ReaderResult, analyzeReader
from .composeAdaptation import ComposeRequest, ComposeResult, ComposeValidationRequest, adaptResponse, validateAdaptedResponse

def getProvider():
    providerName = os.getenv("COMMUNICATION_PROVIDER", "mock")
    if providerName == "mock":
        return MockProvider()
    if providerName == "ollama":
        control=betaContext.get()
        if control is not None:
            return GuardedOllamaProvider(os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434"), os.getenv("OLLAMA_MODEL", "qwen3.5:4b"),control)
        return OllamaProvider(os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434"), os.getenv("OLLAMA_MODEL", "qwen3.5:4b"))
    raise ValueError("Unsupported provider configuration")

def health():
    return {"status": "ok", "provider": os.getenv("COMMUNICATION_PROVIDER", "mock"), "modelConnection": "notChecked", "semanticValidation": "unavailable", "betaAccessVerified": betaContext.get() is not None}

def analyze(request: EmailRequest):
    try:
        return extractFacts(request.originalDraft, request.audience, request.clarifications)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

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

def validate(request: ValidationRequest):
    try:
        return validateMeaning(request.originalDraft, request.improvedDraft, request.audience, request.clarifications)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


def composeResponse(request: ComposeRequest):
    try:
        return adaptResponse(request,getProvider())
    except ClarificationRequired as error:
        raise HTTPException(status_code=409,detail={'code':'clarificationRequired','questions':[q.model_dump() for q in error.questions]}) from error
    except (ProviderUnavailable,ValueError) as error:
        raise HTTPException(status_code=503,detail=str(error)) from error


def validateComposeResponse(request: ComposeValidationRequest):
    return validateAdaptedResponse(request)

def semanticReview(request: ValidationRequest):
    try:
        provider = getProvider()
        return reviewMeaning(request, provider if isinstance(provider, OllamaProvider) else None)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error



def readerAnalysis(request: ReaderRequest):
    try:
        provider = getProvider()
        return analyzeReader(request, provider)
    except (ProviderUnavailable, ValueError) as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


def createApp(settings=None):
    settings=settings or BetaSettings.fromEnvironment()
    application=FastAPI(title='Ritmo',description='Human-centered communication with local inference and explicit human review.',version='0.1.0',
        docs_url=None if settings.enabled else '/docs',redoc_url=None if settings.enabled else '/redoc',openapi_url=None if settings.enabled else '/openapi.json')
    for path,handler,model,method in [
        ('/api/health',health,None,'GET'),('/api/analyze',analyze,AnalysisResult,'POST'),
        ('/api/improve',improve,ImprovementResult,'POST'),('/api/validate',validate,ValidationResult,'POST'),
        ('/api/adaptResponse',composeResponse,ComposeResult,'POST'),
        ('/api/adaptResponse/validate',validateComposeResponse,ValidationResult,'POST'),
        ('/api/review',semanticReview,SemanticReviewResult,'POST'),('/api/readerAnalysis',readerAnalysis,ReaderResult,'POST')]:
        application.add_api_route(path,handler,response_model=model,methods=[method])
    if settings.enabled:
        @application.exception_handler(RequestValidationError)
        async def invalidBetaRequest(request,error):
            # FastAPI's normal 422 includes input values; never echo private drafts in beta errors.
            return JSONResponse(status_code=422,content={'detail':'Request validation failed. Check field types and lengths.'})
        @application.exception_handler(HTTPException)
        async def betaHttpError(request,error):
            # Keep authenticated clarification questions (409) usable, but do
            # not echo internal Pydantic/provider error text in other failures.
            detail={422:'Request could not be processed. Check the submitted fields.',
                    503:'Local AI service is unavailable or busy. Try again later.'}.get(error.status_code,error.detail)
            return JSONResponse(status_code=error.status_code,content={'detail':detail},headers=error.headers)
        control=BetaControl(settings)
        application.state.betaControl=control
        application.add_middleware(BetaBoundary,control=control)
    # CORS is outermost so permitted preflights work without credentials, while
    # every real API request still crosses authentication/rate/body boundaries.
    application.add_middleware(CORSMiddleware,allow_origins=list(settings.origins),allow_methods=['GET','POST'],
        allow_headers=['Content-Type','Authorization'],allow_credentials=False,expose_headers=['Retry-After'])
    return application


app=createApp()
