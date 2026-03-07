# CLAUDE.md — opal
# Super Workflow Master Router v1.0 + opal project context
# DD-001: Claude Code primary runtime | DD-004: Planning owns state, Superpowers owns process

---

## ⚡ STARTUP SEQUENCE (run on every task before anything else)

### Step 1 — State Check
Check for plan files at `.workflow/task_plan.md` in the project root.

IF `.workflow/task_plan.md` does NOT exist AND the task is non-trivial:
  → Create `.workflow/` directory if needed
  → Invoke `planning/planning-with-files` skill to create:
      .workflow/task_plan.md   (phases and checklist)
      .workflow/findings.md    (research and decisions)
      .workflow/progress.md    (session log)
  → READ .workflow/task_plan.md before proceeding

IF `.workflow/task_plan.md` EXISTS:
  → READ .workflow/task_plan.md now
  → Identify the current phase and the next incomplete step

### Step 2 — Discipline Check
Invoke `superpowers/using-superpowers` from the shared registry.
  → Identify relevant PROCESS skills (brainstorming, writing-plans, debugging)
  → Invoke process skills BEFORE implementation skills
  → Do NOT skip this step — process-first prevents rework

### Step 3 — Skill Selection
Select a skill using this precedence order (highest trust first):

  1. core/          ← Shared registry: Anthropic official (docx, pdf, pptx, xlsx, frontend-design)
  2. superpowers/   ← Shared registry: Process skills
  3. planning/      ← Shared registry: planning-with-files
  4. local/         ← Opal project skills (marketing, CRO, SEO — via skills-lock.json)
  5. community/     ← Shared registry: Vercel, Cloudflare, HuggingFace, Stripe
  6. custom/        ← Shared registry: Domain-specific

  Shared registry path: ~/projects/super-workflow/.claude/skills/
  Local skills: managed via skills-lock.json in this repo

  If NO skill matches: proceed without a skill, log gap to .workflow/findings.md
  under "Skill Gaps Identified".

---

## SKILL QUICK REFERENCE

| Task Type                         | Skill(s)                                              |
|-----------------------------------|-------------------------------------------------------|
| Word document                     | core/docx                                             |
| PDF                               | core/pdf                                              |
| Presentation                      | core/pptx                                             |
| Spreadsheet                       | core/xlsx                                             |
| Frontend / React / Vite           | community/react-best-practices, core/frontend-design  |
| Azure deployment                  | STOP — requires CONFIRM (see irreversibility protocol)|
| Payments / Mollie / Stripe        | community/stripe-best-practices                       |
| Database / PostgreSQL             | (SQLAlchemy patterns in shared/db_sqlalchemy.py)      |
| Marketing copy / SEO / CRO        | local/copywriting, local/seo-audit, local/page-cro   |
| Launch / go-to-market             | local/launch-strategy, local/marketing-ideas          |
| Email sequences                   | local/email-sequence, local/cold-email                |
| Brainstorming / design            | superpowers/brainstorming → superpowers/writing-plans |
| Debugging                         | superpowers/systematic-debugging                      |
| New skill creation                | core/skill-creator                                    |
| Complex new task                  | planning/planning-with-files                          |

---

## IRREVERSIBLE ACTION PROTOCOL (DD-011)

STOP and present a summary with estimated impact, then wait for explicit confirmation:

  REQUIRES CONFIRMATION:
  - Any Azure deployment (staging OR production — opal has real Azure costs)
  - Azure resource creation (VMs, storage, service bus, DB instances)
  - Mollie payment webhook changes or billing configuration
  - Sending external communications (email, webhooks)
  - Destructive DB operations (DROP, TRUNCATE, DELETE without WHERE)
  - Using stored credentials in a new context

  DOES NOT REQUIRE CONFIRMATION:
  - Local Docker Compose operations
  - Running tests
  - Creating or editing local files
  - Read operations

  Format: "IRREVERSIBLE ACTION PENDING: [description] | Estimated impact: [cost/scope]
           Type CONFIRM to proceed or ABORT to stop."

---

## ERROR RECOVERY (3-STRIKE PROTOCOL)

If the same step fails 3 consecutive times:
  1. STOP — do not retry the same approach
  2. Log failure to Error Log table in .workflow/task_plan.md
  3. Log details to .workflow/progress.md
  4. Mutate approach: different method, tool, or order
  5. If no alternative: write escalation notice to .workflow/progress.md and halt

Rule: next_action MUST NOT equal the action that just failed.

---

## PLAN FILE RULES

- Plan files live at `.workflow/` in the project root (symlinked to super-workflow)
- UPDATE .workflow/progress.md after every completed phase
- UPDATE .workflow/findings.md after every 2 tool operations
- UPDATE .workflow/task_plan.md checklist as items complete: [ ] → [x]
- NEVER mark a phase complete unless ALL checklist items are [x] or [N/A]
- RE-READ .workflow/task_plan.md before every significant tool use

---

## LAYER CONFLICT RESOLUTION (DD-004)

- STATE decisions (what phase, what step, what failed): Planning-with-Files wins
- PROCESS decisions (how to approach, which skills): Superpowers wins
- When in doubt: .workflow/task_plan.md is the single source of truth

---

# ─────────────────────────────────────────────────────────────────
# OPAL PROJECT CONTEXT (preserve exactly — project-specific knowledge)
# ─────────────────────────────────────────────────────────────────

## Build & Run Commands

### Backend (Python 3.11+ / FastAPI)
```bash
# Run web API locally
cd src/web_api && python -m uvicorn web_api.main:app --reload --port 8080

# Run with Docker Compose (all services)
docker-compose up -d
```

### Frontend (React 19 / Vite)
```bash
cd frontend && npm install && npm run dev     # Dev server on :5173
cd frontend && npm run build                  # Production build (tsc -b && vite build)
cd frontend && npm run lint                   # ESLint
```

### Tests
```bash
# Run all tests (97 tests)
PYTHONPATH=src/shared:src/pipeline_worker:src/web_api python3.12 -m pytest tests/ -x

# Run a single test file
PYTHONPATH=src/shared:src/pipeline_worker:src/web_api python3.12 -m pytest tests/test_pipeline_worker.py -x

# Run a single test
PYTHONPATH=src/shared:src/pipeline_worker:src/web_api python3.12 -m pytest tests/test_pipeline_worker.py::test_name -x
```

The `PYTHONPATH` is required because services are structured as separate packages under `src/`
that import each other.

## Architecture

### Monorepo Layout
```
src/
  shared/shared/       # Shared library: models, config, DB, storage, queue, encryption
  web_api/web_api/     # FastAPI REST API (entry: main.py → uvicorn)
  pipeline_worker/     # Single worker: bg-removal → scene-gen → upscale (in-memory pipeline)
  export_worker/       # Batch export / ZIP packaging
  billing_service/     # Usage tracking (token-based billing)
  orchestrator/        # Queue dispatcher (legacy, replaced by pipeline_worker)
  bg_removal_worker/   # Standalone bg-removal (legacy)
  scene_worker/        # Standalone scene-gen (legacy)
  upscale_worker/      # Standalone upscale (legacy)
frontend/src/          # React 19 SPA (Vite, TanStack Query, MSAL.js)
migrations/            # Sequential SQL migrations (001-010)
infra/                 # Azure Bicep templates (main.bicep)
```

### Key Patterns

**Shared library (`src/shared/shared/`)**: All services import from `shared.*`. Config is via
`pydantic-settings` (`config.py` → `Settings` class). Runtime settings use
`settings_service.get_setting()` which checks DB `admin_settings` table first, then falls back
to env vars.

**Auth dual-path (`web_api/auth.py`)**: Requests authenticate via JWT (Entra External ID) or
API key (`X-API-Key` header). `get_current_user()` returns
`{user_id, tenant_id, email, token_balance}`. API key users get unlimited tokens (999999).
JIT user provisioning on first JWT login — no registration endpoint.

**Docker builds**: Each service has its own Dockerfile. The shared library is copied as
`COPY src/shared/shared /app/shared` (not installed as a package). `PYTHONPATH=/app` makes
`import shared.*` work in containers.

**Vite proxy**: Frontend dev server proxies `/v1/*`, `/healthz`, `/debug` to `localhost:8080`.

**Database**: SQLAlchemy ORM with PostgreSQL. Models in `shared/models.py`. Sessions via
`shared/db.SessionLocal`. No ORM migrations — raw SQL files in `migrations/`.

**Queue**: Azure Service Bus in production (`shared/servicebus.py`), database-backed queue for
local dev (`shared/queue_database.py`). Selected via `QUEUE_BACKEND` env var.

**Storage**: Azure Blob Storage (`shared/storage.py`). Containers: `raw`, `outputs`, `exports`.

**Billing**: Token-based. Atomic deduction at job creation
(`UPDATE ... SET token_balance = token_balance - N WHERE token_balance >= N`).
Mollie payment webhooks always re-fetch status from Mollie API (never trust webhook body).

### Frontend Structure
Single-page app with tab navigation. `App.tsx` handles auth state (MSAL) and renders either
`LandingPage` (unauthenticated) or the tabbed app. API client in `api.ts` with optional Bearer
token. Components map 1:1 to tabs.

### Web API Routes
All routes under `/v1/` prefix. Auth applied at router level in `main.py` via
`dependencies=[Depends(get_current_user)]`. Public routes: `/healthz`, `/v1/billing/packages`.
Admin routes use their own `require_admin` dependency.
GDPR webhooks are HMAC-verified, not auth-gated.

### Pipeline Worker
Runs all three stages (bg-removal → scene-gen → upscale) in a single worker process,
in-memory. Providers: rembg (ONNX) for bg-removal, fal.ai FLUX-dev for scene generation,
Real-ESRGAN for upscaling. Listens on Service Bus `jobs` queue with 600s lock renewal.

## Testing Conventions
- Tests patch `get_setting` (from `shared.settings_service`) rather than patching the settings
  module directly
- No conftest.py — test files are self-contained with inline fixtures
- Test files in `tests/` at repo root
