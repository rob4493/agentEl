import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {describe,it,expect} from 'vitest';
import {UnderstandScreen} from './understandScreen';
import {StageProgress} from './stageProgress';
import {communicationStyles} from './discoverScreen';
import {initialReader,receiveAnalysis,reviewReader} from '../services/readerState';
import type {ReaderResult,WritingStyle} from '../services/readerState';
import {createComposeRequest} from '../services/composeState';

const audience={group:'Team',technicalBackground:'',preferences:'',communicationObjectives:'Preserve meaning',requiredDetails:''};
function result(style:WritingStyle|null):ReaderResult {return {primaryStyle:style,uncertainty:'mixed',observations:[{style:'Driver',characteristic:'actions',excerpt:'Please approve.'}],explanation:'Majority rule: 2 of 3 verified observations',limitations:['67% confidence','Two matching characteristics']};}
function render(reader=receiveAnalysis(result('Driver'))) {return renderToStaticMarkup(<UnderstandScreen receivedEmail="Please approve." disabled={false} analyzing={false} reader={reader} onChange={()=>{}} onAnalyze={()=>{}} onReview={()=>{}}/>);}

describe('reader-facing demonstration results',()=>{
 it.each(communicationStyles)('reuses every exact $name handout point in order',style=>{
  const html=render(receiveAnalysis(result(style.name as WritingStyle)));
  expect(html).toContain(`How to communicate with ${style.name==='Driver'?'a':'an'} ${style.name} reader`);
  let previous=-1;
  for(const point of style.characteristics){const position=html.indexOf(renderToStaticMarkup(<li>{point}</li>));expect(position).toBeGreaterThan(previous);previous=position;}
  expect(html).toContain(`style${style.name}`);expect(html).toContain('Based on characteristics observed in the email');
 });
 it('never renders aggregation, raw explanations, observation totals or confidence',()=>{
  const value=result('Driver');value.observations[0].explanation='Two matching characteristics; 67% confidence';
  const html=render(receiveAnalysis(value));
  for(const forbidden of ['2 of 3','Majority rule','Two matching','confidence','Mixed characteristics','countBadge']) expect(html.toLowerCase()).not.toContain(forbidden.toLowerCase());
  expect(html).not.toContain('<blockquote>');expect(html).not.toContain('Evidence from the email');
 });
 it('explains Inconclusive naturally without exposing the rule',()=>{
  const html=render(receiveAnalysis(result(null)));
  expect(html).toContain('Inconclusive');expect(html).toContain('could not make a clear style suggestion');
  expect(html).not.toContain('2 of 3');expect(html).not.toContain('Majority');expect(html).not.toContain('How to communicate with');
 });
 it('does not preselect the suggestion and preserves explicit override for Compose',()=>{
  const unreviewed=receiveAnalysis(result('Driver'));expect(unreviewed.selectedStyle).toBeNull();
  expect(render(unreviewed)).toContain('<option value="unreviewed" disabled="" selected="">');
  const reviewed=reviewReader(unreviewed,'Amiable');
  expect(render(reviewed)).toContain('How to communicate with an Amiable reader');
  expect(createComposeRequest('Incoming','Original response',reviewed,audience,[]).targetStyle).toBe('Amiable');
  expect(reviewed.result?.primaryStyle).toBe('Driver');
 });
 it('can block forward navigation until reviewed without disabling Back/Discover',()=>{
  const html=renderToStaticMarkup(<StageProgress stage={1} disabled={false} blockedStages={[2,3]} onNavigate={()=>{}}/>);
  expect(html.match(/disabled=""/g)).toHaveLength(2);
 });
 it('keeps confirmation available without a model response',()=>expect(render(initialReader)).toContain('Not reviewed yet'));
});
