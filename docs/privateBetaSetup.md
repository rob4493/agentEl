# Ritmo controlled private beta

Prepared configuration, not an activated deployment. Nothing in this guide authorizes a Git push, Netlify deployment or tunnel activation. Obtain explicit approval before those actions. Preserve the `codex/ritmo-publication` review-branch/PR strategy.

## Architecture and privacy

```text
Browser running Netlify frontend
  -> HTTPS Cloudflare Quick Tunnel
  -> FastAPI at 127.0.0.1:8000
  -> Ollama at 127.0.0.1:11434
```

Frontend origin: **https://ritmoagent.netlify.app**. API origin: **pending Quick Tunnel startup**. Both remain configurable. No Netlify `/api` proxy: existing inference can exceed Netlify's proxy timeout. The browser contacts the tunnel directly. Cloudflare terminates HTTPS and carries email content and authorization headers; local inference does not mean local-only transmission. Netlify serves static assets, not email proxy requests. No cloud model fallback or automatic sending.

Codes represent possession, not verified personal identity or MFA. Issue a separate high-entropy code per reviewer; never share one code across the beta. Use fictional/non-confidential emails initially. Source matching and validation still do not establish semantic equivalence; keep all review, override, revalidation and approval controls.

## Netlify configuration — apply only after deployment approval

`netlify.toml` defines base `frontend`, command `npm run build`, publish `dist`, Node 22, `VITE_BETA_ENABLED=true`. Configure the site build environment:

| Variable | Value |
| --- | --- |
| `VITE_BETA_ENABLED` | `true` |
| `VITE_API_BASE_URL` | The actual `https://…trycloudflare.com` origin, **without `/api`**, once available |

Never put codes, hashes, Cloudflare credentials or backend secrets in Netlify or `VITE_*` variables. Vite exposes `VITE_*` values to browsers. A missing/invalid HTTPS API origin fails the beta build. Builds write CSP and security headers to `dist/_headers`; `connect-src` includes only self and the exact configured API origin. Inline styles remain allowed for existing style accents; script execution does not allow inline/eval. No wildcard API destination.

Deploy-preview and branch-deploy contexts intentionally clear the API origin and fail closed, preventing accidental production API use by unapproved preview origins. To enable a preview later, explicitly approve its exact origin, change the corresponding build context/API origin and backend CORS configuration, then rebuild. Do not allow all `*.netlify.app` sites.

**Every new Quick Tunnel hostname requires updating `VITE_API_BASE_URL` and rebuilding/redeploying.** An existing build cannot discover the new URL; its CSP deliberately rejects a different destination. Quick Tunnels are temporary development/testing endpoints without a production uptime guarantee. A named tunnel/custom domain is a future option, not required or provisioned here.

## Private credential setup — operator commands, not executed automatically

Use the existing Python environment from the repository root. Store beta data outside the repository and outside cloud-synchronized development directories:

```powershell
$env:PYTHONPATH = (Resolve-Path backend).Path
$betaPrivateDirectory = Join-Path $env:LOCALAPPDATA 'RitmoBeta'
New-Item -ItemType Directory -Path $betaPrivateDirectory -Force | Out-Null
$betaOperator = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
icacls $betaPrivateDirectory /inheritance:r /grant:r "${betaOperator}:(OI)(CI)F" 'SYSTEM:(OI)(CI)F'
if ($LASTEXITCODE -ne 0) { throw 'Private directory ACL configuration failed; stop.' }
icacls $betaPrivateDirectory
$env:BETA_CODE_FILE = Join-Path $betaPrivateDirectory 'accessCodes.json'
python -m app.betaCodes create --file "$env:BETA_CODE_FILE" --id reviewer01 --days 14
```

The last command prints the new code **once**. Do not run in a recorded/transcribed shell, copy it into source/README/chat/build settings, or redirect it to a repository file. Deliver it privately using your chosen secure channel; this project does not send invitations. The store contains only opaque IDs, SHA-256 verifiers of 256-bit random bearer codes, enablement and expiry. These are cryptographically random codes, not user-chosen passwords; never substitute low-entropy passwords. Restrict local file ACLs as above. Do not publish the store or hashes. Default lifetime is 14 days; allowed 1–90 days. Maximum 128 unique IDs; revoked IDs cannot be reused.

Issue another reviewer independently:

```powershell
python -m app.betaCodes create --file "$env:BETA_CODE_FILE" --id reviewer02 --days 14
```

Revoke one code without restarting FastAPI:

```powershell
python -m app.betaCodes revoke --file "$env:BETA_CODE_FILE" --id reviewer01
```

The backend rereads the private store on each request. Revocation/expiry blocks subsequent requests immediately; already admitted local inference is not cancelled. Invalid/missing stores fail closed. Atomic replacement prevents partial reads; operator updates use an exclusive lock. After an interrupted operator command, inspect any stale `.lock`/`.tmp` file and confirm no operator process is active before manually removing it. Do not bypass locks or edit hashes into a public configuration file.

Codes stay only in browser module memory, in password inputs while entering, and in HTTPS Authorization headers; not URLs, cookies, localStorage or sessionStorage. Refresh requires reentry. Locking/expiry hides but does not destroy an existing draft; reentry restores the tab's current workflow. Reload/close to clear in-memory drafts. Hidden UI is not a security boundary on a shared computer, and browser extensions/devtools/OS memory are outside this application guarantee.

## Backend startup

From repository root in the configured Python environment:

```powershell
$env:PYTHONPATH = (Resolve-Path backend).Path
$env:COMMUNICATION_PROVIDER = 'ollama'
$env:OLLAMA_BASE_URL = 'http://127.0.0.1:11434'
$env:OLLAMA_MODEL = 'qwen3.5:4b'
$env:BETA_ENABLED = 'true'
$env:BETA_ALLOWED_ORIGINS = 'https://ritmoagent.netlify.app'
$env:BETA_CODE_FILE = Join-Path $env:LOCALAPPDATA 'RitmoBeta\accessCodes.json'
$env:BETA_MAX_REQUEST_BYTES = '262144'
$env:BETA_MAX_REQUESTS = '8'
$env:BETA_REQUESTS_PER_MINUTE = '60'
$env:BETA_INFERENCES_PER_MINUTE = '4'
$env:BETA_FAILED_AUTH_PER_MINUTE = '10'
$env:BETA_TRUST_CLOUDFLARE_IP = 'true'
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --workers 1 --no-proxy-headers --no-access-log
```

Stop the existing development process deliberately before starting this beta process; do not start a second listener or assume the currently running process has reloaded configuration. No `--reload` or multiple workers. `BETA_ENABLED=false`/unset preserves local development behavior and **must never be tunneled**. Beta startup requires local Ollama explicitly selected, an exact HTTPS origin and valid private store. Model installation/download is not automatic. The operator must keep Ollama loopback-only and confirm the intended model is ready; health does not probe it.

One Ollama generation/review may be active across all inference routes per process. Busy inference returns 503/Retry-After without queuing another inference. Eight total active requests, 256-KiB actual body cap (including chunked bodies), ten-second total upload deadline, 60 requests/minute/code and four inference attempts/minute/code are defaults. Invalid-code attempts have bounded per-IP counters. Limits count attempts, including failed requests, and reset with the one backend process. No distributed limiter or volumetric-DDoS guarantee.

`BETA_TRUST_CLOUDFLARE_IP=true` is appropriate **only** with a loopback-only origin reached by cloudflared and `--no-proxy-headers`. The application then accepts Cloudflare's overwritten `CF-Connecting-IP` only from loopback, never arbitrary forwarded-for headers. Set false if those trust conditions are not satisfied; in that case tunnel failures share the loopback IP bucket. Valid authenticated codes have independent quotas. All codes are bearer credentials and should be kept private even though origins are restricted.

Every `/api` route including health requires a code. Permitted CORS preflights do not; CORS alone grants no access. Docs/OpenAPI/non-API paths are disabled in beta. Sensitive API responses are no-store; beta 422 errors omit source inputs. Routine diagnostics contain no bodies, codes, verifiers or raw model output. Existing local-only model transport, exact quotation validation, AI contracts and human-approval rules remain unchanged. The Ollama socket timeout remains 60 seconds; frontend inference deadline 70 seconds and access/health checks ten seconds. A browser abort does not stop a running worker; the actual inference slot is held until the worker finishes.

An authenticated beta health response also reports `betaAccessVerified=true`; local development reports false. The frontend refuses to unlock against a development-mode or mock backend even if it returns HTTP 200. This check is additional misconfiguration detection, not a substitute for verifying unauthenticated rejection at the origin.

Local checks after the beta process is deliberately started (no model inference):

```powershell
curl.exe -i http://127.0.0.1:8000/api/health
# Expected: 401, never an unauthenticated 200.
curl.exe -i -X OPTIONS http://127.0.0.1:8000/api/readerAnalysis -H 'Origin: https://ritmoagent.netlify.app' -H 'Access-Control-Request-Method: POST' -H 'Access-Control-Request-Headers: authorization,content-type'
# Expected: allowed preflight for this exact origin only.
$betaCodeInput = Read-Host 'Individual beta code (not recorded in command history)' -AsSecureString
$betaToken = [System.Net.NetworkCredential]::new('', $betaCodeInput).Password
try {
  Invoke-RestMethod http://127.0.0.1:8000/api/health -Headers @{Authorization="Bearer $betaToken"}
  # Expected: status=ok, provider=ollama, betaAccessVerified=true; model readiness remains notChecked.
} finally { Remove-Variable betaToken,betaCodeInput }
```

## Cloudflare Quick Tunnel — activation requires explicit approval

No Cloudflare login, named tunnel creation or credential files are required for this initial Quick Tunnel. With the secured beta backend running and locally tested, the operator may run **only after approval**:

```powershell
# Safety check: never publish the still-open development process by accident.
$betaProbeStatus = 0
try {
  $betaProbeStatus = [int](Invoke-WebRequest http://127.0.0.1:8000/api/health -UseBasicParsing).StatusCode
} catch {
  if ($null -eq $_.Exception.Response) { throw }
  $betaProbeStatus = [int]$_.Exception.Response.StatusCode
}
if ($betaProbeStatus -ne 401) { throw 'Origin is not rejecting anonymous access; do not activate the tunnel.' }
# Execute the next command ONLY after explicit tunnel activation approval.
cloudflared tunnel --url http://127.0.0.1:8000
```

Record the HTTPS `trycloudflare.com` origin printed by cloudflared. It is a public address, not an access credential. Update Netlify's build environment with that exact origin, then obtain deployment approval and rebuild. Do not tunnel port 11434 or Vite's development/test server. Do not disable beta auth to troubleshoot CORS. Quick Tunnel forwards host paths, so the application's beta boundary deliberately rejects non-API routes and all API calls require authorization. No Ollama administration/forwarding routes are exposed by FastAPI.

Quick Tunnel service is for testing; hostname changes, desktop sleep/offline status, model timeout, or stopping cloudflared interrupt the beta. If a local cloudflared config prevents Quick Tunnel startup, follow Cloudflare's troubleshooting guidance; do not automatically delete existing configuration/credentials. This implementation does not activate or modify your installed tunnel.

See [Cloudflare's Quick Tunnel guidance](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/). Do not add an interactive edge email-login layer without separately testing its cross-origin browser behavior; this configuration uses backend bearer-code authentication.

If the GitHub repository is connected to Netlify, a future push/merge can trigger automatic deployment. Keep automatic publishing disabled or obtain explicit deployment approval before such a push; Git publication approval alone must not silently authorize deployment. No push or Netlify account settings are changed here.

## Checks before admitting testers

1. Confirm both listeners are loopback-only and the beta process, not the old dev process, owns port 8000.
2. Confirm unauthenticated health returns 401; allowed Netlify preflight works; unrelated origins are rejected.
3. In the deployed site, enter a separate reviewer code and test Understand → Compose → Review with synthetic text; never bypass review/approval.
4. Revoke a test reviewer and verify its next API request returns 401 while another code still works. Test expiry, quota, capacity and safe failures.
5. Confirm docs/internal/Ollama paths are unavailable, no codes appear in URLs/storage/logs, and no private config/reports are deployed.
6. Check CSP/browser errors against the current Quick Tunnel URL. Verify stale results, draft retention on access lock and revalidation/approval behavior in a real browser.

External checks cannot be completed before the tunnel URL exists and deployment/activation are approved. Local automated tests use synthetic codes/stub inference, not real beta credentials or live email. Open development-tool advisories are documented in the private implementation report; no automatic major upgrade is performed. Keep developer/test servers private and do not run untrusted tests with production secrets.
