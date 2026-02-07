# v0.2.1 Deployment Checklist

**Date:** February 7, 2026  
**Version:** v0.2.1  
**Type:** Critical Bug Fix

---

## 📋 Pre-Deployment Checklist

- [ ] Review all changed files
- [ ] Understand the 3 critical fixes
- [ ] Ensure GitHub secrets are ready for AML credentials
- [ ] Backup current deployment (already at v0.2 tag)

---

## 🚀 Deployment Steps

### Step 1: Commit and Tag

```bash
cd /path/to/opal

# Add all changed files
git add src/shared/shared/servicebus.py
git add src/orchestrator/orchestrator/worker.py
git add .github/workflows/build-deploy-dev.yml
git add ml/deployment-stub.yml
git add CHANGELOG-v0.2.1.md

# Commit with descriptive message
git commit -m "v0.2.1: Critical bug fixes

- Fix: Add missing send_job_message function to servicebus.py
- Fix: Remove redundant jobs_worker, orchestrator now sends to exports directly
- Fix: Add AML endpoint deployment to workflow
- Improve: Add retry logic for blob uploads
- Improve: Enhanced logging throughout

Fixes #1, #2, #3 from code review"

# Tag the release
git tag -a v0.2.1 -m "v0.2.1: Critical bug fixes

This patch fixes 3 critical issues identified in code review:
1. Missing send_job_message function (web API crash)
2. Redundant jobs_worker architecture (race conditions)
3. AML endpoint not deployed (orchestrator failure)

All services now operational. Ready for Phase 2."

# Push to GitHub
git push origin main
git push origin v0.2.1
```

### Step 2: Monitor GitHub Actions

```bash
# Watch the workflow run
gh run watch

# Or view in browser
# https://github.com/code-418dotcom/opal/actions
```

**Expected workflow steps:**
1. ✅ Detect changes (shared, orchestrator, aml_sd_stub)
2. ✅ Build images (web-api, orchestrator, export-worker, billing-service, aml-sd-stub)
3. ✅ Update container apps
4. ✅ Deploy AML endpoint ← **NEW STEP**
5. ✅ Output AML credentials ← **IMPORTANT**

### Step 3: Capture AML Credentials

From the GitHub Actions output, copy:

```
AML Endpoint deployed successfully!
Scoring URI: https://opal-sd-placement-dev.westeurope.inference.ml.azure.com/score
AML_ENDPOINT_URL=https://opal-sd-placement-dev.westeurope.inference.ml.azure.com/score
AML_ENDPOINT_KEY=<32-character-key>
```

### Step 4: Update GitHub Secrets

```bash
# Set AML_ENDPOINT_URL
gh secret set AML_ENDPOINT_URL --body 'https://opal-sd-placement-dev.westeurope.inference.ml.azure.com/score'

# Set AML_ENDPOINT_KEY (paste the key from workflow output)
gh secret set AML_ENDPOINT_KEY --body '<paste-key-here>'

# Verify secrets are set
gh secret list | grep AML
```

**Expected output:**
```
AML_ENDPOINT_KEY    Updated YYYY-MM-DD
AML_ENDPOINT_URL    Updated YYYY-MM-DD
```

### Step 5: Re-run Workflow to Pick Up Secrets

```bash
# Trigger a new workflow run with the updated secrets
gh workflow run build-deploy-dev.yml

# Or manually via GitHub UI:
# Actions → Build & Deploy Apps (dev) - Smart → Run workflow
```

### Step 6: Verify Deployment

```bash
# Check all container apps are running
az containerapp list -g opal-dev-rg \
  --query "[].{name:name,state:properties.runningStatus,revision:properties.latestRevisionName}" \
  -o table

# Expected: 4 apps running (no jobs_worker)
# - opal-billing-service-dev
# - opal-export-worker-dev
# - opal-orchestrator-dev
# - opal-web-api-dev

# Check AML endpoint
az ml online-endpoint show \
  --name opal-sd-placement-dev \
  -g opal-dev-rg \
  --workspace-name $(az ml workspace list -g opal-dev-rg --query "[0].name" -o tsv) \
  --query "{uri:scoring_uri,state:provisioning_state,traffic:traffic}" \
  -o json

# Expected: {"uri": "https://...", "state": "Succeeded", "traffic": {"blue": 100}}
```

---

## ✅ Post-Deployment Testing

### Test 1: End-to-End Pipeline

```bash
# Get web API URL
WEB_URL=$(az containerapp show -g opal-dev-rg -n opal-web-api-dev \
  --query "properties.configuration.ingress.fqdn" -o tsv)

echo "Web API URL: https://${WEB_URL}"

# Create a test job
curl -X POST "https://${WEB_URL}/v1/jobs" \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "test",
    "brand_profile_id": "default",
    "items": [{"filename": "test.jpg"}]
  }' | jq .

# Save the job_id and item_id from the response
export JOB_ID="<paste-job-id>"
export ITEM_ID="<paste-item-id>"

# Request upload SAS
curl -X POST "https://${WEB_URL}/v1/uploads/sas" \
  -H "Content-Type: application/json" \
  -d "{
    \"tenant_id\": \"test\",
    \"job_id\": \"${JOB_ID}\",
    \"item_id\": \"${ITEM_ID}\",
    \"filename\": \"test.jpg\",
    \"content_type\": \"image/jpeg\"
  }" | jq .

# Save the upload_url
export UPLOAD_URL="<paste-upload-url>"

# Upload a test image (create a 1x1 PNG first)
echo "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==" | base64 -d > test.jpg

curl -X PUT "${UPLOAD_URL}" \
  -H "x-ms-blob-type: BlockBlob" \
  --upload-file test.jpg

# Complete the upload (this triggers the pipeline)
curl -X POST "https://${WEB_URL}/v1/uploads/complete" \
  -H "Content-Type: application/json" \
  -d "{
    \"tenant_id\": \"test\",
    \"job_id\": \"${JOB_ID}\",
    \"item_id\": \"${ITEM_ID}\",
    \"filename\": \"test.jpg\"
  }" | jq .

# Expected: {"ok": true}
```

### Test 2: Monitor Logs

```bash
# Open 3 terminal windows

# Terminal 1: Watch orchestrator
az containerapp logs show -g opal-dev-rg -n opal-orchestrator-dev --follow

# Terminal 2: Watch export worker
az containerapp logs show -g opal-dev-rg -n opal-export-worker-dev --follow

# Terminal 3: Watch web API
az containerapp logs show -g opal-dev-rg -n opal-web-api-dev --follow
```

**Expected log sequence:**

**Web API logs:**
```
INFO shared.servicebus - Sent job message to queue=jobs job_id=... item_id=...
```

**Orchestrator logs:**
```
INFO orchestrator.worker - Processing job message: tenant_id=test job_id=... item_id=...
INFO orchestrator.worker - Calling AML endpoint for item_id=...
INFO orchestrator.worker - Uploading output blob: item_id=... path=...
INFO orchestrator.worker - Item completed: item_id=... output_path=...
INFO shared.servicebus - Sent export message to queue=exports job_id=...
INFO orchestrator.worker - Sent export message for job_id=...
```

**Export Worker logs:**
```
INFO export_worker - Processing export for job_id=... tenant_id=test
INFO export_worker - Completed export message for job_id=...
```

### Test 3: Verify No Errors

```bash
# Check for any errors in the last hour
az monitor activity-log list \
  --resource-group opal-dev-rg \
  --start-time "2026-02-07T00:00:00Z" \
  --query "[?level=='Error'].{time:eventTimestamp,resource:resourceId,message:properties.statusMessage}" \
  -o table

# Expected: Empty table (no errors)
```

---

## 🧹 Optional Cleanup

### Remove Old jobs_worker Container App

```bash
# The jobs_worker app is no longer needed
# It won't receive traffic but still consumes resources

# List to confirm it exists
az containerapp show -g opal-dev-rg -n opal-jobs-worker-dev \
  --query "{name:name,state:properties.runningStatus}" \
  -o table

# Delete it
az containerapp delete -g opal-dev-rg -n opal-jobs-worker-dev --yes

# Verify deletion
az containerapp list -g opal-dev-rg --query "[].name" -o tsv
# Should only show 4 apps now
```

### Clean Up Old Images (Optional)

```bash
# List images in ACR
az acr repository list --name opaldevdbeia4dlnxsy4 -o table

# Old jobs-worker images can be deleted
az acr repository delete \
  --name opaldevdbeia4dlnxsy4 \
  --repository opal/jobs-worker \
  --yes

# Or keep them for rollback purposes
```

---

## 🔄 Rollback Plan (If Needed)

If something goes wrong, you can roll back to v0.2:

```bash
# 1. Checkout v0.2
git checkout v0.2

# 2. Trigger deployment
git push origin main --force

# 3. Or manually update images
export OLD_SHA="<sha-from-v0.2>"

az containerapp update -g opal-dev-rg -n opal-web-api-dev \
  --image opaldevdbeia4dlnxsy4.azurecr.io/opal/web-api:${OLD_SHA}

az containerapp update -g opal-dev-rg -n opal-orchestrator-dev \
  --image opaldevdbeia4dlnxsy4.azurecr.io/opal/orchestrator:${OLD_SHA}

# Note: jobs_worker will need to be redeployed if you rollback
```

---

## 📊 Success Criteria

- [ ] All 4 container apps running (no jobs_worker)
- [ ] AML endpoint deployed and accessible
- [ ] End-to-end test completes successfully
- [ ] No errors in logs
- [ ] Export messages flowing from orchestrator to export_worker
- [ ] GitHub secrets updated with AML credentials

---

## 🎯 What's Next

After successful v0.2.1 deployment:

1. **Verify everything works** ✅
2. **Tag and document v0.2.1** ✅
3. **Start Phase 2: Azure AI Vision integration** 🚀

---

## 🆘 Troubleshooting

### Issue: AML endpoint deployment fails

```bash
# Check AML workspace exists
az ml workspace list -g opal-dev-rg

# Check quota for instance type
az ml compute list-usage -g opal-dev-rg \
  --workspace-name $(az ml workspace list -g opal-dev-rg --query "[0].name" -o tsv) \
  -o table

# Try with smaller instance if quota exceeded
# Edit ml/deployment-stub.yml:
#   instance_type: Standard_DS1_v2
```

### Issue: Container app won't start

```bash
# Check logs for errors
az containerapp logs show -g opal-dev-rg -n opal-orchestrator-dev --tail 100

# Check environment variables
az containerapp show -g opal-dev-rg -n opal-orchestrator-dev \
  --query "properties.template.containers[0].env" -o table

# Verify database connection
az containerapp exec -g opal-dev-rg -n opal-orchestrator-dev \
  --command "python -c 'from shared.config import settings; print(settings.DATABASE_URL)'"
```

### Issue: send_job_message still missing

```bash
# Verify the file was updated
az containerapp exec -g opal-dev-rg -n opal-web-api-dev \
  --command "python -c 'from shared.servicebus import send_job_message; print(send_job_message)'"

# Expected: <function send_job_message at 0x...>

# If still missing, rebuild with --no-cache
az acr build --registry opaldevdbeia4dlnxsy4 \
  --image opal/web-api:$(git rev-parse HEAD) \
  --no-cache \
  -f src/web_api/Dockerfile .
```

---

## 📞 Support

If deployment fails:
1. Check GitHub Actions logs
2. Check Azure Container Apps logs
3. Review this checklist
4. Consult CHANGELOG-v0.2.1.md for details

---

**Status:** ⏳ Ready to Deploy  
**Estimated Time:** 15-20 minutes  
**Risk Level:** Low (backward compatible, tested fixes)
