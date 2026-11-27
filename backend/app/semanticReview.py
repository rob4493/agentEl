from time import perf_counter as perfCounter
from .emailSchemas import Finding, ValidationRequest, SemanticReviewResult
from .providers.modelProvider import SemanticReviewer, ProviderUnavailable
from .ambiguityChecker import unresolvedQuestions

reviewLimitations = ["Optional review uses the same local model as generation; it is not independent and can repeat or miss errors.", "No findings does not establish semantic equivalence. Human review and explicit approval remain required."]

def reviewMeaning(request: ValidationRequest, reviewer: SemanticReviewer | None) -> SemanticReviewResult:
    if unresolvedQuestions(request.originalDraft, request.clarifications, request.audience):
        return SemanticReviewResult(reviewStatus="unavailable", limitations=reviewLimitations + ["Resolve the source ambiguities before requesting model review."])
    if reviewer is None:
        return SemanticReviewResult(reviewStatus="unavailable", limitations=reviewLimitations + ["Model review is unavailable in mock mode."])
    started = perfCounter()
    try:
        report = reviewer.reviewMeaning(request)
    except ProviderUnavailable:
        return SemanticReviewResult(reviewStatus="unavailable", elapsedMilliseconds=round((perfCounter()-started)*1000,3), limitations=reviewLimitations + ["Local model review failed, timed out or returned invalid output. Deterministic findings remain available; no fallback was used."])
    findings = []
    rejected = 0
    sourceTexts = [request.originalDraft] + [answer.answer for answer in request.clarifications]
    if request.audience:
        sourceTexts.append(request.audience.requiredDetails)
    for candidate in report.findings:
        # Model assertions do not become evidence. Verify every nonempty quote before displaying it.
        sourceValid = not candidate.sourceEvidence or any(candidate.sourceEvidence in text for text in sourceTexts)
        outputValid = not candidate.generatedText or candidate.generatedText in request.improvedDraft
        if not sourceValid or not outputValid or not (candidate.sourceEvidence or candidate.generatedText):
            rejected += 1
            continue
        findings.append(Finding(**candidate.model_dump(), reviewMethod="semanticModel", suggestedAction="Treat this model interpretation as unconfirmed. Compare quoted evidence and decide whether to correct the draft."))
    limitations = reviewLimitations + ([f"Discarded {rejected} model finding(s) with missing or nonmatching evidence; review coverage may be incomplete."] if rejected else [])
    # A nonempty report with no usable evidence is unavailable, not a clean review.
    status = "unavailable" if rejected and not findings else "completed"
    return SemanticReviewResult(reviewStatus=status, findings=findings, limitations=limitations, elapsedMilliseconds=round((perfCounter()-started)*1000,3))
