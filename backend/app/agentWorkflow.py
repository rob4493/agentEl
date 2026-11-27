from .emailSchemas import EmailRequest, ImprovementResult
from .meaningValidator import extractFacts, validateMeaning
from .providers.modelProvider import ModelProvider
from .ambiguityChecker import unresolvedQuestions
from time import perf_counter as perfCounter

class ClarificationRequired(Exception):
    def __init__(self, questions):
        self.questions = questions

def improveEmail(request: EmailRequest, provider: ModelProvider) -> ImprovementResult:
    started = perfCounter()
    questions = unresolvedQuestions(request.originalDraft, request.clarifications, request.audience)
    if questions:
        raise ClarificationRequired(questions)
    analysis = extractFacts(request.originalDraft, request.audience, request.clarifications)
    extracted = perfCounter()
    improvedDraft = provider.improve(request)
    generated = perfCounter()
    validation = validateMeaning(request.originalDraft, improvedDraft, request.audience, request.clarifications)
    details = validation.changeDetails
    finished = perfCounter()
    return ImprovementResult(improvedDraft=improvedDraft, analysis=analysis, validation=validation, provider=provider.name, isMock=provider.isMock, changes=["Synthetic demonstration: paragraph spacing only; audience adaptation is not performed."] if provider.isMock else [detail.whatChanged for detail in details] or ["No selected structural or decision-relevant wording change was detected; review the full comparison."], changeDetails=details, processingMilliseconds={"preparation":round((extracted-started)*1000,3),"generation":round((generated-extracted)*1000,3),"deterministicReview":round((finished-generated)*1000,3)})
