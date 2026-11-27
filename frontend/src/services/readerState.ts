import {apiFetch} from './api';
export type WritingStyle='Expressive'|'Amiable'|'Driver'|'Analytical';
export interface ReaderObservation {style:WritingStyle;characteristic:string;excerpt:string;explanation?:string;explanationEvidence?:string|null}
export interface ReaderResult {primaryStyle:WritingStyle|null;uncertainty:'tentative'|'mixed'|'insufficientEvidence';uncertaintyReason?:'weakSignals'|'competingInterpretations'|'contextLimited'|null;observations:ReaderObservation[];explanation:string;limitations:string[]}
export interface ReaderState {result:ReaderResult|null;outdated:boolean;selectedStyle:WritingStyle|null;reviewed:boolean;error:string}
export const initialReader:ReaderState={result:null,outdated:false,selectedStyle:null,reviewed:false,error:''};
export function editReceived(state:ReaderState):ReaderState {return {...initialReader,result:state.result,outdated:Boolean(state.result)};}
export function receiveAnalysis(result:ReaderResult):ReaderState {return {...initialReader,result};}
export function reviewReader(state:ReaderState,selectedStyle:WritingStyle|null):ReaderState {return {...state,result:state.outdated?null:state.result,outdated:false,selectedStyle,reviewed:true};}
export function canContinueToCompose(state:ReaderState):boolean {return state.reviewed&&!state.outdated;}
export function currentReaderContext(receivedEmail:string,state:ReaderState) {return state.reviewed&&!state.outdated?{receivedEmail,analysis:state.result,selectedStyle:state.selectedStyle}:null;}
export async function analyzeReceivedEmail(receivedEmail:string):Promise<ReaderResult> {
  const controller=new AbortController();
  const timeoutId=setTimeout(()=>controller.abort(),70000);
  try {
    const response=await apiFetch('readerAnalysis',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({receivedEmail}),signal:controller.signal});
    if(!response.ok) {const body=await response.json().catch(()=>null);throw new Error(typeof body?.detail==='string'?body.detail:`Writing analysis failed (${response.status}). Check the input and local backend.`);}
    const result=await response.json();
    if(!result||!Array.isArray(result.observations)||result.observations.length>3||!Array.isArray(result.limitations)||typeof result.explanation!=='string') throw new Error('The backend returned an invalid analysis. Please try again.');
    return result;
  } catch(error) {if(controller.signal.aborted) throw new Error('Writing analysis timed out. No analysis was accepted. Please try again.');if(error instanceof TypeError) throw new Error('The local backend could not be reached. Check that it is running and try again.');throw error;}
  finally {clearTimeout(timeoutId);}
}
