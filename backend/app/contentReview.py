"""Conservative content rules, separate from optional model review. These are not semantic proofs."""
import re
from .emailSchemas import AnalysisResult, Finding
from .factExtractor import extractFacts

stopWords = set("a an the this that is are was were be been has have had to of for and or in on at by with it we i our you your please not no yet still remain remains unresolved resolved fixed improved may might will can could should must".split())
actionPatterns = {
    "discussion": r"\b(?:discuss|discussion|talk|revisit)\b",
    "writtenUpdate": r"\b(?:send|submit|provide|share|write|written)\b",
    "approval": r"\b(?:approve|approval|authorize|authorization)\b",
    "validation": r"\b(?:validate|validation|test|testing|check|review|verify|inspect|examine|assess)\b",
}
unresolvedPattern = r"unresolved|not (?:yet )?(?:resolved|fixed)|still|remain|persist|continue"
barrierPattern = r"\b(?:no|not|lacks?|without|cannot|inaccessible|stairs)\b"
uncertaintyPattern = r"\b(?:may|might|uncertain|unconfirmed|unknown|pending)\b|no confirmed|not confirmed|no .*date"

def topicTokens(passage: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", passage.lower().replace("step-free", "stepfree"))
    return {word.rstrip("s") for word in words if word not in stopWords and len(word) > 1}

class PassageMatcher:
    def __init__(self, candidates: list[str]):
        self.candidates = candidates
        self.tokenIndex: dict[str, list[int]] = {}
        for index, candidate in enumerate(candidates):
            for token in topicTokens(candidate):
                self.tokenIndex.setdefault(token, []).append(index)

    def match(self, source: str) -> str:
        tokens = topicTokens(source)
        scores: dict[int, int] = {}
        for token in tokens:
            for index in self.tokenIndex.get(token, []):
                scores[index] = scores.get(index, 0) + 1
        # Venue labels are decision-relevant; never borrow Venue A's access to qualify Venue B.
        entities = set(re.findall(r"\b(?:venue|option|site)\s+[a-z0-9]+\b", source.lower()))
        if entities:
            scores = {index:score for index,score in scores.items() if entities.issubset(set(re.findall(r"\b(?:venue|option|site)\s+[a-z0-9]+\b", self.candidates[index].lower())))}
        best = max(scores, default=None, key=lambda index: (scores[index], -index))
        return self.candidates[best] if best is not None and scores[best] >= min(2,len(tokens)) else ""

def relatedPassage(source: str, candidates: list[str]) -> str:
    return PassageMatcher(candidates).match(source)

def actionKinds(passage: str) -> set[str]:
    # A sender explicitly saying an update is NOT requested does not request that action.
    passage = re.sub(r"(?:a )?written update (?:is )?not (?:requested|required)", "", passage, flags=re.I)
    passage = re.sub(r"\bnot (?:to )?(?:send|submit|provide|share|write)\b[^.;]*", "", passage, flags=re.I)
    return {kind for kind, pattern in actionPatterns.items() if re.search(pattern, passage, re.I)}

def reviewContent(analysis: AnalysisResult, improvedDraft: str) -> list[Finding]:
    findings = []
    # A status header can qualify the following bullet. Keep the contiguous quotation as evidence.
    scoped = [match.group() for match in re.finditer(r"(?m)^[^\n]{1,160}:\n[ \t]*[-*][^\n]+", improvedDraft)]
    candidates = scoped + [fact.sourcePassage for fact in extractFacts(improvedDraft).facts]
    sourceFacts = analysis.facts + [fact for fact in analysis.confirmedContext if fact.evidenceSource == "clarification"]
    outputMatcher = PassageMatcher(candidates)
    sourceMatcher = PassageMatcher([fact.description for fact in sourceFacts])
    sourceText = "\n".join(fact.description for fact in sourceFacts)
    def addFinding(category: str, explanation: str, source: str, output: str = ""):
        findings.append(Finding(category=category, severity="warning", explanation=explanation, sourceEvidence=source, generatedText=output))
    for fact in sourceFacts:
        source = fact.description
        # Unclear idioms are not established actions. Review their explicit sender clarification instead.
        if fact.origin == "unknown":
            continue
        output = outputMatcher.match(source)
        categories = set(fact.categories)
        if not output and categories & {"accessibility", "risk", "importantLimitation", "unresolvedIssue", "requestedAction", "commitment", "deadline"}:
            addFinding("criticalOmission", "A decision-relevant passage has no close lexical match. It may be omitted or substantially reworded.", source)
        if "accessibility" in categories and re.search(barrierPattern, source, re.I) and not re.search(barrierPattern, output, re.I):
            addFinding("accessibilityChanged", "An accessibility barrier may have been omitted or reversed.", source, output)
        negativeResult = r"\bmiss(?:ed)?\b|shortfall|fell short|below target|did not meet"
        if re.search(negativeResult, source, re.I) and not re.search(negativeResult, output, re.I):
            addFinding("negativeInformationChanged", "A missed target or shortfall may have been removed or softened.", source, output)
        if "unresolvedIssue" in categories and not re.search(unresolvedPattern, output, re.I):
            addFinding("statusChanged", "An unresolved issue may be missing or represented as resolved.", source, output)
        if "resolvedIssue" in categories and (not re.search(r"\b(?:resolved|fixed|corrected)\b", output, re.I) or re.search(r"unresolved|not (?:yet )?(?:resolved|fixed)", output, re.I)):
            addFinding("statusChanged", "A resolved issue may have changed status or been omitted.", source, output)
        if re.search(r"\bimproved\b", source, re.I) and not re.search(r"\b(?:resolved|fixed)\b", source, re.I) and re.search(r"\b(?:resolved|fixed)\b", output, re.I):
            addFinding("statusChanged", "An improvement may have been strengthened into a resolution claim.", source, output)
        if "uncertainty" in categories and not re.search(uncertaintyPattern, output, re.I):
            addFinding("uncertaintyChanged", "Source uncertainty may have been omitted or converted into certainty.", source, output)
        if "requestedAction" in categories and actionKinds(source) and not actionKinds(source).issubset(actionKinds(output)):
            addFinding("changedAction", "A requested action may be omitted or changed in kind (for example, discussion versus written update).", source, output)
    for output in candidates:
        source = sourceMatcher.match(output)
        if re.search(r"\b(?:i|we)(?: will|['’]ll| have scheduled| have arranged| commit| guarantee)|\bmeeting (?:is|has been) (?:scheduled|arranged)", output, re.I):
            if not source or not re.search(r"\b(?:will|scheduled|arranged|commit|guarantee)\b|['’]ll", source, re.I):
                addFinding("unsupportedCommitment", "A sender commitment or confirmed arrangement may have been added without support.", source, output)
        praise = r"\b(?:excellent|outstanding|impressive|wonderful)\b|\bgreat (?:work|job)\b|\blove (?:the|your)\b"
        if re.search(praise, output, re.I) and not re.search(praise, sourceText, re.I):
            addFinding("inventedPraise", "A positive evaluation was added without an explicit source opinion.", "", output)
        accomplishment = r"\b(?:achieved|completed|delivered|doubled|exceeded|launched)\b"
        if re.search(accomplishment, output, re.I) and not re.search(r"\b(?:not|no|never)\b", output, re.I) and not re.search(accomplishment, source, re.I):
            addFinding("unsupportedAccomplishment", "An achievement may have been added without a matching source accomplishment.", source, output)
        explanation = r"\b(?:therefore|as a result|because|means|which will)\b"
        if re.search(explanation, output, re.I) and not re.search(explanation, source, re.I):
            addFinding("unsupportedExplanation", "A causal explanation or consequence may be new. Check that the source supports it.", source, output)
        attachment = r"\battach(?:ed|ments?)\b|\b(?:copy|data|report) (?:is |are )?included\b"
        if re.search(attachment, output, re.I) and not re.search(attachment, sourceText, re.I):
            addFinding("unsupportedAddition", "An attachment or included material was claimed without explicit source support.", "", output)
    return findings
