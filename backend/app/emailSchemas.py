from typing import Literal
from pydantic import BaseModel, Field

class AudienceContext(BaseModel):
    group: str = Field(min_length=1, max_length=500)
    technicalBackground: str = Field(default="Mixed technical and nontechnical", max_length=1000)
    preferences: str = Field(default="Clear and professional", max_length=1000)
    communicationObjectives: str = Field(default="Make the message clear while preserving meaning", max_length=1000)
    requiredDetails: str = Field(default="", max_length=2000)

class Clarification(BaseModel):
    ambiguityId: str = Field(max_length=80)
    sourcePassage: str = Field(min_length=1, max_length=20000)
    answer: str = Field(min_length=1, max_length=1000, pattern=r"\S")

class AmbiguityQuestion(BaseModel):
    ambiguityId: str
    category: str
    sourcePassage: str
    question: str

class RecipientProfile(AudienceContext):
    recipientId: str

class EmailRequest(BaseModel):
    originalDraft: str = Field(min_length=1, max_length=20000, pattern=r"\S")
    audience: AudienceContext
    communicationMode: Literal["shared"] = "shared"
    clarifications: list[Clarification] = Field(default_factory=list, max_length=20)

class SourceFact(BaseModel):
    factId: str
    category: str
    description: str
    sourcePassage: str
    critical: bool = True
    extractionUncertainty: str = "Rule-based candidate; human verification required."
    categories: list[str] = Field(default_factory=list)
    origin: Literal["explicitSource", "userConfirmedContext", "modelInterpretation", "unknown"] = "explicitSource"
    evidenceSource: Literal["originalDraft", "audienceContext", "clarification"] = "originalDraft"

class AnalysisResult(BaseModel):
    facts: list[SourceFact]
    senderIntent: str
    limitations: list[str]
    ambiguities: list[AmbiguityQuestion] = Field(default_factory=list)
    confirmedContext: list[SourceFact] = Field(default_factory=list)

class Finding(BaseModel):
    category: str
    severity: Literal["warning", "error"]
    explanation: str
    sourceEvidence: str = ""
    generatedText: str = ""
    suggestedAction: str = "Compare with the original and correct or confirm this change."
    reviewMethod: Literal["deterministic", "semanticModel"] = "deterministic"

class ValidationRequest(BaseModel):
    originalDraft: str = Field(min_length=1, max_length=20000, pattern=r"\S")
    improvedDraft: str = Field(min_length=1, max_length=20000, pattern=r"\S")
    audience: AudienceContext | None = None
    clarifications: list[Clarification] = Field(default_factory=list, max_length=20)

class ChangeExplanation(BaseModel):
    whatChanged: str
    whyHelpful: str
    sourceEvidence: str
    generatedEvidence: str = ""
    requiresHumanReview: bool = True

class ValidationResult(BaseModel):
    findings: list[Finding]
    semanticStatus: Literal["unavailable"] = "unavailable"
    status: Literal["reviewRequired"] = "reviewRequired"
    limitation: str = "Deterministic checks only. Semantic equivalence is not verified; human review is required."
    changeDetails: list[ChangeExplanation] = Field(default_factory=list)

class SemanticFinding(BaseModel):
    category: Literal["criticalOmission", "changedAction", "unsupportedCommitment", "inventedPraise", "statusChanged", "uncertaintyChanged", "accessibilityChanged", "unsupportedExplanation"]
    severity: Literal["warning", "error"]
    explanation: str = Field(min_length=1, max_length=400)
    sourceEvidence: str = Field(default="", max_length=2000)
    generatedText: str = Field(default="", max_length=2000)

class SemanticReport(BaseModel):
    findings: list[SemanticFinding] = Field(max_length=3)

class SemanticReviewResult(BaseModel):
    reviewStatus: Literal["completed", "unavailable"]
    findings: list[Finding] = Field(default_factory=list)
    limitations: list[str]
    independent: bool = False
    elapsedMilliseconds: float = 0

class ImprovementResult(BaseModel):
    improvedDraft: str
    analysis: AnalysisResult
    validation: ValidationResult
    provider: str
    isMock: bool
    changes: list[str]
    changeDetails: list[ChangeExplanation] = Field(default_factory=list)
    processingMilliseconds: dict[str, float] = Field(default_factory=dict)
