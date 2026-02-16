# OPAL Platform Deployment Guide

## Architecture Overview

The OPAL platform consists of two main parts:

1. **Frontend** - React/Vite SPA (Static Site)
2. **Backend** - Python microservices (Container-based)

These must be deployed separately to different infrastructure.

---

## Frontend Deployment

The frontend is a static React application that can be deployed to any static hosting service.

### Option 1: Netlify (Recommended for Quick Deploy)

**Automatic Detection:**
The `netlify.toml` is configured to:
- Build from `frontend/` directory
- Output to `frontend/dist`
- Handle SPA routing

**Manual Steps:**
1. Connect repository to Netlify
2. Deploy! (auto-configured)

**Environment Variables:**
Set in Netlify dashboard:
```
VITE_API_URL=https://your-backend-api.com
VITE_API_KEY=your_api_key
```

### Option 2: Vercel

**Automatic Detection:**
The `vercel.json` is configured for automatic deployment.

**Manual Steps:**
1. Connect repository to Vercel
2. Deploy! (auto-configured)

**Environment Variables:**
Set in Vercel dashboard:
```
VITE_API_URL=https://your-backend-api.com
VITE_API_KEY=your_api_key
```

### Option 3: Static Host (Cloudflare Pages, GitHub Pages, etc.)

**Build Steps:**
```bash
cd frontend
npm install
npm run build
```

**Output:** `frontend/dist/`

Upload the `dist/` folder to your static host.

### Option 4: Local Development

```bash
cd frontend
npm install
npm run dev
```

Access at: http://localhost:5173

---

## Backend Deployment

The backend consists of multiple Python microservices that should be deployed as containers.

### Services

1. **web_api** - REST API (port 8080)
2. **orchestrator** - Job processing worker
3. **export_worker** - Export generation worker
4. **billing_service** - Billing/payment handling (port 8081)

### Azure Container Apps (Current Infrastructure)

The project includes Azure Bicep templates:
- `infra/main.bicep` - Infrastructure as Code
- `.github/workflows/` - CI/CD pipelines

**Deploy using GitHub Actions:**
```bash
# Push to main branch
git push origin main
```

The workflows will:
1. Build Docker images
2. Push to Azure Container Registry
3. Deploy to Azure Container Apps

**Manual Azure Deploy:**
```bash
az deployment group create \
  --resource-group opal-rg-dev \
  --template-file infra/main.bicep \
  --parameters infra/main.parameters.json
```

### Docker Compose (Local Development)

Each service has a `Dockerfile`. To run locally:

```bash
# Web API
cd src/web_api
docker build -t opal-web-api .
docker run -p 8080:8080 --env-file ../../.env opal-web-api

# Orchestrator
cd src/orchestrator
docker build -t opal-orchestrator .
docker run --env-file ../../.env opal-orchestrator

# Export Worker
cd src/export_worker
docker build -t opal-export-worker .
docker run --env-file ../../.env opal-export-worker

# Billing Service
cd src/billing_service
docker build -t opal-billing .
docker run -p 8081:8081 --env-file ../../.env opal-billing
```

---

## Environment Configuration

### Frontend Environment Variables

Required in frontend deployment platform:

```env
VITE_API_URL=https://your-backend-url.com
VITE_API_KEY=your_tenant_apikey123
```

### Backend Environment Variables

Required for all backend services:

```env
# Database
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# Azure Storage
STORAGE_ACCOUNT_NAME=yourstorageaccount

# Service Bus
SERVICEBUS_NAMESPACE=yourservicebus

# API Security
API_KEYS=tenant1_key123,tenant2_key456

# AI Providers (Optional)
REMOVEBG_API_KEY=your_key
FAL_API_KEY=your_key
REPLICATE_API_KEY=your_key
HUGGINGFACE_API_KEY=your_key

# Configuration
LOG_LEVEL=INFO
UPSCALE_ENABLED=true
```

---

## Deployment Checklist

### Pre-Deployment

- [ ] Review `CODE-REVIEW-FIXES.md` for security fixes
- [ ] Set up Azure resources (PostgreSQL, Storage, Service Bus)
- [ ] Configure API keys in backend
- [ ] Update `frontend/.env` with backend URL

### Frontend Deployment

- [ ] Choose hosting platform (Netlify/Vercel/etc)
- [ ] Set environment variables
- [ ] Deploy frontend
- [ ] Test frontend loads correctly
- [ ] Verify API connectivity

### Backend Deployment

- [ ] Build and push Docker images
- [ ] Deploy to Azure Container Apps
- [ ] Verify health endpoints
- [ ] Test API authentication
- [ ] Monitor logs for errors

### Post-Deployment

- [ ] Test end-to-end workflow (upload → process → results)
- [ ] Verify tenant isolation
- [ ] Check error handling
- [ ] Monitor performance metrics
- [ ] Set up alerting

---

## Troubleshooting

### "npm ENOENT" Error

**Problem:** Deployment trying to build from root instead of `frontend/`

**Solution:**
- For Netlify: Uses `netlify.toml` (already configured)
- For Vercel: Uses `vercel.json` (already configured)
- For others: Set build directory to `frontend/`

### Frontend Can't Connect to Backend

**Problem:** CORS or network issues

**Solutions:**
1. Verify `VITE_API_URL` is correct
2. Check CORS is enabled on backend (`main.py` has CORSMiddleware)
3. Verify API key matches backend configuration
4. Check network tab in browser DevTools

### Backend Services Not Starting

**Problem:** Missing environment variables or dependencies

**Solutions:**
1. Check all required env vars are set
2. Verify Azure resources are provisioned
3. Check Docker container logs
4. Verify database connectivity

---

## Quick Start Summary

**Frontend Only (Static Host):**
```bash
cd frontend
npm install
npm run build
# Deploy frontend/dist/ to your host
```

**Full Local Development:**
```bash
# Terminal 1: Frontend
cd frontend
npm install
npm run dev

# Terminal 2: Backend (requires Docker)
# Follow Docker Compose instructions above
```

**Production (Azure):**
```bash
# Push to GitHub, workflows handle deployment
git push origin main
```

---

## Support

- Frontend Issues: Check `FRONTEND-GUIDE.md`
- Backend Issues: Check `CODE-REVIEW-FIXES.md`
- Security: Review API authentication setup
- Infrastructure: Check Azure portal and logs

---

**Version:** OPAL Platform v0.2.1
