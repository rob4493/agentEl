export interface HealthResult { status:string; provider:string; modelConnection:string; semanticValidation:string }

export function describeBackend(health:HealthResult|null): {label:string;detail:string} {
  if(!health || health.status!=='ok') return {label:'Backend unavailable',detail:'Check the local backend and try refreshing.'};
  // Service health does not test inference. Never turn provider selection into a connection claim.
  if(health.provider==='ollama') return {label:'Backend available',detail:'Ollama selected · Model readiness not checked'};
  if(health.provider==='mock') return {label:'Backend available',detail:'Mock mode · Spacing demonstration only'};
  return {label:'Backend available',detail:'Provider configuration needs review'};
}
