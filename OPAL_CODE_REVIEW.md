# OPAL Platform - Code Review & Phase 2 Preparation

**Review Date:** February 7, 2026  
**Version:** v0.2 (Post-Phase 1 Infrastructure Deployment)  
**Reviewer:** Claude (Assistant)

---

## Executive Summary

✅ **Infrastructure Status:** Fully deployed and operational  
⚠️ **Code Issues:** 3 critical bugs found that need immediate attention  
🎯 **Phase 2 Readiness:** Ready to proceed after addressing critical issues  

The OPAL platform has a solid architectural foundation with proper separation of concerns, managed identity integration, and queue-based workflow orchestration. However, there are some redundancies and missing implementations that should be addressed before Phase 2.

---

## Infrastructure Overview

### Deployed Azure Resources

| Resource | Purpose | Status |
|----------|---------|--------|
| **Container Registry (ACR)** | Docker images | ✅ Operational |
| **Container Apps Environment** | Hosting services | ✅ Operational |
| **Service Bus** | Message queuing (jobs, exports) | ✅ Operational |
| **PostgreSQL Flexible Server** | Database | ✅ Operational |
| **Storage Account** | Blob storage (raw, outputs, exports) | ✅ Operational |
| **Key Vault** | Secrets management | ✅ Deployed (not yet used) |
| **Application Insights** | Monitoring | ✅ Deployed |
| **Azure ML Workspace** | ML endpoints | ✅ Deployed (stub only) |

### Container Apps Deployed

| Service | Role | Ingress | Queue | Status |
|---------|------|---------|-------|--------|
| **web-api** | REST API for uploads/jobs | External :8080 | - | ✅ Running |
| **billing-service** | Mollie webhooks (stub) | External :8080 | - | ✅ Running |
| **orchestrator** | Main pipeline worker | Internal :8080 | jobs → | ✅ Running |
| **export-worker** | Export variants (stub) | None | exports → | ✅ Running |
| **jobs-worker** | Message forwarder | None | jobs → exports | ✅ Running |

### RBAC Configuration

All Container Apps have Managed Identity with:
- ✅ AcrPull (for image pulls)
- ✅ Storage Blob Data Contributor (for blob access)
- ✅ Azure Service Bus Data Receiver
- ✅ Azure Service Bus Data Sender

---

## Critical Issues Found

### 🔴 ISSUE #1: Missing `send_job_message` Function

**Location:** `src/shared/shared/servicebus.py`  
**Severity:** CRITICAL - **Code will not run**  
**Impact:** Web API cannot queue jobs after upload

**Problem:**
```python
# In routes_uploads.py line 62:
from shared.servicebus import send_job_message

# But this function doesn't exist in servicebus.py!
```

**Current servicebus.py only has:**
- `get_fully_qualified_namespace()`
- `get_client()`

**Fix Required:**
```python
# Add to src/shared/shared/servicebus.py

import json
from azure.servicebus import ServiceBusMessage
from shared.config import settings

def send_job_message(payload: dict) -> None:
    """Send a message to the jobs queue."""
    with get_client() as client:
        sender = client.get_queue_sender(queue_name=settings.SERVICEBUS_JOBS_QUEUE)
        with sender:
            message = ServiceBusMessage(json.dumps(payload))
            sender.send_messages(message)
```

---

### 🟡 ISSUE #2: Redundant Worker Architecture

**Locations:** `orchestrator/worker.py` and `jobs_worker/worker.py`  
**Severity:** MEDIUM - Architecture confusion  
**Impact:** Unnecessary complexity and resource usage

**Problem:**

Both `orchestrator` and `jobs_worker` consume from the **same queue** (`jobs`):

1. **orchestrator** (lines 98-104):
   - Reads from `jobs` queue
   - Calls AML endpoint
   - Writes output to blob storage
   - Marks item as completed

2. **jobs_worker** (lines 44-68):
   - Reads from `jobs` queue
   - Forwards message to `exports` queue
   - Does nothing else

**Issues:**
- Both workers compete for the same messages
- Race condition: orchestrator might process a message, then jobs_worker tries to forward it (or vice versa)
- Unclear separation of responsibility
- jobs_worker seems unnecessary in current architecture

**Recommended Fixes:**

**Option A: Remove jobs_worker entirely (RECOMMENDED)**
- Delete `jobs_worker` service
- Have `orchestrator` send to `exports` queue after completing processing
- Simpler, clearer flow: web-api → jobs queue → orchestrator → exports queue → export_worker

**Option B: Separate queues**
- web-api sends to `preprocessing` queue
- jobs_worker reads `preprocessing`, does work, sends to `jobs` queue
- orchestrator reads `jobs` queue
- More complex but allows for future preprocessing step

**Recommended: Option A** - Remove jobs_worker for now; add it back later if preprocessing is needed.

---

### 🟡 ISSUE #3: AML Endpoint Missing in Current Deployment

**Location:** Workflow deployment  
**Severity:** MEDIUM - Pipeline won't work end-to-end  
**Impact:** Orchestrator will fail when calling AML endpoint

**Problem:**
The GitHub workflow `build-deploy-dev.yml` builds the `aml-sd-stub` Docker image but **never deploys it** to Azure ML.

**Lines 178-180** build the image:
```yaml
if [ "${{ steps.decide.outputs.aml_sd_stub }}" = "true" ]; then
  build_push "${ACR_LOGIN}/opal/aml-sd-stub:${IMAGE_TAG}" "src/aml_sd_stub/Dockerfile"
fi
```

But there's **no corresponding deployment step** for Azure ML Online Endpoint/Deployment.

**Fix Required:**
Add deployment steps after line 371:
```yaml
- name: Deploy AML Endpoint (if changed)
  if: steps.decide.outputs.aml_sd_stub == 'true'
  run: |
    # Deploy to Azure ML using ml/ deployment files
    # Update AML_ENDPOINT_URL and AML_ENDPOINT_KEY secrets
```

Or manually deploy via:
```bash
az ml online-endpoint create -f ml/endpoint.yml
az ml online-deployment create -f ml/deployment.yml --endpoint <endpoint-name>
```

---

## Architecture Analysis

### Current Pipeline Flow

```
User Upload
    ↓
1. POST /v1/jobs → creates job & items in DB
    ↓
2. POST /v1/uploads/sas → get SAS URL for upload
    ↓
3. PUT to SAS URL → upload image to blob storage (raw container)
    ↓
4. POST /v1/uploads/complete → mark as "uploaded" + send to queue
    ↓
5. Message sent to "jobs" queue ← ❌ ISSUE #1: send_job_message missing
    ↓
6a. orchestrator reads "jobs" queue → calls AML stub → writes to outputs
    └── OR ←── ❌ ISSUE #2: Race condition!
6b. jobs_worker reads "jobs" queue → forwards to "exports" queue
    ↓
7. export_worker reads "exports" queue (stub - does nothing yet)
```

### Recommended Pipeline Flow (After Fixes)

```
User Upload
    ↓
1. POST /v1/jobs → creates job & items
    ↓
2. POST /v1/uploads/sas → get upload URL
    ↓
3. PUT to SAS → upload to blob (raw)
    ↓
4. POST /v1/uploads/complete → send to "jobs" queue
    ↓
5. orchestrator reads "jobs" queue
    ├─> calls background removal (Phase 2)
    ├─> calls Stable Diffusion placement (Phase 2)
    ├─> calls upscaling (Phase 2)
    ├─> writes final output to outputs container
    └─> sends message to "exports" queue
    ↓
6. export_worker creates export variants (1:1, 4:3, 9:16)
```

---

## Code Quality Review

### ✅ **Strengths**

1. **Proper separation of concerns:**
   - Web API handles HTTP
   - Workers handle async processing
   - Shared library for common code

2. **Managed Identity throughout:**
   - No hardcoded credentials
   - RBAC-based access
   - DefaultAzureCredential pattern

3. **Idempotency patterns:**
   - Orchestrator checks if already processing/completed (line 45-47)
   - Prevents duplicate work

4. **Correlation IDs:**
   - Proper tracking across services
   - Good for debugging

5. **SAS URL pattern:**
   - Secure blob access
   - No keys in application code

6. **Database models well-designed:**
   - Clean SQLAlchemy models
   - Status enums
   - Proper relationships

### ⚠️ **Areas for Improvement**

1. **Missing error handling in some places:**
   - No retry logic on blob uploads (orchestrator line 84)
   - Could use tenacity decorator

2. **No logging in shared modules:**
   - storage.py, servicebus.py have no logging
   - Makes debugging harder

3. **Hardcoded timeout values:**
   - Line 28 in orchestrator: `timeout=180`
   - Line 84: `timeout=60`
   - Should be in config

4. **Database connections not pooled:**
   - Each `SessionLocal()` creates new connection
   - Consider using scoped sessions

5. **No health checks for workers:**
   - Only web-api and billing-service have /healthz
   - Workers should expose metrics

---

## Database Schema Review

### Current Tables

```sql
jobs (
    id VARCHAR(64) PK,
    tenant_id VARCHAR(128) INDEXED,
    brand_profile_id VARCHAR(128),
    status JobStatus,  -- created|processing|completed|failed
    correlation_id VARCHAR(64) INDEXED,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
)

job_items (
    id VARCHAR(64) PK,
    job_id VARCHAR(64) FK → jobs.id,
    tenant_id VARCHAR(128) INDEXED,
    filename VARCHAR(512),
    status ItemStatus,  -- created|uploaded|queued|processing|completed|failed
    raw_blob_path VARCHAR(1024),
    output_blob_path VARCHAR(1024),
    error_message TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
)

credit_ledger (
    id INTEGER PK AUTOINCREMENT,
    tenant_id VARCHAR(128) INDEXED,
    delta INTEGER,  -- +grant -usage
    reason VARCHAR(256),
    ref VARCHAR(256),  -- payment_id, job_id, etc.
    created_at TIMESTAMP
)
```

### ✅ Schema Strengths

- Clean design with proper indexes
- Status tracking at both job and item level
- Billing foundation ready (credit_ledger)

### 📝 Suggested Additions for Phase 2

```sql
-- Add to job_items table for AI pipeline tracking
ALTER TABLE job_items ADD COLUMN bg_removed_blob_path VARCHAR(1024);
ALTER TABLE job_items ADD COLUMN placed_blob_path VARCHAR(1024);
ALTER TABLE job_items ADD COLUMN upscaled_blob_path VARCHAR(1024);
ALTER TABLE job_items ADD COLUMN processing_started_at TIMESTAMP;
ALTER TABLE job_items ADD COLUMN processing_completed_at TIMESTAMP;
ALTER TABLE job_items ADD COLUMN ai_metadata JSONB;  -- store prompts, settings, etc.

-- Add brand profiles table (currently just a string field)
CREATE TABLE brand_profiles (
    id VARCHAR(64) PRIMARY KEY,
    tenant_id VARCHAR(128) NOT NULL,
    name VARCHAR(256) NOT NULL,
    sd_prompts JSONB,  -- Stable Diffusion settings
    placement_style VARCHAR(128),  -- lifestyle, studio, etc.
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_brand_profiles_tenant ON brand_profiles(tenant_id);
```

---

## Phase 2 Readiness Assessment

### ✅ **Ready**

- Infrastructure fully deployed
- RBAC configured correctly
- Storage containers ready
- Service Bus queues operational
- Database schema solid

### ❌ **Blockers Before Phase 2**

1. **Must fix:** Missing `send_job_message` function
2. **Should fix:** Clarify worker architecture (remove jobs_worker or separate queues)
3. **Should fix:** Deploy AML stub endpoint so orchestrator can actually run

### 🎯 **Phase 2 Additions Needed**

1. **Azure AI Vision** integration for background removal
2. **Stable Diffusion** on Azure ML for product placement
3. **Upscaling** service (Real-ESRGAN or similar)
4. Update orchestrator to call all three services in sequence
5. Add intermediate blob paths to track each processing stage

---

## Recommended Immediate Actions

### Priority 1: Fix Critical Bugs

```bash
# 1. Add send_job_message function
# Edit: src/shared/shared/servicebus.py
# (See ISSUE #1 above for code)

# 2. Remove jobs_worker (recommended)
git rm -rf src/jobs_worker/
# Update .github/workflows/build-deploy-dev.yml to skip jobs_worker

# OR keep it and fix queue names
# Edit: src/jobs_worker/jobs_worker/worker.py
# Change to consume from a different queue

# 3. Deploy AML stub
az ml online-endpoint create -f ml/endpoint.yml -g opal-dev-rg
az ml online-deployment create -f ml/deployment.yml -g opal-dev-rg --endpoint <name>
# Update GitHub secrets: AML_ENDPOINT_URL and AML_ENDPOINT_KEY
```

### Priority 2: Code Improvements

```python
# Add retry logic to blob uploads
# In orchestrator/worker.py

@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=5))
def upload_blob(sas_url: str, data: bytes):
    with httpx.Client(timeout=60) as client:
        r = client.put(sas_url, content=data, headers={"x-ms-blob-type": "BlockBlob"})
        r.raise_for_status()

# Add logging to shared modules
import logging
LOG = logging.getLogger(__name__)

# Move timeouts to config
# In shared/config.py
AML_TIMEOUT: int = 180
BLOB_UPLOAD_TIMEOUT: int = 60
```

### Priority 3: Testing

```bash
# Test the full pipeline
curl -X POST https://<web-api-url>/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{"tenant_id":"demo","brand_profile_id":"default","items":[{"filename":"test.jpg"}]}'

# Get upload SAS
curl -X POST https://<web-api-url>/v1/uploads/sas \
  -H "Content-Type: application/json" \
  -d '{"tenant_id":"demo","job_id":"<job_id>","item_id":"<item_id>","filename":"test.jpg","content_type":"image/jpeg"}'

# Upload image to SAS URL
curl -X PUT "<sas_url>" \
  -H "x-ms-blob-type: BlockBlob" \
  --upload-file test.jpg

# Complete upload
curl -X POST https://<web-api-url>/v1/uploads/complete \
  -H "Content-Type: application/json" \
  -d '{"tenant_id":"demo","job_id":"<job_id>","item_id":"<item_id>","filename":"test.jpg"}'

# Check orchestrator logs
az containerapp logs show -g opal-dev-rg -n opal-orchestrator-dev --follow
```

---

## Phase 2 Implementation Plan

### Week 1: Background Removal (Azure AI Vision)

**Tasks:**
1. Create Azure AI Vision resource
2. Add vision SDK to orchestrator requirements
3. Implement background removal in orchestrator
4. Save to bg_removed_blob_path
5. Test with real images

**Files to modify:**
- `src/orchestrator/requirements.txt` (add azure-ai-vision)
- `src/orchestrator/orchestrator/worker.py` (add bg removal step)
- `src/shared/shared/models.py` (add bg_removed_blob_path)
- `src/shared/shared/config.py` (add VISION_ENDPOINT)

### Week 2: Stable Diffusion Integration

**Tasks:**
1. Replace AML stub with real Stable Diffusion model
2. Configure placement prompts by brand profile
3. Implement composite image creation
4. Save to placed_blob_path
5. Test placement quality

**Files to modify:**
- `src/aml_sd_stub/score.py` (replace with real SD code)
- `ml/deployment.yml` (update instance type for GPU)
- `src/shared/shared/models.py` (add placed_blob_path)

### Week 3: Upscaling & Export Variants

**Tasks:**
1. Add upscaling service (Real-ESRGAN)
2. Implement export_worker (1:1, 4:3, 9:16 crops)
3. Generate final outputs
4. End-to-end testing
5. Performance optimization

**Files to create:**
- `src/upscaler/` (new service)
- Update `src/export_worker/export_worker/worker.py` (real implementation)

---

## Conclusion

**Overall Assessment:** The OPAL platform has a **solid foundation** with proper Azure infrastructure, security (Managed Identity), and architectural patterns (queue-based workers, SAS URLs). The code is generally well-structured with good separation of concerns.

However, there are **3 critical issues** that must be fixed before Phase 2:
1. Missing `send_job_message` function (breaks web API)
2. Redundant worker architecture (jobs_worker vs orchestrator)
3. AML endpoint not deployed (orchestrator can't call it)

Once these are addressed, the platform will be ready for Phase 2 AI integration.

**Recommendation:** Fix these issues in v0.2.1 before starting Phase 2 development.

---

## Files Reviewed

```
📁 opal-v0_2.zip
├── 📁 infra/
│   ├── main.bicep (212 lines)
│   └── main.parameters.json
├── 📁 ml/
│   ├── endpoint.yml
│   └── deployment.yml
├── 📁 src/
│   ├── 📁 shared/shared/
│   │   ├── config.py
│   │   ├── db.py
│   │   ├── models.py ⭐
│   │   ├── servicebus.py ❌ Missing function
│   │   ├── storage.py
│   │   └── util.py
│   ├── 📁 web_api/
│   │   ├── routes_jobs.py
│   │   ├── routes_uploads.py ⭐
│   │   ├── routes_health.py
│   │   └── main.py
│   ├── 📁 orchestrator/ ⭐
│   │   └── worker.py
│   ├── 📁 jobs_worker/ ⚠️ Redundant
│   │   └── worker.py
│   ├── 📁 export_worker/
│   │   └── worker.py (stub)
│   ├── 📁 billing_service/
│   │   └── (stub)
│   └── 📁 aml_sd_stub/
│       └── score.py (stub)
└── 📁 .github/workflows/
    └── build-deploy-dev.yml ⭐

Total: ~2,500 lines of code reviewed
```

---

**Ready for Phase 2?** Almost! Fix the 3 critical issues first, then proceed. 🚀
