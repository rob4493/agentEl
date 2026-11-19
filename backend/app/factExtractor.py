import re
from hashlib import sha256
from .ambiguityChecker import findAmbiguities, unresolvedQuestions
from .emailSchemas import AnalysisResult, SourceFact, AudienceContext, Clarification
from .textPassages import splitPassages

categoryPatterns = [
    ("accessibility", r"step[- ]free|wheelchair|accessib|stairs|ramp|screen reader|captions"),
    ("unresolvedIssue", r"unresolved|not (?:yet )?(?:resolved|fixed)|outstanding issue|still .*timeouts?"),
    ("uncertainty", r"\bmay\b|\bmight\b|uncertain|unconfirmed|no confirmed|not confirmed|no .*date"),
    ("risk", r"\brisk\b|\bfail|\bmiss(?:ed)?\b|shortfall|fell short"),
    ("importantLimitation", r"\bnot\b|\bno\b|\blacks?\b|\bwithout\b|limitation|\bexceed|\bmissed\b|shortfall"),
    ("requestedAction", r"\bplease\b|\basked\b|\bneed to\b|\bmust\b|\brequired\b|feedback|action required"),
    ("commitment", r"\b(?:i|we) (?:will|commit|guarantee)\b|\b(?:i|we)['’]ll\b"),
    ("deadline", r"\b(?:by|before|deadline|due)\b"),
    ("date", r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\b|\b\d{4}-\d{2}-\d{2}\b"),
    ("accomplishment", r"\bimproved\b|\bcompleted\b|\bdeployed\b|\bdelivered\b|\bachieved\b"),
    ("technicalFact", r"\bversion\b|authentication|notifications|CSV|dataset|\bsoftware\b"),
]

def passageCategories(passage: str) -> list[str]:
    categories = [category for category, pattern in categoryPatterns if re.search(pattern, passage, re.I)]
    if re.search(r"\b(?:resolved|fixed|corrected)\b", passage, re.I) and not re.search(r"\b(?:unresolved|not (?:yet )?(?:resolved|fixed))\b", passage, re.I):
        categories.append("resolvedIssue")
    return categories or ["technicalFact"]

def extractFacts(originalDraft: str, audience: AudienceContext | None = None, clarifications: list[Clarification] | None = None) -> AnalysisResult:
    answers = clarifications or []
    unresolvedQuestions(originalDraft, answers)
    questions = findAmbiguities(originalDraft)
    passages = splitPassages(originalDraft)
    facts = []
    for index, passage in enumerate(passages):
        categories = passageCategories(passage)
        factId = "fact" + sha256(f"{index}:{passage}".encode()).hexdigest()[:12]
        # Exact quotations establish what the sender wrote, not whether the claim is true.
        origin = "unknown" if any(question.sourcePassage in passage or passage in question.sourcePassage for question in questions) else "explicitSource"
        facts.append(SourceFact(factId=factId, category=categories[0], categories=categories, description=passage, sourcePassage=passage, origin=origin))
    context = []
    for answer in answers:
        question = next(item for item in questions if item.ambiguityId == answer.ambiguityId)
        context.append(SourceFact(factId=answer.ambiguityId, category=question.category, categories=[question.category], description=answer.answer, sourcePassage=answer.sourcePassage, origin="userConfirmedContext", evidenceSource="clarification", extractionUncertainty="Sender supplied this clarification; verify its accuracy."))
    if audience and audience.requiredDetails.strip():
        context.append(SourceFact(factId="contextRequiredDetails", category="technicalFact", categories=["technicalFact"], description=audience.requiredDetails, sourcePassage=audience.requiredDetails, origin="userConfirmedContext", evidenceSource="audienceContext", extractionUncertainty="Sender-specified preservation guidance, not an inferred source claim."))
    return AnalysisResult(facts=facts, confirmedContext=context, ambiguities=unresolvedQuestions(originalDraft, answers), senderIntent=audience.communicationObjectives if audience else "Confirm the sender's goals before generation.", limitations=["Rule-based, overlapping categories are incomplete. Exact source evidence is verified; interpretations and factual truth are not. Clarifications are sender-provided context."])
