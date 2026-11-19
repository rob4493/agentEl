from .contentReview import relatedPassage
from .emailSchemas import AnalysisResult, ChangeExplanation
from .factExtractor import extractFacts

def explainChanges(originalDraft: str, improvedDraft: str, analysis: AnalysisResult) -> list[ChangeExplanation]:
    changes = []
    if len(originalDraft.splitlines()) != len(improvedDraft.splitlines()):
        changes.append(ChangeExplanation(whatChanged="Paragraph or line structure changed.", whyHelpful="Grouping information may make it easier to scan. Confirm all details remain in the correct context.", sourceEvidence=originalDraft[:400], generatedEvidence=improvedDraft[:400]))
    candidates = [fact.sourcePassage for fact in extractFacts(improvedDraft).facts]
    # Explain a few observable high-impact differences, never the model's hidden reasoning.
    for fact in analysis.facts:
        if len(changes) >= 4:
            break
        if fact.sourcePassage not in improvedDraft and set(fact.categories) & {"accessibility", "risk", "importantLimitation", "unresolvedIssue", "requestedAction"}:
            match = relatedPassage(fact.sourcePassage, candidates)
            changes.append(ChangeExplanation(whatChanged="A decision-relevant passage was reworded or has no close match.", whyHelpful="A clearer expression can support shared understanding, but omission or changed meaning requires correction.", sourceEvidence=fact.sourcePassage, generatedEvidence=match))
    return changes
