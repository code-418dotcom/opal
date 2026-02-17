# Quick Azure Deployment - OPAL Orchestrator

## You Have Everything Ready!

From your Azure portal screenshot, you have:
- ✅ Resource Group: `opaldevdbeia4dlnxsy4sa`
- ✅ Container Registry: `opaldevdbeia4dlnxsy4`
- ✅ Storage Account: `opaldevdbeia4dlnxsy4sa`
- ✅ Service Bus: `opal-dev-dbeia4dlnxsy4-bus`
- ✅ PostgreSQL Database: `opal-dev-dbeia4dlnxsy4-pg-ne`
- ✅ FAL.AI API Key: `09c4a4ef-8788-497c-a417-91aa605dfb98:...`

---

## Step 1: Get Connection Strings (Run on Your Local Machine)

Open PowerShell or Terminal and run:

```bash
# Login to Azure (if not already)
az login

# Get Storage Connection String
az storage account show-connection-string \
  --name opaldevdbeia4dlnxsy4sa \
  --resource-group opaldevdbeia4dlnxsy4sa \
  --output tsv

# Get Service Bus Connection String
az servicebus namespace authorization-rule keys list \
  --resource-group opaldevdbeia4dlnxsy4sa \
  --namespace-name opal-dev-dbeia4dlnxsy4-bus \
  --name RootManageSharedAccessKey \
  --query primaryConnectionString \
  --output tsv
```

Save these outputs - you'll need them in Step 3.

---

## Step 2: Create Storage Containers & Service Bus Queue

```bash
# Create blob storage containers
az storage container create \
  --name raw \
  --account-name opaldevdbeia4dlnxsy4sa

az storage container create \
  --name outputs \
  --account-name opaldevdbeia4dlnxsy4sa

# Create Service Bus queue
az servicebus queue create \
  --name jobs \
  --namespace-name opal-dev-dbeia4dlnxsy4-bus \
  --resource-group opaldevdbeia4dlnxsy4sa
```

---

## Step 3: Set Environment Variables

Create a file `.env.azure` in the project root:

```env
# Database (your Azure PostgreSQL)
DATABASE_URL=postgresql+psycopg://opaladmin:YOUR_PASSWORD@opal-dev-dbeia4dlnxsy4-pg-ne.postgres.database.azure.com:5432/opal?sslmode=require

# Azure Storage (from Step 1)
AZURE_STORAGE_CONNECTION_STRING=<paste-from-step-1>

# Azure Service Bus (from Step 1)
AZURE_SERVICEBUS_CONNECTION_STRING=<paste-from-step-1>

# FAL.AI (Get from https://fal.ai/dashboard)
FAL_API_KEY=YOUR_FAL_API_KEY_HERE

# Config
SERVICEBUS_JOBS_QUEUE=jobs
STORAGE_BACKEND=azure
QUEUE_BACKEND=azure
BACKGROUND_REMOVAL_PROVIDER=rembg
IMAGE_GEN_PROVIDER=fal
UPSCALE_PROVIDER=realesrgan
UPSCALE_ENABLED=true
LOG_LEVEL=INFO
```

Then load them:

```bash
# PowerShell
Get-Content .env.azure | ForEach-Object {
  $name, $value = $_.split('=', 2)
  Set-Item -Path "env:$name" -Value $value
}

# Bash/Terminal
export $(cat .env.azure | xargs)
```

---

## Step 4: Build & Deploy Orchestrator

```bash
# Navigate to project directory
cd /path/to/opal-platform

# Login to Azure Container Registry
az acr login --name opaldevdbeia4dlnxsy4

# Build and push Docker image
docker build -t opaldevdbeia4dlnxsy4.azurecr.io/orchestrator:latest -f src/orchestrator/Dockerfile .
docker push opaldevdbeia4dlnxsy4.azurecr.io/orchestrator:latest

# Create Container Apps Environment (if needed)
az containerapp env create \
  --name opal-dev-cae \
  --resource-group opaldevdbeia4dlnxsy4sa \
  --location westeurope

# Deploy the orchestrator
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

## Step 5: Verify Deployment

```bash
# Check status
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

Expected log output:
```
INFO: Worker started, listening to queue: jobs
INFO: Waiting for messages...
```

---

## Step 6: Update Frontend (Optional)

If you want to switch from Supabase Edge Functions to Azure-based API:

### Option A: Keep Current Setup (Easiest)
Your frontend already works with Supabase. Just update the orchestrator to use Azure storage:
- Jobs are created via Supabase Edge Functions
- Orchestrator processes them using Azure
- Results stored in Azure Blob Storage

### Option B: Deploy Web API to Azure
```bash
# Build and push web API
docker build -t opaldevdbeia4dlnxsy4.azurecr.io/web-api:latest -f src/web_api/Dockerfile .
docker push opaldevdbeia4dlnxsy4.azurecr.io/web-api:latest

# Deploy web API
az containerapp create \
  --name opal-web-api \
  --resource-group opaldevdbeia4dlnxsy4sa \
  --environment opal-dev-cae \
  --image opaldevdbeia4dlnxsy4.azurecr.io/web-api:latest \
  --target-port 8080 \
  --ingress external \
  --cpu 0.5 \
  --memory 1Gi \
  --min-replicas 1 \
  --max-replicas 5 \
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
    API_KEYS=dev_testkey123
```

Get the API URL:
```bash
az containerapp show \
  --name opal-web-api \
  --resource-group opaldevdbeia4dlnxsy4sa \
  --query 'properties.configuration.ingress.fqdn' \
  --output tsv
```

Update frontend/.env.local:
```
VITE_API_URL=https://<api-url-from-above>
VITE_API_KEY=dev_testkey123
```

---

## Test the Full Pipeline

1. **Upload a product image** via your frontend
2. **Check Azure logs**:
   ```bash
   az containerapp logs show --name opal-orchestrator --resource-group opaldevdbeia4dlnxsy4sa --follow
   ```

3. **Expected output**:
   ```
   INFO: Received message: job_abc123
   INFO: Processing item: item_xyz
   INFO: [1/5] Downloading input from Azure Blob
   INFO: [2/5] Removing background with rembg
   INFO: [3/5] Generating lifestyle scene with fal.ai
   INFO: FAL.AI generation successful
   INFO: [4/5] Compositing product onto scene
   INFO: [5/5] Upscaling with realesrgan
   INFO: ✓ Item completed in 45.2s
   INFO: Uploaded output to: outputs/item_xyz.jpg
   ```

4. **Download the result** from your frontend

---

## Troubleshooting

### Container won't start
```bash
# Check logs for errors
az containerapp logs show --name opal-orchestrator --resource-group opaldevdbeia4dlnxsy4sa --tail 50
```

### Out of memory
```bash
# Increase memory to 8GB
az containerapp update \
  --name opal-orchestrator \
  --resource-group opaldevdbeia4dlnxsy4sa \
  --memory 8Gi
```

### Slow processing
```bash
# Add more replicas
az containerapp update \
  --name opal-orchestrator \
  --resource-group opaldevdbeia4dlnxsy4sa \
  --min-replicas 2 \
  --max-replicas 5
```

### Switch to API-based upscaling (faster)
```bash
# Update to use FAL.AI for upscaling too
az containerapp update \
  --name opal-orchestrator \
  --resource-group opaldevdbeia4dlnxsy4sa \
  --set-env-vars UPSCALE_PROVIDER=fal
```

---

## Cost Monitoring

View Container Apps costs:
```bash
az costmanagement query \
  --type Usage \
  --dataset-filter "{\"and\":[{\"dimensions\":{\"name\":\"ResourceGroup\",\"operator\":\"In\",\"values\":[\"opaldevdbeia4dlnxsy4sa\"]}}]}" \
  --timeframe MonthToDate
```

---

## Next Steps

1. ✅ Deploy orchestrator to Azure
2. ⬜ Test full pipeline with real images
3. ⬜ Monitor costs and performance
4. ⬜ Implement brand profiles feature
5. ⬜ Add multi-scene generation
6. ⬜ Set up CI/CD pipeline
