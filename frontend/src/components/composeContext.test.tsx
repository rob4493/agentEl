import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {it,expect} from 'vitest';
import {ComposeContext,AdaptationNotes} from './composeContext';
import {ReviewSummary} from './journeyScreens';
import type {AdaptationResult} from '../types/contracts';

it('shows incoming context exactly but never preselects a model suggestion',()=>{
 const html=renderToStaticMarkup(<ComposeContext receivedEmail={'First paragraph.\n\nSecond paragraph.'} selectedStyle={null} modelStyle="Amiable" disabled={false} onSelect={()=>{}}/>);
 expect(html).toContain('First paragraph.\n\nSecond paragraph.');expect(html).toContain('has not been confirmed');expect(html).toContain('<option value="" selected="">');expect(html).toContain('required=""');
});
it('shows an explicit override and disables changes during processing',()=>{
 const html=renderToStaticMarkup(<ComposeContext receivedEmail="email" selectedStyle="Driver" modelStyle="Amiable" disabled onSelect={()=>{}}/>);
 expect(html).toContain('Selected by you: Driver');expect(html).toContain('<option value="Driver" selected="">');expect(html).toContain('disabled=""');
});
it('passes both drafts and selected style to Review without claiming equivalence',()=>{
 const html=renderToStaticMarkup(<ReviewSummary originalDraft={'I may review on December 4.\n'} improvedDraft="I may review the plan on December 4." targetStyle="Analytical" hasResult hasValidation factCount={1} findingCount={1} isMock={false} comparison={null} findings={null} actions={null}/>);
 expect(html).toContain('I may review on December 4.\n');expect(html).toContain('I may review the plan on December 4.');expect(html).toContain('selected Analytical');expect(html).toContain('not automatically verified');
});
it('does not reuse a model change explanation after the user edits',()=>{
 const result={targetStyle:'Driver',styleAdjustments:['Original explanation'],preservationWarnings:['Review']} as AdaptationResult;
 const html=renderToStaticMarkup(<AdaptationNotes result={result} edited/>);expect(html).not.toContain('Original explanation');expect(html).toContain('no longer describes this version');
});
