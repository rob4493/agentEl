import re
from .emailSchemas import Finding, ValidationResult, AudienceContext, Clarification
from .factExtractor import extractFacts
from .contentReview import reviewContent
from .changeExplainer import explainChanges

def validateMeaning(originalDraft: str, improvedDraft: str, audience: AudienceContext | None = None, clarifications: list[Clarification] | None = None) -> ValidationResult:
    findings = []
    def addFinding(category: str, explanation: str, evidence: str = "", output: str = ""):
        # Keep relevant evidence only; repeating a full 20,000-character draft per warning bloats responses.
        findings.append(Finding(category=category, severity="warning", explanation=explanation, sourceEvidence=evidence, generatedText=output))
    # Compare numeric tokens as strings so versions, row counts and dates cannot silently change.
    numericPattern = r"\b\d+(?:[.,]\d+)*\b"
    sourceNumbers = set(re.findall(numericPattern, originalDraft))
    outputNumbers = set(re.findall(numericPattern, improvedDraft))
    contextText = "\n".join([answer.answer for answer in clarifications or []] + ([audience.requiredDetails] if audience else []))
    contextNumbers = set(re.findall(numericPattern, contextText))
    if (sourceNumbers | contextNumbers) - outputNumbers or outputNumbers - sourceNumbers - contextNumbers:
        missing = sorted((sourceNumbers | contextNumbers) - outputNumbers)
        added = sorted(outputNumbers - sourceNumbers - contextNumbers)
        addFinding("numericalChange", "Numbers, versions or date components changed.", missing[0] if missing else "", added[0] if added else "")
    months = r"January|February|March|April|May|June|July|August|September|October|November|December"
    datePattern = rf"\b(?:{months})\s+\d{{1,2}}(?:,?\s+\d{{4}})?\b"
    sourceDates = set(re.findall(datePattern, originalDraft, re.I))
    outputDates = set(re.findall(datePattern, improvedDraft, re.I))
    contextDates = set(re.findall(datePattern, contextText, re.I))
    if (sourceDates | contextDates) - outputDates or outputDates - sourceDates - contextDates:
        missingDates = sorted((sourceDates | contextDates) - outputDates)
        addedDates = sorted(outputDates - sourceDates - contextDates)
        addFinding("deadlineChange", "A written date was added, removed or changed.", missingDates[0] if missingDates else "", addedDates[0] if addedDates else "")
    # Deliberately conservative: paraphrases also trigger review, avoiding false semantic guarantees.
    for fact in extractFacts(originalDraft).facts:
        if fact.sourcePassage not in improvedDraft:
            addFinding("sourcePassageChanged", "An original passage is missing or reworded; verify all facts, uncertainty and actions.", fact.sourcePassage)
    sourcePassages = {fact.sourcePassage for fact in extractFacts(originalDraft).facts}
    for fact in extractFacts(improvedDraft).facts:
        if fact.sourcePassage not in sourcePassages:
            addFinding("unsupportedOrReworded", "New or rewritten passage needs source verification.", output=fact.sourcePassage)
    analysis = extractFacts(originalDraft, audience, clarifications)
    return ValidationResult(findings=reviewContent(analysis, improvedDraft) + findings, changeDetails=explainChanges(originalDraft, improvedDraft, analysis))
