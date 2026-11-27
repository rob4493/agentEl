import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {describe,it,expect} from 'vitest';
import {AudienceFields,AdditionalPreferences,updateContext,audienceSuggestions,goalSuggestions} from './preparationFields';
import {initialReview,validateDraft,approveDraft,changeDraft,canCopyApprovedDraft} from '../services/reviewState';
const audience={group:'Custom group',communicationObjectives:'My exact objective',technicalBackground:'Known context',preferences:'Use short paragraphs',requiredDetails:''};
describe('preparation context',()=>{
  it('populates suggestions and retains subsequent custom audience and goal edits',()=>{
    for(const value of audienceSuggestions) expect(updateContext(audience,'group',value).group).toBe(value);
    for(const value of goalSuggestions) expect(updateContext(audience,'communicationObjectives',value).communicationObjectives).toBe(value);
    const selected=updateContext(audience,'group',audienceSuggestions[0]);
    expect(updateContext(selected,'group','My complete custom group').group).toBe('My complete custom group');
    expect(updateContext(audience,'communicationObjectives','Ask for detailed feedback on section 3').communicationObjectives).toBe('Ask for detailed feedback on section 3');
  });
  it('renders keyboard-operable suggestions and editable custom values',()=>{
    const html=renderToStaticMarkup(<AudienceFields audience={audience} disabled={false} onChange={()=>{}}/>);
    expect(html).toContain('type="button"');expect(html).toContain('aria-pressed="false"');
    expect(html).toContain('value="Custom group"');expect(html).toContain('value="My exact objective"');
  });
  it('retains advanced values while closed and keeps the example outside input values',()=>{
    const html=renderToStaticMarkup(<AdditionalPreferences audience={audience} disabled={false} onChange={()=>{}}/>);
    expect(html).not.toContain(' open=');expect(html).toContain('value="Known context"');expect(html).toContain('value="Use short paragraphs"');
    expect(html).toContain('Example only:');expect(html).toContain('value=""');
    expect(JSON.stringify(audience)).not.toContain('2.4.1');
  });
  it('revokes approval when context changes through the shared invalidation transition',()=>{
    const approved=approveDraft(validateDraft(initialReview));expect(canCopyApprovedDraft(approved)).toBe(true);
    expect(canCopyApprovedDraft(changeDraft(approved))).toBe(false);
  });
});
