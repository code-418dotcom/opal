# Azure Deployment Guide - OPAL AI Pipeline

## Overview

Deploy the OPAL platform to Azure with full AI processing capabilities.

**Architecture:**
- **Frontend**: Supabase Edge Functions → Azure (current Bolt setup can remain)
- **Orchestrator**: Azure Container Apps (NEW - runs AI pipeline)
- **Database**: Supabase PostgreSQL (or migrate to Azure PostgreSQL)
- **Storage**: Azure Blob Storage
- **Queue**: Azure Service Bus
- **AI**: FAL.AI (scene generation), rembg (background removal), Real-ESRGAN (upscaling)

---

## Prerequisites

1. **Azure CLI** installed: `az login`
2. **Docker** installed (for building images)
3. **FAL.AI API Key**: Get from https://fal.ai/dashboard
4. **Azure resources** (you already have these from screenshot):
   - Resource Group: `opaldevdbeia4dlnxsy4sa` (or create new)
   - Service Bus Namespace: `opal-dev-dbeia4dlnxsy4-bus`
   - Storage Account: `opaldevdbeia4dlnxsy4sa`
   - Container Registry: `opaldevdbeia4dlnxsy4`

---

## Step 1: Set Up Azure Blob Storage

Create containers for images:

```bash
az storage container create \
  --name raw \
  --account-name opaldevdbeia4dlnxsy4sa

az storage container create \
  --name outputs \
  --account-name opaldevdbeia4dlnxsy4sa
```

Get connection string:

```bash
az storage account show-connection-string \
  --name opaldevdbeia4dlnxsy4sa \
  --resource-group opaldevdbeia4dlnxsy4sa \
  --output tsv
```

Save this as `AZURE_STORAGE_CONNECTION_STRING`

---

## Step 2: Set Up Azure Service Bus Queue

Create queue for job processing:

```bash
az servicebus queue create \
  --name jobs \
  --namespace-name opal-dev-dbeia4dlnxsy4-bus \
  --resource-group opaldevdbeia4dlnxsy4sa
```

Get connection string:

```bash
az servicebus namespace authorization-rule keys list \
  --resource-group opaldevdbeia4dlnxsy4sa \
  --namespace-name opal-dev-dbeia4dlnxsy4-bus \
  --name RootManageSharedAccessKey \
  --query primaryConnectionString \
  --output tsv
```

Save this as `AZURE_SERVICEBUS_CONNECTION_STRING`

---

## Step 3: Build and Push Orchestrator Container

```bash
# Login to your Azure Container Registry
az acr login --name opaldevdbeia4dlnxsy4

# Build the orchestrator image
docker build -t opaldevdbeia4dlnxsy4.azurecr.io/orchestrator:latest -f src/orchestrator/Dockerfile .

# Push to registry
docker push opaldevdbeia4dlnxsy4.azurecr.io/orchestrator:latest
```

---

## Step 4: Create Container Apps Environment

```bash
# Create Container Apps Environment (if not exists)
az containerapp env create \
  --name opal-dev-cae \
  --resource-group opaldevdbeia4dlnxsy4sa \
  --location westeurope
```

---

## Step 5: Deploy Orchestrator Worker

Create `.env.azure` file with your config:

```env
# Database (keep using Supabase)
DATABASE_URL=postgresql://postgres:your-password@db.yourproject.supabase.co:5432/postgres

# Azure
AZURE_STORAGE_CONNECTION_STRING=<from step 1>
AZURE_SERVICEBUS_CONNECTION_STRING=<from step 2>
SERVICEBUS_JOBS_QUEUE=jobs

# AI Providers
FAL_API_KEY=<your-fal-api-key>
BACKGROUND_REMOVAL_PROVIDER=rembg
IMAGE_GEN_PROVIDER=fal
UPSCALE_PROVIDER=realesrgan
UPSCALE_ENABLED=true

# Config
LOG_LEVEL=INFO
STORAGE_BACKEND=azure
QUEUE_BACKEND=azure
```

Deploy orchestrator:

```bash
# Deploy container app
az containerapp create \
  --name opal-orchestrator-dev \
  --resource-group opaldevdbeia4dlnxsy4sa \
  --environment opal-dev-cae \
  --image opaldevdbeia4dlnxsy4.azurecr.io/orchestrator:latest \
  --registry-server opaldevdbeia4dlnxsy4.azurecr.io \
  --cpu 2 \
  --memory 4Gi \
  --min-replicas 1 \
  --max-replicas 3 \
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

Set secrets:

```bash
az containerapp secret set \
  --name opal-orchestrator-dev \
  --resource-group opaldevdbeia4dlnxsy4sa \
  --secrets \
    database-url="<your-database-url>" \
    storage-connection="<your-storage-connection-string>" \
    servicebus-connection="<your-servicebus-connection-string>" \
    fal-api-key="<your-fal-api-key>"
```

---

## Step 6: Deploy Web API (Optional)

If you want to move the API from Supabase to Azure:

```bash
docker build -t opaldevdbeia4dlnxsy4.azurecr.io/web-api:latest -f src/web_api/Dockerfile .
docker push opaldevdbeia4dlnxsy4.azurecr.io/web-api:latest

az containerapp create \
  --name opal-web-api-dev \
  --resource-group opaldevdbeia4dlnxsy4sa \
  --environment opal-dev-cae \
  --image opaldevdbeia4dlnxsy4.azurecr.io/web-api:latest \
  --target-port 8080 \
  --ingress external \
  --cpu 0.5 \
  --memory 1Gi \
  --min-replicas 1 \
  --max-replicas 5
```

---

## Step 7: Connect Frontend to Azure Backend

Update your frontend environment variables:

```env
# If using Azure Web API
VITE_API_URL=https://opal-web-api-dev.yourdomain.com

# If keeping Supabase Edge Functions (hybrid approach)
VITE_SUPABASE_URL=https://yourproject.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key
```

---

## Step 8: Test the Pipeline

1. **Upload an image** via your frontend
2. **Check logs**:
   ```bash
   az containerapp logs show \
     --name opal-orchestrator-dev \
     --resource-group opaldevdbeia4dlnxsy4sa \
     --follow
   ```

3. **Expected log output**:
   ```
   [1/5] Downloading input
   [2/5] Removing background with rembg
   [3/5] Generating lifestyle scene with fal.ai
   [4/5] Compositing product onto scene
   [5/5] Upscaling with realesrgan
   ✓ Item completed
   ```

---

## Architecture Options

### Option A: Hybrid (Recommended for Quick Start)

**Frontend**: Supabase Edge Functions (current)
**Backend**: Azure Container Apps (orchestrator only)
**Database**: Supabase PostgreSQL
**Storage**: Azure Blob Storage
**Queue**: Azure Service Bus

**Pros**: Minimal changes, quick deployment
**Cons**: Split infrastructure

### Option B: Full Azure

**Frontend**: Azure Static Web Apps
**Backend**: Azure Container Apps (all services)
**Database**: Azure PostgreSQL Flexible Server
**Storage**: Azure Blob Storage
**Queue**: Azure Service Bus

**Pros**: Everything in Azure, easier management
**Cons**: More migration work

---

## Cost Estimate (Option A)

- **Azure Container Apps** (orchestrator): ~$30/month (1 replica, 2 CPU, 4GB RAM)
- **Azure Blob Storage**: ~$5/month (100GB)
- **Azure Service Bus**: ~$10/month (Basic tier)
- **FAL.AI**: ~$0.03/image
- **Supabase**: Free tier (or $25/month Pro)

**Total**: ~$45-70/month + $0.03 per image processed

---

## Troubleshooting

### Orchestrator not processing jobs

Check if worker is running:
```bash
az containerapp logs show --name opal-orchestrator-dev --resource-group opaldevdbeia4dlnxsy4sa --follow
```

### Background removal slow

Switch to remove.bg API:
```bash
az containerapp update \
  --name opal-orchestrator-dev \
  --resource-group opaldevdbeia4dlnxsy4sa \
  --set-env-vars BACKGROUND_REMOVAL_PROVIDER=remove.bg REMOVEBG_API_KEY=<key>
```

### Out of memory errors

Increase memory:
```bash
az containerapp update \
  --name opal-orchestrator-dev \
  --resource-group opaldevdbeia4dlnxsy4sa \
  --memory 8Gi
```

---

## Next Steps

1. ✅ Deploy orchestrator to Azure Container Apps
2. ✅ Test full AI pipeline
3. ⬜ Deploy web API to Azure (optional)
4. ⬜ Migrate frontend to Azure Static Web Apps (optional)
5. ⬜ Set up CI/CD with GitHub Actions
6. ⬜ Add monitoring with Application Insights
7. ⬜ Implement brand profiles
8. ⬜ Add multi-scene generation
