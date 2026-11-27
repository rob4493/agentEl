import {useEffect,useState} from 'react';
import {describeBackend} from '../services/serviceStatus';
import type {HealthResult} from '../services/serviceStatus';
import {WorkspaceIcon} from './workspaceIcon';
import {apiFetch} from '../services/api';

export function ServiceStatus() {
  const [health,setHealth]=useState<HealthResult|null>(null);
  const [checking,setChecking]=useState(true);
  const [refreshId,setRefreshId]=useState(0);
  useEffect(()=>{
    const controller=new AbortController();
    setChecking(true);
    apiFetch('health',{signal:controller.signal},10000).then(async response=>{
      if(!response.ok) throw new Error('Unavailable');
      const next=await response.json();
      if(!next || next.status!=='ok' || typeof next.provider!=='string') throw new Error('Invalid status');
      if(!controller.signal.aborted) setHealth(next);
    }).catch(()=>{if(!controller.signal.aborted) setHealth(null);}).finally(()=>{if(!controller.signal.aborted) setChecking(false);});
    return ()=>controller.abort();
  },[refreshId]);
  const status=describeBackend(health);
  return <button className={`serviceStatus ${!checking&&!health?'isUnavailable':''}`} disabled={checking} onClick={()=>setRefreshId(value=>value+1)} title="Refresh local backend status. Model readiness is checked only when inference is requested." aria-label={checking?'Checking backend status':`Refresh backend status. ${status.label}. ${status.detail}`}><span className={`statusDot ${checking?'isChecking':''}`}/><span><strong>{checking?'Checking backend…':status.label}</strong><small>{checking?'Local service status':status.detail}</small></span><WorkspaceIcon name="refresh"/></button>;
}
