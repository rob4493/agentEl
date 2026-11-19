# Agent EL

**Agent EL**, or **EL** for short, is an English email workspace designed to help a sender communicate with a mixed professional audience. It produces one shared draft for review, rather than separate recipient-specific messages.

This is an independent project. It is not an official United Nations application, partnership or endorsed project.

Repository: [rob4493/agentEl](https://github.com/rob4493/agentEl).

## Current functionality

The local prototype follows **Confirm → Improve and Compare → Decide**:

- Paste an English email and specify the group, stated technical background, objectives, known preferences and required details.
- Clarify selected action/deadline/approval expressions before generation. These deterministic rules are limited; they do not detect every ambiguity.
- Generate one draft using a replaceable provider: mock mode by default, or explicitly configured local Ollama.
- Compare source and output, inspect source passages and sender-confirmed context, and review deterministic wording, number, date and targeted content warnings.
- Inspect selected observable communication changes. These descriptions are comparisons, not the model's internal reasoning.
- Edit and revalidate, reject, regenerate, or explicitly approve the current draft before copying. Changes revoke prior checks and approval. The application does not send email.
- Optionally request experimental structured AI meaning review. It adds one local inference call using the same model as generation and is not an independent accuracy check.

Mock mode only adjusts paragraph spacing and labels its output as a demonstration; it is not an AI rewrite. Real AI output can invent or omit information. Neither deterministic checks nor optional model review establishes semantic equivalence. The sender must review the exact final content.

## Technology stack

- React, TypeScript, Vite and responsive CSS.
- Python, FastAPI, Pydantic, Uvicorn and pytest.
- Vitest for frontend review-state tests.
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

The provider defaults to mock. Load the synthetic example or paste a draft, confirm the audience, then choose **Confirm & improve**. Answer any clarification questions and try again. Review comparison/findings, edit and revalidate as necessary, and explicitly approve before copying.

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
| `POST /api/review` | Explicit, experimental same-model review; separate completed/unavailable status |

Interactive request/response schemas are available at [the backend API docs](http://127.0.0.1:8000/docs) while the server runs. Source text, sender-confirmed context, generated content, deterministic findings and model interpretations remain distinct. Model review never promotes an interpretation into an established source fact or automatically approves a draft.

## Known limitations and privacy

- Keyword/lexical checks have false positives and missed errors. Conservative wording warnings also flag legitimate paraphrases. Numbers are compared as sets, and date/entity/negation handling is limited.
- AI generation can invent attachments, claims, praise, commitments or framing despite its instructions. Human editing and review remain necessary.
- Optional review uses the same model, can repeat generation errors and can be wrong even with exact quotations. Empty findings never mean fully verified meaning.
- Source character limits do not guarantee that source plus audience context fits the model's loaded token context. Long inputs, cold starts, concurrency and request cancellation need further evaluation.
- The UI supports local review; approval is not a signed audit record. Automated frontend tests are state tests, not comprehensive browser, clipboard, accessibility or device certification.
- The application is designed for English; it does not enforce language detection. Personalized Mode C and multilingual generation are not implemented.
- Drafts are held in application memory without a user database or intentional server-side draft persistence. There are no email account integrations, automatic sending or hosted AI providers. OS clipboard history and Ollama's own behavior are outside application control.
- This is a loopback development prototype without authentication, production TLS, rate limiting or a transport body-size cap. CORS is not authentication. Do not expose the development servers as a public service. Treat drafts as untrusted data; prompt separation is not proven resistance to prompt injection.
