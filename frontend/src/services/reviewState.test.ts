import {expect, test} from 'vitest';
import {initialReview, changeDraft, validateDraft, approveDraft, rejectDraft, clearApproval} from './reviewState';
test('approval requires validation and every edit revokes approval', () => {
  expect(approveDraft(initialReview).approved).toBe(false);
  const approved = approveDraft(validateDraft(initialReview));
  expect(approved.approved).toBe(true);
  expect(changeDraft(approved)).toEqual({revision:1,validatedRevision:null,approved:false});
});
test('rejecting or regenerating an approved draft requires fresh validation and approval',()=>{
  const approved = approveDraft(validateDraft(initialReview));
  const rejected = rejectDraft(approved);
  expect(rejected.approved).toBe(false);
  expect(rejected.validatedRevision).toBe(null);
  const regenerated = validateDraft(changeDraft(approved));
  expect(regenerated.approved).toBe(false);
  expect(regenerated.revision).toBeGreaterThan(approved.revision);
});
test('context or clarification edits use the same revision invalidation as output edits',()=>{
  const edited = changeDraft(approveDraft(validateDraft(initialReview)));
  expect(approveDraft(edited).approved).toBe(false);
  expect(approveDraft(validateDraft(edited)).approved).toBe(true);
});
test('requesting extra review revokes approval without claiming new validation',()=>{
  const state = clearApproval(approveDraft(validateDraft(initialReview)));
  expect(state.approved).toBe(false);
  expect(state.validatedRevision).toBe(state.revision);
});
