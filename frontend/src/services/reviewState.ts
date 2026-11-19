export interface ReviewState { revision: number; validatedRevision: number | null; approved: boolean }
export const initialReview: ReviewState = {revision:0, validatedRevision:null, approved:false};
export function changeDraft(state: ReviewState): ReviewState { return {revision:state.revision+1, validatedRevision:null, approved:false}; }
export function validateDraft(state: ReviewState): ReviewState { return {...state, validatedRevision:state.revision, approved:false}; }
export function approveDraft(state: ReviewState): ReviewState {
  // Approval is tied to the exact validated revision, including source and audience changes.
  return {...state, approved:state.validatedRevision === state.revision};
}
export function rejectDraft(state: ReviewState): ReviewState {return changeDraft(state);}
export function clearApproval(state: ReviewState): ReviewState {return {...state,approved:false};}
