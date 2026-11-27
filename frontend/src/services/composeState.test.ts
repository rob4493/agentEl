import {afterEach,describe,it,expect,vi} from 'vitest';
import {createComposeRequest,createAdaptationClient} from './composeState';
import {initialReader,receiveAnalysis,reviewReader,editReceived} from './readerState';
import type {ReaderResult} from './readerState';
import type {AdaptationResult} from '../types/contracts';
import {initialReview,changeDraft,validateDraft,approveDraft,canCopyApprovedDraft} from './reviewState';
const audience={group:'Team',technicalBackground:'',preferences:'',communicationObjectives:'Preserve meaning',requiredDetails:''};
const report:ReaderResult={primaryStyle:'Driver',uncertainty:'mixed',observations:[],explanation:'Tentative',limitations:[]};
const response:AdaptationResult={targetStyle:'Amiable',improvedDraft:'I can help on December 4.',styleAdjustments:['Warm opening.'],preservationWarnings:['Human review required.'],analysis:{facts:[],confirmedContext:[],senderIntent:'',limitations:[],ambiguities:[]},validation:{findings:[],semanticStatus:'unavailable',status:'reviewRequired',limitation:'Human review',changeDetails:[]},provider:'ollama',isMock:false,changes:[],changeDetails:[],processingMilliseconds:{}};
const request=()=>createComposeRequest('Incoming\nemail.','  I can help on December 4.\n',reviewReader(receiveAnalysis(report),'Amiable'),audience,[]);
afterEach(()=>{vi.unstubAllGlobals();vi.useRealTimers();});

describe('Compose human choice and original preservation',()=>{
 it('transfers only an explicit confirmed/overridden style and exact source strings',()=>{
  const next=request();expect(next.targetStyle).toBe('Amiable');expect(next.receivedEmail).toBe('Incoming\nemail.');expect(next.originalDraft).toBe('  I can help on December 4.\n');expect(report.primaryStyle).toBe('Driver');
 });
 it.each([initialReader,receiveAnalysis(report),reviewReader(initialReader,null),editReceived(reviewReader(receiveAnalysis(report),'Driver'))])('never promotes an unconfirmed, unspecified or outdated style',reader=>expect(()=>createComposeRequest('email','draft',reader,audience,[])).toThrow('Explicitly choose'));
 it('rejects empty drafts',()=>expect(()=>createComposeRequest('email',' \n',reviewReader(initialReader,'Driver'),audience,[])).toThrow('original response'));
 it('lets a manual choice work without analysis and revokes validation after changes',()=>{
  expect(createComposeRequest('','Draft',reviewReader(initialReader,'Analytical'),audience,[]).targetStyle).toBe('Analytical');
  const approved=approveDraft(validateDraft(initialReview));expect(canCopyApprovedDraft(approved)).toBe(true);expect(canCopyApprovedDraft(changeDraft(approved))).toBe(false);
 });
});
describe('Compose API',()=>{
 it('sends the snapshot, receives a suggestion and never overwrites the original',async()=>{
  const next=request();const before=JSON.stringify(next);const fetch=vi.fn().mockResolvedValue({ok:true,json:async()=>response});vi.stubGlobal('fetch',fetch);
  expect(await createAdaptationClient()(next)).toEqual(response);expect(JSON.stringify(next)).toBe(before);expect(JSON.parse(fetch.mock.calls[0][1].body)).toEqual(next);expect(fetch.mock.calls[0][0]).toBe('/api/adaptResponse');
 });
 it('prevents duplicate requests before React can rerender',async()=>{
  let resolve!:(value:unknown)=>void;const fetch=vi.fn().mockImplementation(()=>new Promise(done=>{resolve=done;}));vi.stubGlobal('fetch',fetch);
  const adapt=createAdaptationClient();const pending=adapt(request());await expect(adapt(request())).rejects.toThrow('already processing');expect(fetch).toHaveBeenCalledTimes(1);
  resolve({ok:true,json:async()=>response});await pending;
 });
 it('returns backend failures and releases the request lock for a retry',async()=>{
  vi.stubGlobal('fetch',vi.fn().mockResolvedValueOnce({ok:false,status:503,json:async()=>({detail:'Ollama unavailable'})}).mockResolvedValueOnce({ok:true,json:async()=>response}));
  const adapt=createAdaptationClient();await expect(adapt(request())).rejects.toThrow('Ollama unavailable');expect(await adapt(request())).toEqual(response);
 });
 it('retains clarification questions',async()=>{
  vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:false,status:409,json:async()=>({detail:{code:'clarificationRequired',questions:[{ambiguityId:'deadline',question:'When?',sourcePassage:'EOD'}]}})}));
  await expect(createAdaptationClient()(request())).rejects.toMatchObject({questions:[{ambiguityId:'deadline',question:'When?',sourcePassage:'EOD'}]});
 });
 it.each([{...response,targetStyle:'Driver'},{...response,isMock:true},{...response,improvedDraft:''}])('rejects invalid, mock or mismatched adaptation responses',async bad=>{
  vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:true,json:async()=>bad}));await expect(createAdaptationClient()(request())).rejects.toThrow('invalid adaptation');
 });
 it('bounds waiting and preserves the source on timeout',async()=>{
  vi.useFakeTimers();const next=request();vi.stubGlobal('fetch',vi.fn((_url,options)=>new Promise((_resolve,reject)=>options.signal.addEventListener('abort',()=>reject(new Error('abort'))))));
  const pending=expect(createAdaptationClient()(next)).rejects.toThrow('timed out');await vi.advanceTimersByTimeAsync(70000);await pending;expect(next.originalDraft).toBe(request().originalDraft);
 });
});
