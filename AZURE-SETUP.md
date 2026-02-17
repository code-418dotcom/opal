# OPAL Azure Deployment - Complete Setup Guide

Your OPAL platform is ready to deploy to Azure with full AI processing capabilities!

## What You Have

✅ **Azure Resources** (from your screenshot):
- Resource Group: `opaldevdbeia4dlnxsy4sa`
- Container Registry: `opaldevdbeia4dlnxsy4`
- Storage Account: `opaldevdbeia4dlnxsy4sa`
- Service Bus: `opal-dev-dbeia4dlnxsy4-bus`
- PostgreSQL: `opal-dev-dbeia4dlnxsy4-pg-ne`

✅ **Credentials**:
- FAL.AI API Key: `09c4a4ef-8788-497c-a417-91aa605dfb98:...`
- Database URL: `postgresql+psycopg://opaladmin:...@opal-dev-dbeia4dlnxsy4-pg-ne.postgres.database.azure.com/opal`

✅ **AI Pipeline** (fully coded):
- Background removal (rembg - local, free)
- Scene generation (FAL.AI FLUX.1 - $0.03/image)
- Product compositing (PIL - local, free)
- 2x upscaling (Real-ESRGAN - local, free)

---

## 3-Step Deployment

### Step 1: Set Up Database

Run this on your local machine (requires PostgreSQL client):

```bash
# Make script executable
chmod +x setup-azure-db.sh

# Run migration
./setup-azure-db.sh
```

It will:
- Connect to your Azure PostgreSQL database
- Create tables: `jobs`, `job_items`, `job_queue`, `brand_profiles`
- Set up indexes and triggers

**Alternative: Manual Migration**

```bash
# Using environment variable for password
export PGPASSWORD="YOUR_POSTGRES_PASSWORD_HERE"

# Run migration
psql -h opal-dev-dbeia4dlnxsy4-pg-ne.postgres.database.azure.com \
     -U opaladmin \
     -d opal \
     -p 5432 \
     -f migrations/001_azure_initial_schema.sql
```

---

### Step 2: Configure Azure Resources

```bash
# Login to Azure
az login

# Create blob storage containers for images
az storage container create \
  --name raw \
  --account-name opaldevdbeia4dlnxsy4sa

az storage container create \
  --name outputs \
  --account-name opaldevdbeia4dlnxsy4sa

# Create Service Bus queue for job processing
az servicebus queue create \
  --name jobs \
  --namespace-name opal-dev-dbeia4dlnxsy4-bus \
  --resource-group opaldevdbeia4dlnxsy4sa

# Get connection strings (save these!)
echo "=== Storage Connection String ==="
az storage account show-connection-string \
  --name opaldevdbeia4dlnxsy4sa \
  --resource-group opaldevdbeia4dlnxsy4sa \
  --output tsv

echo ""
echo "=== Service Bus Connection String ==="
az servicebus namespace authorization-rule keys list \
  --resource-group opaldevdbeia4dlnxsy4sa \
  --namespace-name opal-dev-dbeia4dlnxsy4-bus \
  --name RootManageSharedAccessKey \
  --query primaryConnectionString \
  --output tsv
```

---

### Step 3: Deploy Orchestrator

Create `.env.deploy` file with your connection strings from Step 2:

```env
DATABASE_URL=postgresql+psycopg://opaladmin:YOUR_PASSWORD@opal-dev-dbeia4dlnxsy4-pg-ne.postgres.database.azure.com:5432/opal?sslmode=require
AZURE_STORAGE_CONNECTION_STRING=<from-step-2>
AZURE_SERVICEBUS_CONNECTION_STRING=<from-step-2>
FAL_API_KEY=YOUR_FAL_API_KEY_HERE
```

Deploy:

```bash
# Load environment
export $(cat .env.deploy | xargs)

# Login to container registry
az acr login --name opaldevdbeia4dlnxsy4

# Build and push orchestrator
docker build -t opaldevdbeia4dlnxsy4.azurecr.io/orchestrator:latest \
  -f src/orchestrator/Dockerfile .
docker push opaldevdbeia4dlnxsy4.azurecr.io/orchestrator:latest

# Create Container Apps environment
az containerapp env create \
  --name opal-dev-cae \
  --resource-group opaldevdbeia4dlnxsy4sa \
  --location westeurope

# Deploy orchestrator
az containerapp create \
  --name opal-orchestrator \
  --resource-group opaldevdbeia4dlnxsy4sa \
  --environment opal-dev-cae \
  --image opaldevdbeia4dlnxsy4.azurecr.io/orchestrator:latest \
  --registry-server opaldevdbeia4dlnxsy4.azurecr.io \
  --cpu 2 \
  --memory 4Gi \
  --min-replicas 1 \
  --max-replicas 3 \
  --secrets \
    database-url="$DATABASE_URL" \
    storage-connection="$AZURE_STORAGE_CONNECTION_STRING" \
    servicebus-connection="$AZURE_SERVICEBUS_CONNECTION_STRING" \
    fal-api-key="$FAL_API_KEY" \
  --env-vars \
    DATABASE_URL=secretref:database-url \
    AZURE_STORAGE_CONNECTION_STRING=secretref:storage-connection \
    AZURE_SERVICEBUS_CONNECTION_STRING=secretref:servicebus-connection \
    SERVICEBUS_JOBS_QUEUE=jobs \
    FAL_API_KEY=secretref:fal-api-key \
    BACKGROUND_REMOVAL_PROVIDER=rembg \
    IMAGE_GEN_PROVIDER=fal \
    UPSCALE_PROVIDER=realesrgan \
    UPSCALE_ENABLED=true \
    LOG_LEVEL=INFO \
    STORAGE_BACKEND=azure \
    QUEUE_BACKEND=azure
```

---

## Verify Deployment

```bash
# Check orchestrator status
az containerapp show \
  --name opal-orchestrator \
  --resource-group opaldevdbeia4dlnxsy4sa \
  --query 'properties.runningStatus'

# View logs
az containerapp logs show \
  --name opal-orchestrator \
  --resource-group opaldevdbeia4dlnxsy4sa \
  --follow
```

Expected output:
```
INFO: Worker started, listening to Azure Service Bus queue: jobs
INFO: Waiting for messages...
```

---

## Deploy Web API (Optional)

If you want to move your API from Supabase to Azure:

```bash
# Build and push
docker build -t opaldevdbeia4dlnxsy4.azurecr.io/web-api:latest \
  -f src/web_api/Dockerfile .
docker push opaldevdbeia4dlnxsy4.azurecr.io/web-api:latest

# Deploy
az containerapp create \
  --name opal-web-api \
  --resource-group opaldevdbeia4dlnxsy4sa \
  --environment opal-dev-cae \
  --image opaldevdbeia4dlnxsy4.azurecr.io/web-api:latest \
  --target-port 8080 \
  --ingress external \
  --cpu 0.5 \
  --memory 1Gi \
  --secrets \
    database-url="$DATABASE_URL" \
    storage-connection="$AZURE_STORAGE_CONNECTION_STRING" \
    servicebus-connection="$AZURE_SERVICEBUS_CONNECTION_STRING" \
  --env-vars \
    DATABASE_URL=secretref:database-url \
    AZURE_STORAGE_CONNECTION_STRING=secretref:storage-connection \
    AZURE_SERVICEBUS_CONNECTION_STRING=secretref:servicebus-connection \
    STORAGE_BACKEND=azure \
    QUEUE_BACKEND=azure \
    API_KEYS=prod_$(openssl rand -hex 16)

# Get API URL
az containerapp show \
  --name opal-web-api \
  --resource-group opaldevdbeia4dlnxsy4sa \
  --query 'properties.configuration.ingress.fqdn' \
  --output tsv
```

---

## Test the Pipeline

### Create a test job via Azure API:

```bash
# Get API URL
API_URL=$(az containerapp show \
  --name opal-web-api \
  --resource-group opaldevdbeia4dlnxsy4sa \
  --query 'properties.configuration.ingress.fqdn' \
  --output tsv)

# Create job
curl -X POST "https://$API_URL/v1/jobs" \
  -H "X-API-Key: dev_testkey123" \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "test_tenant",
    "brand_profile_id": "default_brand",
    "items": [{
      "filename": "product.jpg"
    }]
  }'
```

### Or test via Supabase Edge Function:

Your existing frontend already works! Just point it to use Azure backend:

1. Update Edge Functions to use Azure Service Bus queue
2. Upload image via frontend
3. Watch orchestrator logs process it

---

## Monitor Processing

Watch the orchestrator process your image:

```bash
az containerapp logs show \
  --name opal-orchestrator \
  --resource-group opaldevdbeia4dlnxsy4sa \
  --follow
```

Expected output:
```
INFO: Received message from Service Bus
INFO: Processing job: job_abc123, item: item_xyz
INFO: [1/5] Downloading from Azure Blob: raw/item_xyz.jpg
INFO: [2/5] Removing background with rembg (U²-Net model)
INFO: Background removed in 8.3s
INFO: [3/5] Generating lifestyle scene with FAL.AI FLUX.1
INFO: Prompt: modern minimalist scene, bright natural lighting...
INFO: FAL.AI generation complete in 12.1s
INFO: [4/5] Compositing product onto scene
INFO: Composite created in 0.4s
INFO: [5/5] Upscaling 2x with Real-ESRGAN
INFO: Upscaling complete in 18.7s
INFO: ✓ Item completed in 39.5s
INFO: Uploaded to Azure Blob: outputs/item_xyz.jpg
INFO: Job item status updated to: completed
```

---

## Architecture

```
┌─────────────┐
│   Frontend  │ (React)
│   (Vite)    │
└──────┬──────┘
       │
       ▼
┌─────────────────────┐
│  Supabase Edge Fns  │ OR  ┌─────────────────┐
│  (TypeScript)       │     │  Azure Web API  │
└──────┬──────────────┘     └────────┬────────┘
       │                             │
       │ Creates job in database     │
       ▼                             ▼
┌──────────────────────────────────────────┐
│       Azure PostgreSQL Database          │
│  - jobs, job_items, job_queue, brands    │
└──────────────────────────────────────────┘
       │
       │ Orchestrator polls queue
       ▼
┌────────────────────────────────────────┐
│   Azure Container Apps - Orchestrator  │
│   - Background removal (rembg)         │
│   - Scene generation (FAL.AI)          │
│   - Compositing (PIL)                  │
│   - Upscaling (Real-ESRGAN)            │
└────────┬───────────────────────────────┘
         │
         ▼
┌─────────────────────┐
│  Azure Blob Storage │
│  - raw/             │
│  - outputs/         │
└─────────────────────┘
```

---

## Cost Estimate

**Monthly Fixed Costs:**
- Container Apps (orchestrator): $30-50
- PostgreSQL Flexible Server: $15-30
- Blob Storage: $5-10
- Service Bus: $10
- **Total: ~$60-100/month**

**Variable Costs:**
- FAL.AI: $0.03 per image processed
- Bandwidth: minimal

**Example:**
- 1,000 images/month: ~$90/month total
- 10,000 images/month: ~$360/month total

---

## Next Steps

1. ✅ Database migrated
2. ✅ Azure resources configured
3. ✅ Orchestrator deployed
4. ⬜ Test full pipeline
5. ⬜ Deploy web API (optional)
6. ⬜ Update frontend config
7. ⬜ Implement brand profiles
8. ⬜ Add multi-scene generation
9. ⬜ Set up monitoring & alerts
10. ⬜ Configure CI/CD pipeline

---

## Troubleshooting

See `QUICK-DEPLOY.md` for detailed troubleshooting steps.

Quick fixes:
```bash
# Increase memory if OOM
az containerapp update --name opal-orchestrator \
  --resource-group opaldevdbeia4dlnxsy4sa --memory 8Gi

# Scale up for more throughput
az containerapp update --name opal-orchestrator \
  --resource-group opaldevdbeia4dlnxsy4sa --min-replicas 2

# Switch upscaling to API (faster, uses FAL.AI)
az containerapp update --name opal-orchestrator \
  --resource-group opaldevdbeia4dlnxsy4sa \
  --set-env-vars UPSCALE_PROVIDER=fal
```

---

**You're ready to process real images with AI!** 🚀
