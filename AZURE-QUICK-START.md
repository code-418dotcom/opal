# Azure Backend - Quick Start Guide

Your OPAL platform is now configured to use Azure infrastructure!

## 🎯 What's Running

### **Backend Services (Azure Container Apps)**
- **Web API**: `https://opal-web-api-dev.victoriousmoss-91bcd75e.westeurope.azurecontainerapps.io`
- **Orchestrator**: Background worker processing images
- **Export Worker**: Creates export variants
- **Billing Service**: Handles billing/credits

### **Infrastructure**
- **Database**: Azure PostgreSQL (North Europe)
- **Storage**: Azure Blob Storage
- **Queue**: Azure Service Bus
- **Registry**: Azure Container Registry

All services are ✅ **RUNNING** and ✅ **HEALTHY**

---

## 🚀 Quick Start (3 Steps)

### **Step 1: Start Frontend (Already Configured!)**

Your [frontend/.env.local](frontend/.env.local) is already set up for Azure:

```bash
cd frontend
npm install
npm run dev
```

Visit: **http://localhost:5173**

### **Step 2: Test the Application**

1. **Upload an image** - Click the upload button
2. **Create a job** - Process your image
3. **Monitor status** - Watch real-time updates
4. **Download result** - Get your processed image

### **Step 3: Deploy Frontend to Azure (Optional)**

Your frontend Static Web App is already deployed:
- Check: Azure Portal → `opal-frontend-dev`
- It needs environment variables configured

---

## 🔄 Switching Between Backends

Your frontend now supports **both** Supabase and Azure!

### **For Azure (Current):**
Edit [frontend/.env.local](frontend/.env.local):
```bash
VITE_BACKEND_TYPE=azure
VITE_API_URL=https://opal-web-api-dev.victoriousmoss-91bcd75e.westeurope.azurecontainerapps.io
VITE_API_KEY=dev_testkey123
```

### **For Supabase:**
Edit [frontend/.env.local](frontend/.env.local):
```bash
VITE_BACKEND_TYPE=supabase
VITE_SUPABASE_URL=https://YOUR_PROJECT.supabase.co
VITE_SUPABASE_ANON_KEY=YOUR_ANON_KEY
VITE_API_KEY=dev_testkey123
```

---

## 🔍 Monitoring Your Azure Backend

### **Check Service Health**
```bash
curl https://opal-web-api-dev.victoriousmoss-91bcd75e.westeurope.azurecontainerapps.io/healthz
```

Expected:
```json
{
  "status": "ok",
  "db": "ok",
  "storage": "ok",
  "service_bus": "ok"
}
```

### **View Logs**
```bash
# Web API logs
az containerapp logs show -n opal-web-api-dev -g opal-dev-rg --follow

# Orchestrator logs (image processing)
az containerapp logs show -n opal-orchestrator-dev -g opal-dev-rg --follow
```

### **Check Resource Status**
```bash
az containerapp list -g opal-dev-rg --query "[].{Name:name, Status:properties.runningStatus}" -o table
```

---

## 📊 Architecture

```
┌─────────────┐
│   Frontend  │ (React + Vite)
│  localhost  │
└──────┬──────┘
       │ VITE_BACKEND_TYPE=azure
       ▼
┌───────────────────────────────────────────┐
│  Azure Container Apps - Web API           │
│  opal-web-api-dev.victoriousmoss...       │
└──────┬────────────────────────────────────┘
       │
       ├─► Azure PostgreSQL (jobs, items)
       ├─► Azure Blob Storage (images)
       └─► Azure Service Bus (queue)
              │
              ▼
       ┌────────────────────────────┐
       │  Orchestrator Worker       │
       │  - Background removal      │
       │  - AI generation (FAL.AI)  │
       │  - Compositing             │
       │  - Upscaling              │
       └────────────────────────────┘
```

---

## 🛠️ Troubleshooting

### **Frontend can't connect to API**
1. Check [frontend/.env.local](frontend/.env.local) has correct URL
2. Verify `VITE_BACKEND_TYPE=azure`
3. Restart dev server: `npm run dev`

### **Jobs not processing**
```bash
# Check orchestrator logs
az containerapp logs show -n opal-orchestrator-dev -g opal-dev-rg --tail 50
```

### **Need to update backend code**
```bash
# Rebuild and push images
docker build -t opaldevdbeia4dlnxsy4.azurecr.io/web_api:latest -f src/web_api/Dockerfile .
docker push opaldevdbeia4dlnxsy4.azurecr.io/web_api:latest

# Update container app
az containerapp update -n opal-web-api-dev -g opal-dev-rg --image opaldevdbeia4dlnxsy4.azurecr.io/web_api:latest
```

---

## 💰 Cost Management

**Current Setup:**
- Container Apps: ~$50/month (4 services)
- PostgreSQL: ~$20/month
- Storage: ~$5/month
- Service Bus: ~$10/month
- **Total: ~$85/month** + FAL.AI API costs

**To reduce costs:**
```bash
# Scale down to 0 replicas when not in use
az containerapp update -n opal-orchestrator-dev -g opal-dev-rg --min-replicas 0
```

---

## 📚 Next Steps

1. ✅ **Backend is running**
2. ✅ **Frontend is configured**
3. ⬜ **Add AI provider credentials** (FAL.AI API key)
4. ⬜ **Test full image processing flow**
5. ⬜ **Deploy frontend to Azure Static Web Apps**
6. ⬜ **Set up CI/CD pipeline**

---

## 🎉 You're All Set!

Your OPAL platform is now running on Azure with:
- ✅ PostgreSQL database
- ✅ Blob storage for images
- ✅ Service Bus for queuing
- ✅ Container Apps for scalable backend
- ✅ Frontend configured to use Azure

**Start developing:** `cd frontend && npm run dev`

For questions, check the main [README.md](README.md) or other documentation files.
