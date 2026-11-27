import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {it,expect} from 'vitest';
import {UnderstandScreen} from './understandScreen';
import {initialReader,receiveAnalysis,editReceived} from '../services/readerState';
it('disables empty input and explains privacy',()=>{
 const html=renderToStaticMarkup(<UnderstandScreen receivedEmail="" disabled={false} analyzing={false} reader={initialReader} onChange={()=>{}} onAnalyze={()=>{}} onReview={()=>{}}/>);
 expect(html).toContain('disabled=""');expect(html).toContain('Avoid including passwords');expect(html).toContain('Paste the email you received');
});
it('hides stale findings and shows current errors',()=>{
 const stale=editReceived(receiveAnalysis({primaryStyle:'Driver',uncertainty:'tentative',observations:[{style:'Driver',characteristic:'actions',excerpt:'STALE EVIDENCE'}],explanation:'Old explanation',limitations:[]}));
 const html=renderToStaticMarkup(<UnderstandScreen receivedEmail="Changed" disabled={false} analyzing={false} reader={{...stale,error:'Backend unavailable'}} onChange={()=>{}} onAnalyze={()=>{}} onReview={()=>{}}/>);
 expect(html).not.toContain('STALE EVIDENCE');expect(html).toContain('outdated');expect(html).toContain('Backend unavailable');
});
it('shows style guidance without source evidence or generated explanations',()=>{
 const reader=receiveAnalysis({primaryStyle:'Analytical',uncertainty:'tentative',observations:[{style:'Analytical',characteristic:'structure',excerpt:'Which version applies?',explanation:'The wording is tentatively interpreted as structured clarification.'}],explanation:'A tentative suggestion.',limitations:[]});
 const html=renderToStaticMarkup(<UnderstandScreen receivedEmail="Which version applies?" disabled={false} analyzing={false} reader={reader} onChange={()=>{}} onAnalyze={()=>{}} onReview={()=>{}}/>);
 expect(html).not.toContain('<blockquote>');
 expect(html).toContain('How to communicate with an Analytical reader');
 expect(html).not.toContain('The wording is tentatively interpreted as structured clarification.');
 expect(html).not.toContain('Evidence from the email');
 expect(html).not.toContain('Model interpretation of a verified excerpt; please review.');
});
it('retains a safe label-based fallback for an older response without explanation',()=>{
 const reader=receiveAnalysis({primaryStyle:'Driver',uncertainty:'tentative',observations:[{style:'Driver',characteristic:'actions',excerpt:'Please review.'}],explanation:'Tentative.',limitations:[]});
 const html=renderToStaticMarkup(<UnderstandScreen receivedEmail="Please review." disabled={false} analyzing={false} reader={reader} onChange={()=>{}} onAnalyze={()=>{}} onReview={()=>{}}/>);
 expect(html).toContain('How to communicate with a Driver reader');expect(html).not.toContain('<blockquote>');
});
