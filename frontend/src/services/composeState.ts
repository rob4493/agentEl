import {currentReaderContext} from './readerState';
import type {ReaderState,WritingStyle} from './readerState';
import type {AudienceContext,Clarification,AdaptationResult} from '../types/contracts';
import {ApiError,postJson} from './api';

export interface ComposeRequest {receivedEmail:string;originalDraft:string;targetStyle:WritingStyle;audience:AudienceContext;clarifications:Clarification[];communicationMode:'shared'}
export function createComposeRequest(receivedEmail:string,originalDraft:string,reader:ReaderState,audience:AudienceContext,clarifications:Clarification[]):ComposeRequest {
  const context=currentReaderContext(receivedEmail,reader);
  if(!originalDraft.trim()) throw new ApiError('Write your original response before adapting.');
  if(!context?.selectedStyle) throw new ApiError('Explicitly choose a target reader style before adapting.');
  // Do not trim, normalize or replace the author's draft or incoming context.
  return {receivedEmail,originalDraft,targetStyle:context.selectedStyle,audience,clarifications,communicationMode:'shared'};
}

export function createAdaptationClient() {
  let pending=false;
  return async(request:ComposeRequest):Promise<AdaptationResult>=>{
    if(pending) throw new ApiError('An adaptation is already processing.');
    pending=true;
    const controller=new AbortController();const timer=setTimeout(()=>controller.abort(),70000);
    try {
      const result=await postJson<AdaptationResult>('adaptResponse',request,controller.signal);
      if(result.targetStyle!==request.targetStyle||result.isMock!==false||typeof result.improvedDraft!=='string'||!result.improvedDraft.trim()||!Array.isArray(result.styleAdjustments)||!result.styleAdjustments.every(x=>typeof x==='string')||!Array.isArray(result.preservationWarnings)||!result.preservationWarnings.every(x=>typeof x==='string')||!Array.isArray(result.analysis?.facts)||!Array.isArray(result.validation?.findings)) throw new ApiError('The backend returned an invalid adaptation. No suggestion was accepted.');
      return result;
    } catch(error) {
      if(controller.signal.aborted) throw new ApiError('Adaptation timed out. Your original response is unchanged; please try again.');
      if(error instanceof TypeError) throw new ApiError('The local backend could not be reached. Your original response is unchanged.');
      throw error;
    } finally {clearTimeout(timer);pending=false;}
  };
}
export const requestAdaptation=createAdaptationClient();
