#!/bin/bash
set -e

# OPAL Azure Deployment Script
# This script deploys the orchestrator to Azure Container Apps

echo "========================================"
echo "OPAL Azure Deployment"
echo "========================================"
echo ""

# Configuration
RESOURCE_GROUP="${RESOURCE_GROUP:-opaldevdbeia4dlnxsy4sa}"
ACR_NAME="${ACR_NAME:-opaldevdbeia4dlnxsy4}"
CONTAINER_ENV="${CONTAINER_ENV:-opal-dev-cae}"
APP_NAME="${APP_NAME:-opal-orchestrator-dev}"
LOCATION="${LOCATION:-westeurope}"

# Check prerequisites
command -v az >/dev/null 2>&1 || { echo "Error: Azure CLI not installed"; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "Error: Docker not installed"; exit 1; }

# Check if logged in to Azure
az account show >/dev/null 2>&1 || { echo "Error: Not logged in to Azure. Run: az login"; exit 1; }

echo "Configuration:"
echo "  Resource Group: $RESOURCE_GROUP"
echo "  Container Registry: $ACR_NAME"
echo "  Container Environment: $CONTAINER_ENV"
echo "  App Name: $APP_NAME"
echo ""

# Prompt for secrets if not set
if [ -z "$DATABASE_URL" ]; then
    echo "Enter DATABASE_URL (Supabase PostgreSQL):"
    read -s DATABASE_URL
    echo ""
fi

if [ -z "$AZURE_STORAGE_CONNECTION_STRING" ]; then
    echo "Enter AZURE_STORAGE_CONNECTION_STRING:"
    read -s AZURE_STORAGE_CONNECTION_STRING
    echo ""
fi

if [ -z "$AZURE_SERVICEBUS_CONNECTION_STRING" ]; then
    echo "Enter AZURE_SERVICEBUS_CONNECTION_STRING:"
    read -s AZURE_SERVICEBUS_CONNECTION_STRING
    echo ""
fi

if [ -z "$FAL_API_KEY" ]; then
    echo "Enter FAL_API_KEY (get from https://fal.ai/dashboard):"
    read -s FAL_API_KEY
    echo ""
fi

echo "Step 1: Login to Azure Container Registry..."
az acr login --name $ACR_NAME

echo "Step 2: Building orchestrator Docker image..."
docker build -t $ACR_NAME.azurecr.io/orchestrator:latest -f src/orchestrator/Dockerfile .

echo "Step 3: Pushing image to registry..."
docker push $ACR_NAME.azurecr.io/orchestrator:latest

echo "Step 4: Checking if Container Apps Environment exists..."
if ! az containerapp env show --name $CONTAINER_ENV --resource-group $RESOURCE_GROUP >/dev/null 2>&1; then
    echo "Creating Container Apps Environment..."
    az containerapp env create \
        --name $CONTAINER_ENV \
        --resource-group $RESOURCE_GROUP \
        --location $LOCATION
fi

echo "Step 5: Deploying orchestrator container app..."
if az containerapp show --name $APP_NAME --resource-group $RESOURCE_GROUP >/dev/null 2>&1; then
    echo "Updating existing container app..."
    az containerapp update \
        --name $APP_NAME \
        --resource-group $RESOURCE_GROUP \
        --image $ACR_NAME.azurecr.io/orchestrator:latest
else
    echo "Creating new container app..."
    az containerapp create \
        --name $APP_NAME \
        --resource-group $RESOURCE_GROUP \
        --environment $CONTAINER_ENV \
        --image $ACR_NAME.azurecr.io/orchestrator:latest \
        --registry-server $ACR_NAME.azurecr.io \
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
fi

echo ""
echo "========================================"
echo "✓ Deployment Complete!"
echo "========================================"
echo ""
echo "View logs:"
echo "  az containerapp logs show --name $APP_NAME --resource-group $RESOURCE_GROUP --follow"
echo ""
echo "Check status:"
echo "  az containerapp show --name $APP_NAME --resource-group $RESOURCE_GROUP --query 'properties.runningStatus'"
echo ""
