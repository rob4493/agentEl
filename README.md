# Ritmo

**Ritmo** (formerly Agent EL) is a human-centered AI communication-learning platform and English email workspace. It helps people understand communication styles and adapt their writing while retaining control of their intended message. AI suggestions require human review; Ritmo does not send email.

This is an independent project. It is not an official United Nations application, partnership or endorsed project.

Repository: [rob4493/agentEl](https://github.com/rob4493/agentEl).

## Current functionality

The local prototype follows **Discover → Understand → Compose → Review** across four screens:

- **Discover:** explore Expressive, Amiable, Driver and Analytical communication through an interactive educational carousel. These are contextual writing patterns, not permanent personality labels.
- **Understand:** optionally analyze a received email, then confirm or override the tentative reader-style suggestion before proceeding.
- **Compose:** write an original response, choose a reader style and request a local Ollama adaptation. Incoming messages supply context; the original response remains authoritative. General clarity improvement and limited ambiguity clarification are also available.
- **Review:** compare the original and suggestion, inspect warnings, edit and revalidate, regenerate or reject. Explicitly approve the current revision before copying. Editing source, audience or output revokes earlier validation and approval.

Optional experimental AI meaning review adds one inference with the same model; it is not an independent accuracy check. Internal editing experiments and evaluation reports are not production features.

Discover introduces four writing patterns; Understand analyzes an optional received email only when requested, using the configured local Ollama model. It displays Ritmo's tentative writing-style suggestion, a brief style description, and the established course guidance for communicating with the selected reader. Source evidence is validated internally and is not displayed in the result panel. Exact source matching does not establish that a style interpretation is correct. Users must confirm or override the suggestion (or explicitly choose Inconclusive) before continuing from Understand to Compose. Editing invalidates prior analysis and selection. Compose displays the incoming message and carries forward only an explicitly confirmed or manually selected target style. Its local Ollama adaptation uses the original response as the source of truth; incoming text is untrusted background, not permission to add facts. Writer-style analysis and personalized learning summaries remain planned. Mock mode does not fabricate reader analysis. Compose contains the working email workspace; Review reuses its comparison, findings and explicit approval controls. Navigation preserves entered values until the page is reloaded.

The Compose workspace has side-by-side editors on desktop and stacked editors on small screens, editable audience and goal suggestions with optional preferences below the original draft, a key-change summary, and expandable review panels. Approve and Copy approved are separate actions. The header reports backend availability and the configured provider; it does not claim that Ollama or a model is connected based on service health alone.

Mock mode only adjusts paragraph spacing and labels its output as a demonstration; it is not an AI rewrite. Real AI output can invent or omit information. Neither deterministic checks nor optional model review establishes semantic equivalence. The sender must review the exact final content.

Reader analysis is experimental: exact quotes do not validate style interpretations. Short samples may be inconclusive, model responses may be rejected, and styles may overlap. In local development, received emails remain in application memory and are processed through local Ollama. Remote access introduces network intermediaries; avoid secrets or confidential content you are not authorized to use.

## Technology stack

- React, TypeScript, Vite and responsive CSS.
- Python, FastAPI, Pydantic, Uvicorn and pytest.
- Vitest for frontend state, transport and component rendering tests.
- Optional local Ollama with `qwen3.5:4b` as the default model candidate.

Frontend dependency resolutions are in `frontend/package-lock.json`; backend dependency ranges are in `backend/requirements.txt`.

## Installation

Prerequisites: Python 3.12 or later, Node.js 22 or later with npm, and Git. Ollama is optional for mock development. Examples assume you are at the repository root.

```sh
git clone https://github.com/rob4493/agentEl.git
cd agentEl
```

Create and activate a virtual environment.

PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

macOS/Linux:

```sh
python3 -m venv .venv
source .venv/bin/activate
```

With that environment activated:

```sh
python -m pip install -r backend/requirements.txt
npm ci --prefix frontend
```

If activation is unavailable, invoke the environment interpreter directly instead of changing security settings: `.\.venv\Scripts\python.exe` on Windows or `.venv/bin/python` on macOS/Linux.

## Run locally

Start the backend from the repository root, with the Python environment activated:

```sh
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

In a second terminal, start the frontend:

```sh
npm run dev --prefix frontend
```

Open [the workspace](http://127.0.0.1:5173). If that port is occupied, run `npm run dev --prefix frontend -- --port 5174` and open [port 5174](http://127.0.0.1:5174). Vite proxies `/api` to the backend on port 8000.

The provider defaults to mock. Choose Get Started, enter an optional incoming email in Understand, and explicitly select/confirm a reader style. In Compose, write your own response, choose a target style if needed, then select **Adapt my response**. Style adaptation requires the configured local Ollama provider; mock mode returns an honest unavailable result, not a fabricated adaptation. **Improve clarity only** retains the existing general improvement/mock workflow. Answer any clarification questions, then review both drafts and warnings in Review. Edit and revalidate as needed, and explicitly approve before copying. Example loaders do not overwrite a nonempty response.

## Enable local Ollama generation

Install Ollama separately and ensure it is running with `qwen3.5:4b` already available. Check the installed models with:

```sh
ollama list
```

If the model is missing, obtain it manually through Ollama before selecting the provider. Project installation and application startup do not download or install models. Model weights are not part of this repository.

Set environment variables in the backend terminal **before** starting or restarting Uvicorn.

PowerShell:

```powershell
$env:COMMUNICATION_PROVIDER = 'ollama'
$env:OLLAMA_BASE_URL = 'http://127.0.0.1:11434'
$env:OLLAMA_MODEL = 'qwen3.5:4b'
```

macOS/Linux:

```sh
export COMMUNICATION_PROVIDER=ollama
export OLLAMA_BASE_URL=http://127.0.0.1:11434
export OLLAMA_MODEL=qwen3.5:4b
```

Use `COMMUNICATION_PROVIDER=mock` to select demonstrations explicitly. No `.env` loader is configured; setting process variables is required. Connection settings remain configurable, but the provider accepts only loopback HTTP inference and never silently switches to mock or a cloud service when a real request fails.

Ollama calls request `think: false` and consume only final message content. Explicit leaked reasoning tags or malformed/incomplete output cause a provider failure. Generation retains a 60-second socket timeout, which is not a strict end-to-end wall-clock deadline. Optional AI review may take substantial additional time, fail, misclassify differences or supply unusable evidence; unavailable review is reported explicitly.

## Controlled remote beta — prepared, not activated

The intended controlled-beta architecture is:

```text
Netlify-hosted frontend -> HTTPS Cloudflare Tunnel -> local FastAPI -> local Ollama
```

For direct browser-to-API requests, Netlify hosts the static frontend and Cloudflare carries API traffic. Local inference does not mean remote email submissions stay entirely on the user's device. A proxy through Netlify would introduce another service into that data path.

The checkout includes opt-in beta authentication with individually revocable, expiring access codes; exact-origin CORS; actual-byte request limits; bounded per-code/IP rate controls; one active inference worker; restricted documentation; and no-store API responses. Codes stay in browser memory and private operator files store only verifiers. Authentication does not establish model accuracy. Local development remains unchanged when beta mode is disabled.

`netlify.toml` builds `frontend` using `npm run build` and publishes `dist`. Set build variables `VITE_BETA_ENABLED=true` and `VITE_API_BASE_URL` to the approved HTTPS API **origin without `/api`**. All frontend API calls, including health and reader analysis, use this centralized base. Production beta builds fail if it is missing or invalid. Generated security headers restrict API connections to the configured origin. Never place access codes, hashes or Cloudflare secrets in frontend bundles or `VITE_*` variables. Preview builds intentionally fail closed until separately configured/approved.

The confirmed frontend origin is `https://ritmoagent.netlify.app`; the initial API uses a Cloudflare Quick Tunnel whose URL is not yet assigned. Every new Quick Tunnel hostname requires updating the API build variable and rebuilding/redeploying. Keep FastAPI on `127.0.0.1:8000` and Ollama on `127.0.0.1:11434`; never expose Ollama, Vite or test servers. Use one backend worker. Before exposing anything, generate private codes, enable backend beta mode, verify unauthenticated calls are rejected and obtain tunnel/deployment approval. No external connectivity is certified by the local tests.

See [the beta operator guide](docs/privateBetaSetup.md) for exact Netlify settings, private credential-generation/revocation commands, backend startup, limits and approval-gated Quick Tunnel instructions. No real credentials/configuration belong in Git. Developer-tool advisories remain under review; no automatic major dependency upgrade has been applied.

No application script provisions a tunnel or sends email. A connected Netlify site can automatically deploy after a Git push/merge; keep automatic publishing disabled or obtain explicit deployment approval first. Preserve the existing human review and approval safeguards.

## Tests and build

With the Python environment activated, from the repository root:

```sh
python -m pytest -c backend/pytest.ini backend/tests
npm test --prefix frontend
npm run build --prefix frontend
```

The backend suite uses mock/stub inference and deterministic assertions; it requires neither Ollama nor network model inference. It covers API contracts, provider response/error handling, clarification/source evidence, selected meaning-change scenarios and optional-review safeguards. Frontend tests exercise revision-bound validation/approval state. Passing tests does not establish general model accuracy or complete browser behavior.

`npm run build` writes frontend output to `frontend/dist`; it is a build check, not a deployed application. Build output, virtual environments, dependencies, caches, secrets and local model files are excluded from Git.

## Source layout and API

- `frontend/src/`: workspace, typed API client, finding display and review-state logic.
- `backend/app/`: schemas, clarification/fact extraction, generation workflow, deterministic comparison, optional model review and replaceable providers.
- `backend/tests/`: automated backend tests.
- `evaluation/fixtures/stagingEmail.json`: synthetic release example used by the frontend and backend tests.
- `evaluation/fixtures/communicationScenarios.json`: synthetic correct/incorrect accessibility, praise, action, negative-result, commitment and release scenarios used by tests.

The fixtures are source/test inputs, not real correspondence or raw model reports. Their dates and facts remain fixed for reproducible checks.

| Endpoint | Purpose |
| --- | --- |
| `GET /api/health` | Service/configuration status; does not probe model readiness |
| `POST /api/analyze` | Deterministic source facts, context and selected ambiguity questions |
| `POST /api/improve` | One shared draft and deterministic review; unresolved ambiguity returns 409 |
| `POST /api/validate` | Recompute deterministic warnings and observable changes after editing |
| `POST /api/adaptResponse` | One local style-adaptation call from receivedEmail, originalDraft and explicit targetStyle (plus audience/clarifications); returns suggestion, model-described changes and preservation warnings |
| `POST /api/adaptResponse/validate` | Recheck an edited response, including conservative qualification and incoming-passage warnings |
| `POST /api/readerAnalysis` | Requested local received-email writing observations, verified quotes, uncertainty and limitations |
| `POST /api/review` | Explicit, experimental same-model review; separate completed/unavailable status |

Interactive request/response schemas are available at [the backend API docs](http://127.0.0.1:8000/docs) while the server runs. Source text, sender-confirmed context, generated content, deterministic findings and model interpretations remain distinct. Model review never promotes an interpretation into an established source fact or automatically approves a draft.

## Known limitations and privacy

- Keyword/lexical checks have false positives and missed errors. Conservative wording warnings also flag legitimate paraphrases. Numbers are compared as sets, and date/entity/negation handling is limited.
- AI generation can invent attachments, claims, praise, commitments or framing despite its instructions. Human editing and review remain necessary.
- Optional review uses the same model, can repeat generation errors and can be wrong even with exact quotations. Empty findings never mean fully verified meaning.
- Source character limits do not guarantee that source plus audience context fits the model's loaded token context. Long inputs, cold starts, concurrency and request cancellation need further evaluation.
- The UI supports local review; approval is not a signed audit record. Automated frontend tests are state tests, not comprehensive browser, clipboard, accessibility or device certification.
- The application is designed for English; it does not enforce language detection. Personalized Mode C and multilingual generation are not implemented.
- Four synthetic Compose scenarios are available only in the Vite development build. They expose intended demonstration styles separately from live classifications and require explicit loading/normal human style selection. Their starter responses load only into an empty editor; they are not validated accuracy examples.
- Adaptation can omit qualifications or invent explanations even when amounts/dates remain unchanged. Model-described style changes also require review. Conservative checks can warn about legitimate paraphrases and miss altered names, nuanced commitments or paraphrased incoming additions.
- Compose checks also flag some changed word quantities, weekdays/times, sender sign-offs, commitment strength, conditions and status transitions. These warnings are incomplete heuristics; a clear prompt and an empty warning list do not establish faithful meaning or correct style.
- Drafts are held in application memory without a user database or intentional server-side draft persistence. There are no email account integrations, automatic sending or hosted AI providers. OS clipboard history and Ollama's own behavior are outside application control.
- Default local development mode is intentionally unauthenticated and must remain loopback-only. Explicit beta mode adds access codes and request controls but is not a production-security certification, distributed service or proven prompt-injection defense. Static frontend assets remain public; API data/inference is protected by the backend, not by hiding frontend controls. Expiry/revocation blocks new requests, not already received content or admitted inference. Deployment and tunnel activation require separate approval.
