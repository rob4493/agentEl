export interface AudienceContext { group: string; technicalBackground: string; preferences: string; communicationObjectives: string; requiredDetails: string }
export interface AmbiguityQuestion { ambiguityId: string; category: string; sourcePassage: string; question: string }
export interface Clarification { ambiguityId: string; sourcePassage: string; answer: string }
export interface SourceFact { factId: string; category: string; categories: string[]; description: string; sourcePassage: string; critical: boolean; extractionUncertainty: string; origin: string; evidenceSource: string }
export interface AnalysisResult { facts: SourceFact[]; confirmedContext: SourceFact[]; senderIntent: string; limitations: string[]; ambiguities: AmbiguityQuestion[] }
export interface Finding { category: string; severity: string; explanation: string; sourceEvidence: string; generatedText: string; suggestedAction: string; reviewMethod: 'deterministic' | 'semanticModel' }
export interface ChangeExplanation { whatChanged: string; whyHelpful: string; sourceEvidence: string; generatedEvidence: string; requiresHumanReview: boolean }
export interface ValidationResult { findings: Finding[]; semanticStatus: 'unavailable'; status: 'reviewRequired'; limitation: string; changeDetails: ChangeExplanation[] }
export interface SemanticReviewResult { reviewStatus: 'completed' | 'unavailable'; findings: Finding[]; limitations: string[]; independent: false; elapsedMilliseconds: number }
export interface ImprovementResult { improvedDraft: string; analysis: AnalysisResult; validation: ValidationResult; provider: string; isMock: boolean; changes: string[]; changeDetails: ChangeExplanation[]; processingMilliseconds: Record<string,number> }
export interface AdaptationResult extends ImprovementResult { targetStyle: import('../services/readerState').WritingStyle; styleAdjustments:string[]; preservationWarnings:string[] }
