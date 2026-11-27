import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {describe,it,expect} from 'vitest';
import {DiscoverScreen,UnderstandScreen,ReviewSummary,communicationStyles} from './journeyScreens';
import {initialReader} from '../services/readerState';
import {StageProgress} from './stageProgress';

describe('four-stage screens',()=>{
  it('introduces four writing patterns without claiming classification works',()=>{
    const html=renderToStaticMarkup(<DiscoverScreen onStart={()=>{}}/>);
    for(const style of communicationStyles) expect(html).toContain(style.name);
    expect(html).toContain('Get Started');expect(html).toContain('not fixed personality types');expect(html).toContain('About this preview');expect(html).toContain('How to write for this reader');
  });
  it('renders retained received input and honest unavailable analysis',()=>{
    const html=renderToStaticMarkup(<UnderstandScreen receivedEmail="Please review the proposed schedule." disabled={false} analyzing={false} reader={initialReader} onAnalyze={()=>{}} onReview={()=>{}} onChange={()=>{}}/>);
    expect(html).toContain('Please review the proposed schedule.');expect(html).toContain('No current analysis');expect(html).toContain('configured local Ollama');
  });
  it('renders all navigation positions without claiming completed analysis',()=>{
    for(let stage=0;stage<4;stage++) {
      const html=renderToStaticMarkup(<StageProgress stage={stage} disabled={false} onNavigate={()=>{}}/>);
      expect(html.match(/aria-current="step"/g)).toHaveLength(1);
      expect(html).not.toContain('isComplete');
      for(const label of ['Discover','Understand','Compose','Review']) expect(html).toContain(label);
    }
    expect(renderToStaticMarkup(<StageProgress stage={2} disabled onNavigate={()=>{}}/>).match(/disabled=""/g)).toHaveLength(4);
  });
  it('keeps empty review and learning placeholders honest',()=>{
    const html=renderToStaticMarkup(<ReviewSummary originalDraft="" improvedDraft="" hasResult={false} hasValidation={false} factCount={0} findingCount={0} isMock={false} comparison={null} findings={<p>Important warnings</p>} actions={null}/>);
    expect(html).toContain('No improved draft yet');expect(html).toContain('No current validation');expect(html).toContain('not implemented');expect(html).toContain('Important warnings');
  });
  it('uses actual drafts and counts and separates mock from adaptation',()=>{
    const html=renderToStaticMarkup(<ReviewSummary originalDraft="Source email" improvedDraft="Spacing demo" hasResult hasValidation factCount={3} findingCount={2} isMock comparison={<p>Actual changes</p>} findings={null} actions={null}/>);
    expect(html).toContain('Source email');expect(html).toContain('Spacing demo');expect(html).toContain('mock spacing demonstration');expect(html).toContain('Actual changes');
  });
});
