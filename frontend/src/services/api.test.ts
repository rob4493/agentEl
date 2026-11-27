import {afterEach,describe,expect,it,vi} from 'vitest';
import {apiConfiguration,apiFetch,postJson} from './api';
import {resolveApiConfiguration,isVerifiedBetaHealth} from './apiConfiguration';
import {getAccessCode,setAccessCode,onAccessChange} from './betaSession';

const initialBase=apiConfiguration.baseUrl;
afterEach(()=>{apiConfiguration.baseUrl=initialBase;setAccessCode('');vi.unstubAllGlobals();vi.useRealTimers();});

it('does not unlock beta from an unauthenticated development health response',()=>{
  expect(isVerifiedBetaHealth({status:'ok',provider:'ollama',betaAccessVerified:false})).toBe(false);
  expect(isVerifiedBetaHealth({status:'ok',provider:'mock',betaAccessVerified:true})).toBe(false);
  expect(isVerifiedBetaHealth({status:'ok',provider:'ollama',betaAccessVerified:true})).toBe(true);
});

describe('beta API configuration',()=>{
  it('uses relative requests in unchanged local development',()=>expect(resolveApiConfiguration(undefined,undefined,true)).toEqual({baseUrl:'',betaEnabled:false}));
  it('requires HTTPS API origin for production beta',()=>{
    expect(()=>resolveApiConfiguration(undefined,'true',false)).toThrow('requires');
    expect(resolveApiConfiguration('https://api.example.test/','true',false)).toEqual({baseUrl:'https://api.example.test',betaEnabled:true});
  });
  it.each(['http://api.example.test','https://api.example.test/api','https://api.example.test/?code=bad','https://api.example.test/#fragment','https://user:placeholder@api.example.test','//api.example.test'])('rejects unsafe API configuration %s',value=>expect(()=>resolveApiConfiguration(value,'true',false)).toThrow());
  it('rejects a misspelled beta toggle',()=>expect(()=>resolveApiConfiguration('','yes',false)).toThrow());
});

it('centralizes URL/auth without cookies, caches or redirects',async()=>{
  apiConfiguration.baseUrl='https://api.example.test';setAccessCode('synthetic-test-only');
  const fetchMock=vi.fn().mockResolvedValue({ok:true,status:200,json:async()=>({status:'ok'})});vi.stubGlobal('fetch',fetchMock);
  await apiFetch('health');await postJson('validate',{originalDraft:'source'});
  for(const [url,options] of fetchMock.mock.calls) {
    expect(url).toMatch(/^https:\/\/api.example.test\/api\//);
    expect(options.headers.get('Authorization')).toBe('Bearer synthetic-test-only');
    expect(options.credentials).toBe('omit');expect(options.redirect).toBe('error');expect(options.cache).toBe('no-store');
  }
  expect(fetchMock.mock.calls[0][0]).not.toContain('synthetic');
});

it('clears code and notifies lock listeners on unauthorized responses',async()=>{
  const listener=vi.fn();const stop=onAccessChange(listener);setAccessCode('synthetic-test-only');
  vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:false,status:401}));
  await apiFetch('health');expect(getAccessCode()).toBe('');expect(listener).toHaveBeenCalled();stop();
});

it('does not let stale unauthorized responses clear a replacement code',async()=>{
  let resolve!:(value:unknown)=>void;
  vi.stubGlobal('fetch',vi.fn(()=>new Promise(r=>{resolve=r;})));
  setAccessCode('old-test-code');const pending=apiFetch('health');setAccessCode('new-test-code');resolve({status:401});await pending;
  expect(getAccessCode()).toBe('new-test-code');
});

it('bounds health request waiting',async()=>{
  vi.useFakeTimers();vi.stubGlobal('fetch',vi.fn((_url,options)=>new Promise((_resolve,reject)=>options.signal.addEventListener('abort',()=>reject(new Error('aborted'))))));
  const pending=expect(apiFetch('health',{},10000)).rejects.toThrow('aborted');await vi.advanceTimersByTimeAsync(10000);await pending;
});

it('rejects attempts to substitute an arbitrary API destination',async()=>{
  await expect(apiFetch('https://evil.example')).rejects.toThrow('Invalid API path');
});
