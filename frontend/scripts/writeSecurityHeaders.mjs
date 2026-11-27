import {writeFileSync} from 'node:fs';
import {loadEnv} from 'vite';
const environment=loadEnv('production',process.cwd(),'VITE_');
const enabled=environment.VITE_BETA_ENABLED;
if(enabled!==undefined&&!['true','false'].includes(enabled))throw new Error('VITE_BETA_ENABLED must be true or false.');
const raw=(environment.VITE_API_BASE_URL??'').trim();
if(enabled==='true'&&!raw)throw new Error('Private beta build requires VITE_API_BASE_URL.');
let apiOrigin='';
if(raw) {
  const url=new URL(raw);
  if(url.protocol!=='https:'||url.username||url.password||url.search||url.hash||!['','/'].includes(url.pathname))throw new Error('API base must be an HTTPS origin without credentials or paths.');
  apiOrigin=url.origin;
}
// Headers live in generated dist, never a private configuration file. Exact
// connect-src follows the configured API; no wildcard exfiltration destination.
const policy=`default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self' ${apiOrigin}; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'`;
writeFileSync(new URL('../dist/_headers',import.meta.url),`/*\n  Content-Security-Policy: ${policy}\n  X-Content-Type-Options: nosniff\n  Referrer-Policy: no-referrer\n  Permissions-Policy: camera=(), microphone=(), geolocation=()\n  Strict-Transport-Security: max-age=31536000\n`);
