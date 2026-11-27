import type {AmbiguityQuestion} from '../types/contracts';
import {resolveApiConfiguration} from './apiConfiguration';
import {getAccessCode,setAccessCode} from './betaSession';

export const apiConfiguration=resolveApiConfiguration(import.meta.env.VITE_API_BASE_URL,import.meta.env.VITE_BETA_ENABLED,import.meta.env.DEV);

export async function apiFetch(path:string,init:RequestInit={},timeoutMs=70000):Promise<Response> {
  if(!/^[A-Za-z][A-Za-z0-9/]*$/.test(path)) throw new Error('Invalid API path.');
  const controller=new AbortController();const abort=()=>controller.abort();
  if(init.signal?.aborted)controller.abort();
  init.signal?.addEventListener('abort',abort,{once:true});
  const timer=setTimeout(abort,timeoutMs);const headers=new Headers(init.headers);const code=getAccessCode();
  if(code)headers.set('Authorization',`Bearer ${code}`);
  try {
    const response=await fetch(`${apiConfiguration.baseUrl}/api/${path}`,{...init,headers,signal:controller.signal,credentials:'omit',cache:'no-store',redirect:'error'});
    if(response.status===401&&getAccessCode()===code)setAccessCode('');
    return response;
  } finally {clearTimeout(timer);init.signal?.removeEventListener('abort',abort);}
}

export class ApiError extends Error {
  questions: AmbiguityQuestion[];
  constructor(message: string, questions: AmbiguityQuestion[] = []) {super(message);this.questions = questions;}
}

export async function postJson<T>(path: string, body: unknown, signal?:AbortSignal): Promise<T> {
  const response = await apiFetch(path, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body),...(signal?{signal}:{})});
  if (!response.ok) {
    const error = await response.json().catch(() => null);
    if (error?.detail?.code === 'clarificationRequired') throw new ApiError('Clarify the material ambiguity before generation.', error.detail.questions);
    throw new ApiError(typeof error?.detail === 'string' ? error.detail : `Request failed (${response.status}). Check input and backend availability.`);
  }
  return response.json();
}
