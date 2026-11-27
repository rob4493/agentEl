export function resolveApiConfiguration(baseValue:string|undefined,betaValue:string|undefined,isDev:boolean) {
  if(betaValue!==undefined&&!['true','false'].includes(betaValue)) throw new Error('VITE_BETA_ENABLED must be true or false.');
  const betaEnabled=betaValue==='true';const raw=(baseValue??'').trim();
  if(!raw) {
    if(betaEnabled&&!isDev) throw new Error('Private beta requires VITE_API_BASE_URL.');
    return {baseUrl:'',betaEnabled};
  }
  let parsed:URL;
  try {parsed=new URL(raw);} catch {throw new Error('Invalid API base URL.');}
  const local=['localhost','127.0.0.1','[::1]'].includes(parsed.hostname);
  if(parsed.username||parsed.password||parsed.search||parsed.hash||!['','/'].includes(parsed.pathname)||
      (parsed.protocol!=='https:'&&!(isDev&&!betaEnabled&&local&&parsed.protocol==='http:'))) throw new Error('API base must be an HTTPS origin without credentials or paths.');
  return {baseUrl:parsed.origin,betaEnabled};
}

export function isVerifiedBetaHealth(value:unknown):boolean {
  const health=value as Record<string,unknown>|null;
  return Boolean(health&&typeof health==='object'&&health.status==='ok'&&health.provider==='ollama'&&health.betaAccessVerified===true);
}
