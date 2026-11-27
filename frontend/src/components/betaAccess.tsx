import {useEffect,useState} from 'react';
import type {ReactNode,FormEvent} from 'react';
import {apiConfiguration,apiFetch} from '../services/api';
import {getAccessCode,setAccessCode,onAccessChange} from '../services/betaSession';
import {isVerifiedBetaHealth} from '../services/apiConfiguration';

export function BetaAccess({children}:{children:ReactNode}) {
  const enabled=apiConfiguration.betaEnabled;
  const [unlocked,setUnlocked]=useState(!enabled);const [mounted,setMounted]=useState(!enabled);
  const [value,setValue]=useState('');const [busy,setBusy]=useState(false);const [error,setError]=useState('');
  useEffect(()=>onAccessChange(()=>{if(!getAccessCode()&&enabled)setUnlocked(false);}),[enabled]);
  async function unlock(event:FormEvent) {
    event.preventDefault();if(busy)return;setBusy(true);setError('');setAccessCode(value.trim());
    try {
      const response=await apiFetch('health',{},10000);
      if(!response.ok)throw new Error(response.status===429?'Too many attempts. Please wait before trying again.':'Access could not be verified. Check your code or contact the beta operator.');
      const health=await response.json();if(!isVerifiedBetaHealth(health))throw new Error('The backend is not in verified private-beta mode. Contact the beta operator.');
      setMounted(true);setUnlocked(true);setValue('');
    } catch(error) {setAccessCode('');setValue('');setError(error instanceof Error?error.message:'Access unavailable.');}
    finally {setBusy(false);}
  }
  return <>{!unlocked&&<main className="betaAccess"><h1>Ritmo private beta</h1><p>Enter your individual access code. It stays only in this tab’s memory. Email submissions travel through Cloudflare to the operator’s local inference service.</p><form onSubmit={unlock}><label htmlFor="betaCode">Beta access code</label><input id="betaCode" type="password" autoComplete="off" spellCheck={false} maxLength={200} required value={value} onChange={event=>setValue(event.target.value)}/><button className="button primaryButton" disabled={busy}>{busy?'Checking access…':'Enter beta'}</button></form>{error&&<p role="alert">{error}</p>}<p>When access expires or is revoked, re-enter a valid code. Drafts remain only in this tab; reload to clear them.</p></main>}
    {unlocked&&enabled&&<div className="betaAccessBar"><span>Private beta · human review required</span><button className="button" onClick={()=>setAccessCode('')}>Lock beta access</button></div>}
    {/* Preserve source state when access expires; hidden content is NOT a security boundary. */}
    <div hidden={!unlocked}>{mounted?children:null}</div></>;
}
