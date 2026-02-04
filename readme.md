# Opal — Ghost Product Photographer (Workflow-first)

This repo is designed so you:
- Develop locally on any machine (including Win 11 ARM)
- Push to GitHub
- Azure builds + deploys
- You test ONLY in Azure

Architecture:
- Azure Container Apps: product services
  - web-api: upload + job creation + status API
  - orchestrator: queue worker that runs pipeline steps
  - export-worker: creates export variants (stub for now)
  - billing-service: Mollie webhooks + credit ledger (stub billing logic for now)
- Azure ML Managed Online Endpoint:
  - sd-placement (stub container now; replace with real SD later)

We start with a "stub pipeline" that proves:
- Storage upload works
- Queue works
- Orchestrator consumes messages
- Orchestrator calls AML endpoint
- Job status updates in DB

Then you replace the AML stub with Stable Diffusion and add real background removal/upscale.

---

## Prerequisites

### Azure
- Azure subscription
- Create a Resource Group is handled by Bicep deployment (workflow does it).
- Create a Federated Credential / OIDC for GitHub Actions (recommended), or a service principal secret.

### Local tooling (for sanity checks and occasional manual commands)
Install Azure CLI + extensions:
- az extension add -n containerapp
- az extension add -n ml

Docs:
- Azure Container Apps GitHub Actions guidance: https://learn.microsoft.com/en-us/azure/container-apps/github-actions
- Azure ML online endpoint deploy: https://learn.microsoft.com/en-us/azure/machine-learning/how-to-deploy-online-endpoints?view=azureml-api-2

---

## Step-by-step sanity checks (do these in order)

### Step 0 — Repo + GitHub secrets
In GitHub repo settings > Secrets and variables > Actions > New repository secret:

Required:
- AZURE_CLIENT_ID
- AZURE_TENANT_ID
- AZURE_SUBSCRIPTION_ID

These are for OIDC login (no secret required). You must also create a Federated Credential for the app registration.

Optional (later):
- MOLLIE_API_KEY
- MOLLIE_WEBHOOK_SECRET

---

### Step 1 — Deploy Infra (dev)
Run GitHub Action: `.github/workflows/infra-deploy-dev.yml`

Sanity check in workflow logs:
- Bicep deploy succeeded
- Outputs printed (ACR name, ACA env, storage, service bus, postgres, key vault, app insights, AML workspace)

---

### Step 2 — Build + Deploy services (dev)
Run GitHub Action: `.github/workflows/build-deploy-dev.yml`

Sanity check in workflow logs:
- Built images pushed to ACR
- Container Apps updated
- AML endpoint created/updated
- AML deployment created/updated

---

### Step 3 — Health checks (dev)
After deploy, get the web-api URL from ACA:

In Azure Portal -> Container Apps -> opal-web-api-dev -> Ingress -> Application URL

Hit:
- GET /healthz
Expect:
- status: ok
- db: ok
- storage: ok
- service_bus: ok

---

### Step 4 — Create job + upload item (dev)
1) Create a job:
POST /v1/jobs
Body:
{
  "tenant_id": "demo-tenant",
  "brand_profile_id": "default",
  "items": [
    {"filename": "sample.jpg"}
  ]
}

2) Request an upload URL:
POST /v1/uploads/sas
Body:
{
  "tenant_id": "demo-tenant",
  "job_id": "<job_id>",
  "item_id": "<item_id>",
  "filename": "sample.jpg",
  "content_type": "image/jpeg"
}

3) PUT the image to the SAS URL using any HTTP client (Postman/curl).
4) Finalize upload:
POST /v1/uploads/complete
Body:
{
  "tenant_id": "demo-tenant",
  "job_id": "<job_id>",
  "item_id": "<item_id>",
  "filename": "sample.jpg"
}

Sanity check:
- Item status becomes "queued"
- Orchestrator logs show it consumed the message
- Orchestrator calls AML endpoint
- Item ends in "completed" with an output URL

---

## Notes on "robust from start"
This scaffold includes:
- Correlation IDs on every job/item
- Idempotency-safe patterns (retries, durable-ish worker behavior)
- Credit ledger tables (billing service will use these next)
- Private blobs only; downloads via SAS generated per request

---

## Next upgrades (after pipeline works)
1) Replace AML stub with Stable Diffusion container + real score.py
2) Add background removal worker (model endpoint or container worker)
3) Add real export-worker (1:1, 4:3, 9:16 variants)
4) Implement Mollie subscriptions + webhook signature verification + monthly credit grants
