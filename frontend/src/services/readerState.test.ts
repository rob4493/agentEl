import {describe,it,expect,vi,afterEach} from 'vitest';
import {initialReader,receiveAnalysis,editReceived,reviewReader,currentReaderContext,analyzeReceivedEmail,canContinueToCompose} from './readerState';
import type {ReaderResult} from './readerState';
const result:ReaderResult={primaryStyle:'Driver',uncertainty:'mixed',observations:[{style:'Driver',characteristic:'actions',excerpt:'Please review.'}],explanation:'Tentative.',limitations:['Not personality.']};
afterEach(()=>vi.unstubAllGlobals());
describe('reader review state and transport',()=>{
  it('keeps the model suggestion and evidence unchanged during override',()=>{
    const state=reviewReader(receiveAnalysis(result),'Amiable');
    expect(state.result).toEqual(result);expect(state.selectedStyle).toBe('Amiable');
    expect(currentReaderContext('Current email',state)?.analysis?.observations).toEqual(result.observations);
  });
  it('allows reviewed inconclusive choice and preserves context across navigation',()=>{
    const state=reviewReader(receiveAnalysis(result),null);
    expect(currentReaderContext('Original\nemail',state)).toEqual({receivedEmail:'Original\nemail',analysis:result,selectedStyle:null});
    expect(currentReaderContext('Original\nemail',state)).toEqual(currentReaderContext('Original\nemail',state));
  });
  it('invalidates stale analysis and confirmation on input change',()=>{
    const stale=editReceived(reviewReader(receiveAnalysis(result),'Driver'));
    expect(stale.outdated).toBe(true);expect(stale.reviewed).toBe(false);expect(currentReaderContext('Changed email',stale)).toBeNull();
    const manual=reviewReader(stale,'Analytical');expect(manual.result).toBeNull();expect(manual.outdated).toBe(false);
    expect(currentReaderContext('Changed email',manual)?.selectedStyle).toBe('Analytical');
  });
  it('never treats an unreviewed model suggestion as reader context',()=>expect(currentReaderContext('email',receiveAnalysis(result))).toBeNull());
  it('sends only the received email to the dedicated endpoint',async()=>{
    const fetchMock=vi.fn().mockResolvedValue({ok:true,json:async()=>result});vi.stubGlobal('fetch',fetchMock);
    expect(await analyzeReceivedEmail('Email\nparagraph')).toEqual(result);
    expect(fetchMock.mock.calls[0][0]).toBe('/api/readerAnalysis');expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({receivedEmail:'Email\nparagraph'});
  });
  it('reports backend failure without fabricating analysis',async()=>{
    vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:false,status:503,json:async()=>({detail:'Ollama unavailable'})}));
    await expect(analyzeReceivedEmail('email')).rejects.toThrow('Ollama unavailable');
  });
});
it('rejects malformed backend output',async()=>{
 vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:true,json:async()=>({})}));
 await expect(analyzeReceivedEmail('email')).rejects.toThrow('invalid analysis');
});
it('aborts a timed-out request without returning a result',async()=>{
 vi.useFakeTimers();
 vi.stubGlobal('fetch',vi.fn((_url,options)=>new Promise((_resolve,reject)=>options.signal.addEventListener('abort',()=>reject(new Error('aborted'))))));
 const pending=expect(analyzeReceivedEmail('email')).rejects.toThrow('timed out');
 await vi.advanceTimersByTimeAsync(70000);await pending;vi.useRealTimers();
});
it('explains an unreachable local backend',async()=>{
 vi.stubGlobal('fetch',vi.fn().mockRejectedValue(new TypeError('Failed to fetch')));
 await expect(analyzeReceivedEmail('email')).rejects.toThrow('local backend could not be reached');
});

it('requires an explicit current review before continuing to Compose',()=>{
 expect(canContinueToCompose(initialReader)).toBe(false);
 expect(canContinueToCompose(receiveAnalysis(result))).toBe(false);
 expect(canContinueToCompose(reviewReader(receiveAnalysis(result),'Amiable'))).toBe(true);
 expect(canContinueToCompose(reviewReader(receiveAnalysis(result),null))).toBe(true);
 expect(canContinueToCompose(editReceived(reviewReader(receiveAnalysis(result),'Driver')))).toBe(false);
});
