import re
from hashlib import sha256
from .emailSchemas import AmbiguityQuestion, Clarification, AudienceContext
from .textPassages import splitPassages

def findAmbiguities(originalDraft: str, audience: AudienceContext | None = None) -> list[AmbiguityQuestion]:
    questions = []
    # Limit interruptions to material action/deadline idioms, not general style preferences.
    for passage in splitPassages(originalDraft):
        candidates = []
        if re.search(r"\b(?:need to|please|let['’]s|(?:we|you) (?:should|will|must)|can (?:you|we)|could (?:you|we))\s+circle back\b", passage, re.I):
            candidates.append(("requestedAction", "Does ‘circle back’ mean a discussion, a written update, or another action? State the intended action."))
        if re.search(r"\b(?:by|before)\s+(?:EOD|end of (?:the )?day)\b", passage, re.I) and not re.search(r"\b\d{1,2}:\d{2}\b", passage):
            candidates.append(("deadline", "What exact date, time and time zone does end of day mean here?"))
        if re.search(r"\b(?:proceed|go ahead)\s+(?:if|unless)\s+(?:we hear|you hear|there are|anyone)\b", passage, re.I):
            candidates.append(("approval", "What explicit approval or decision is required before proceeding?"))
        for category, question in candidates:
            ambiguityId = "ambiguity" + sha256(f"{category}:{passage}".encode()).hexdigest()[:16]
            if not any(item.ambiguityId == ambiguityId for item in questions):
                questions.append(AmbiguityQuestion(ambiguityId=ambiguityId, category=category, sourcePassage=passage, question=question))
    objective = audience.communicationObjectives.strip() if audience else ""
    if re.search(r"\brequest (?:a )?decision\b", objective, re.I):
        # Only interrupt when no concrete decision request is identifiable; never invent its subject.
        decisionRequest = re.search(r"\b(?:please |could you |can you )?(?:decide|approve|choose|select)\s+(?!(?:it|this|that)\s*[.!?]?(?:$|\n))[^.!?\n]+|\b(?:decision|approval)\s+(?:on|about|whether|between)\s+\S+|\blet (?:me|us) know (?:whether|which)\s+\S+", originalDraft, re.I)
        if not decisionRequest:
            ambiguityId = "ambiguity" + sha256(f"decision:{objective}:{originalDraft}".encode()).hexdigest()[:16]
            questions.append(AmbiguityQuestion(ambiguityId=ambiguityId, category="requestedAction", sourcePassage=originalDraft, question="What decision are you asking the recipients to make?"))
    return questions

def unresolvedQuestions(originalDraft: str, clarifications: list[Clarification], audience: AudienceContext | None = None) -> list[AmbiguityQuestion]:
    questions = findAmbiguities(originalDraft, audience)
    for answer in clarifications:
        if not any(question.ambiguityId == answer.ambiguityId and question.sourcePassage == answer.sourcePassage for question in questions):
            raise ValueError("A clarification no longer matches this source. Analyze the current draft again.")
    if len({answer.ambiguityId for answer in clarifications}) != len(clarifications):
        raise ValueError("Provide one answer per clarification question.")
    return [question for question in questions if not any(answer.ambiguityId == question.ambiguityId for answer in clarifications)]
