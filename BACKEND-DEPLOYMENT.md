# OPAL Backend Deployment Guide

## Overview

The OPAL backend has been updated to support **Supabase** as the primary cloud infrastructure, replacing Azure-specific services. This makes deployment much simpler and more cost-effective.

## What Changed?

### ✅ Supabase Integration

**Replaced:**
- Azure Storage → **Supabase Storage**
- Azure Service Bus → **Database-backed Queue**
- Azure PostgreSQL → **Supabase PostgreSQL**

**Benefits:**
- Single platform for all backend services
- Generous free tier
- Simpler deployment
- No vendor lock-in
- Direct SQL access

### 🔄 Backward Compatibility

The backend **still supports Azure** if needed. Configure via environment variables:
- `STORAGE_BACKEND=azure` (instead of supabase)
- `QUEUE_BACKEND=azure` (instead of database)

---

## Prerequisites

### 1. Create Supabase Project

1. Go to [supabase.com](https://supabase.com)
2. Create a new project
3. Wait for provisioning (~2 minutes)
4. Note down:
   - Project URL
   - Service Role Key (Settings → API)
   - Database connection string (Settings → Database)

### 2. Run Database Migration

The schema is already created! The migration ran automatically when you started this session.

**Verify in Supabase Dashboard:**
- Go to Table Editor
- You should see: `jobs`, `job_items`, `job_queue`
- Go to Storage
- You should see: `raw`, `outputs`, `exports` buckets

**If not visible, run manually:**
```sql
-- Copy the SQL from supabase/migrations/001_initial_schema.sql
-- Run in SQL Editor in Supabase Dashboard
```

---

## Quick Start (Docker Compose)

### 1. Configure Environment

Create `.env` file (use `.env.example` as template):

```bash
# Database
DATABASE_URL=postgresql://postgres:[password]@db.[project].supabase.co:5432/postgres

# Supabase
SUPABASE_URL=https://[project].supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
SUPABASE_ANON_KEY=your-anon-key

# Backend Selection
STORAGE_BACKEND=supabase
QUEUE_BACKEND=database

# API Security
API_KEYS=dev_testkey123,tenant1_abc123

# AI Providers (Optional)
BACKGROUND_REMOVAL_PROVIDER=rembg
IMAGE_GEN_PROVIDER=fal
FAL_API_KEY=your-fal-key
UPSCALE_ENABLED=false

# App Config
LOG_LEVEL=INFO
```

### 2. Start Services

```bash
docker-compose up -d
```

This starts:
- **web-api** on port 8080
- **orchestrator** (worker)
- **export-worker** (worker)

### 3. Test API

```bash
curl http://localhost:8080/healthz
```

Expected response:
```json
{
  "status": "healthy",
  "database": "ok",
  "storage": "ok"
}
```

---

## Platform-Specific Deployment

### Option 1: Railway (Recommended)

**Why Railway:**
- Easy Docker deployment
- Automatic HTTPS
- Built-in monitoring
- $5/month credit

**Steps:**

1. **Install Railway CLI:**
   ```bash
   npm install -g @railway/cli
   railway login
   ```

2. **Initialize Project:**
   ```bash
   railway init
   ```

3. **Add Services:**
   ```bash
   # Create web API service
   railway up -d src/web_api/Dockerfile --service web-api

   # Create orchestrator service
   railway up -d src/orchestrator/Dockerfile --service orchestrator

   # Create export worker service
   railway up -d src/export_worker/Dockerfile --service export-worker
   ```

4. **Set Environment Variables:**
   ```bash
   railway variables set DATABASE_URL="postgresql://..."
   railway variables set SUPABASE_URL="https://..."
   railway variables set SUPABASE_SERVICE_ROLE_KEY="..."
   railway variables set API_KEYS="dev_testkey123"
   ```

5. **Deploy:**
   ```bash
   railway up
   ```

**Public URL:** Railway provides automatic HTTPS domain

---

### Option 2: Render

**Steps:**

1. **Connect GitHub Repository**
   - Go to [render.com](https://render.com)
   - New → Web Service
   - Connect your GitHub repo

2. **Create Web API Service:**
   - **Name:** opal-web-api
   - **Runtime:** Docker
   - **Dockerfile Path:** src/web_api/Dockerfile
   - **Port:** 8080

3. **Create Worker Services:**
   - **Orchestrator:** Background Worker, Dockerfile: src/orchestrator/Dockerfile
   - **Export Worker:** Background Worker, Dockerfile: src/export_worker/Dockerfile

4. **Set Environment Variables:**
   - Add all variables from `.env.example`
   - Set in Render dashboard for each service

5. **Deploy:**
   - Automatic on git push

**Free Tier:** Available but services sleep after 15min inactivity

---

### Option 3: Fly.io

**Steps:**

1. **Install Fly CLI:**
   ```bash
   curl -L https://fly.io/install.sh | sh
   fly auth login
   ```

2. **Create App:**
   ```bash
   fly launch --no-deploy
   ```

3. **Deploy Services:**
   ```bash
   # Web API
   fly deploy --dockerfile src/web_api/Dockerfile --app opal-web-api

   # Orchestrator
   fly deploy --dockerfile src/orchestrator/Dockerfile --app opal-orchestrator

   # Export Worker
   fly deploy --dockerfile src/export_worker/Dockerfile --app opal-export-worker
   ```

4. **Set Secrets:**
   ```bash
   fly secrets set DATABASE_URL="..." --app opal-web-api
   fly secrets set SUPABASE_URL="..." --app opal-web-api
   fly secrets set SUPABASE_SERVICE_ROLE_KEY="..." --app opal-web-api
   ```

**Global Distribution:** Fly.io deploys to edge locations worldwide

---

### Option 4: Google Cloud Run

**Steps:**

1. **Build and Push Images:**
   ```bash
   # Authenticate
   gcloud auth login
   gcloud config set project YOUR_PROJECT

   # Build images
   docker build -t gcr.io/YOUR_PROJECT/opal-web-api -f src/web_api/Dockerfile .
   docker build -t gcr.io/YOUR_PROJECT/opal-orchestrator -f src/orchestrator/Dockerfile .

   # Push to Container Registry
   docker push gcr.io/YOUR_PROJECT/opal-web-api
   docker push gcr.io/YOUR_PROJECT/opal-orchestrator
   ```

2. **Deploy to Cloud Run:**
   ```bash
   # Web API (with public access)
   gcloud run deploy opal-web-api \
     --image gcr.io/YOUR_PROJECT/opal-web-api \
     --platform managed \
     --region us-central1 \
     --allow-unauthenticated \
     --port 8080

   # Workers (no public access needed)
   gcloud run deploy opal-orchestrator \
     --image gcr.io/YOUR_PROJECT/opal-orchestrator \
     --platform managed \
     --region us-central1 \
     --no-allow-unauthenticated
   ```

3. **Set Environment Variables:**
   ```bash
   gcloud run services update opal-web-api \
     --set-env-vars DATABASE_URL="...",SUPABASE_URL="...",API_KEYS="..."
   ```

**Auto-scaling:** Scales to zero when not in use (cost-effective)

---

### Option 5: DigitalOcean App Platform

**Steps:**

1. **Connect GitHub:**
   - Go to [cloud.digitalocean.com](https://cloud.digitalocean.com)
   - Create App → GitHub

2. **Configure Services:**
   - **Web API:** Web Service, Dockerfile Path: src/web_api/Dockerfile
   - **Orchestrator:** Worker, Dockerfile Path: src/orchestrator/Dockerfile
   - **Export Worker:** Worker, Dockerfile Path: src/export_worker/Dockerfile

3. **Set Environment Variables:**
   - Add variables in App Platform dashboard

4. **Deploy:**
   - Automatic on configuration

**Cost:** Starts at $5/month per service

---

## Environment Variables Reference

### Required

```bash
# Database
DATABASE_URL=postgresql://user:pass@host:5432/db

# Supabase
SUPABASE_URL=https://project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-key
SUPABASE_ANON_KEY=your-key

# Security
API_KEYS=tenant1_key1,tenant2_key2
```

### Optional (AI Features)

```bash
# Background Removal
BACKGROUND_REMOVAL_PROVIDER=rembg
REMOVEBG_API_KEY=

# Image Generation
IMAGE_GEN_PROVIDER=fal
FAL_API_KEY=
REPLICATE_API_KEY=
HUGGINGFACE_API_KEY=

# Upscaling
UPSCALE_PROVIDER=realesrgan
UPSCALE_ENABLED=false
```

### Configuration

```bash
STORAGE_BACKEND=supabase
QUEUE_BACKEND=database
LOG_LEVEL=INFO
ENV_NAME=production
```

---

## Testing Deployment

### 1. Health Check

```bash
curl https://your-api-url.com/healthz
```

Expected:
```json
{
  "status": "healthy",
  "database": "ok",
  "storage": "ok"
}
```

### 2. Create Job

```bash
curl -X POST https://your-api-url.com/v1/jobs \
  -H "X-API-Key: dev_testkey123" \
  -H "Content-Type: application/json" \
  -d '{
    "items": [
      {"filename": "test.jpg"}
    ]
  }'
```

### 3. Check Job

```bash
curl https://your-api-url.com/v1/jobs/{job_id} \
  -H "X-API-Key: dev_testkey123"
```

---

## Monitoring & Debugging

### View Logs

**Docker Compose:**
```bash
docker-compose logs -f web-api
docker-compose logs -f orchestrator
docker-compose logs -f export-worker
```

**Railway:**
```bash
railway logs --service web-api
```

**Render:**
- View in Render dashboard

**Cloud Run:**
```bash
gcloud logging read "resource.type=cloud_run_revision" --limit 50
```

### Database Queries

Connect to Supabase SQL Editor and run:

```sql
-- Check recent jobs
SELECT * FROM jobs ORDER BY created_at DESC LIMIT 10;

-- Check queue status
SELECT queue_name, status, COUNT(*)
FROM job_queue
GROUP BY queue_name, status;

-- Check failed items
SELECT * FROM job_items WHERE status = 'failed';
```

---

## Scaling

### Horizontal Scaling

**Workers:** Add more orchestrator/export-worker instances

**Docker Compose:**
```bash
docker-compose up -d --scale orchestrator=3 --scale export-worker=2
```

**Railway/Render:** Add replicas in dashboard

### Vertical Scaling

Increase resources in platform settings:
- CPU: 0.5 → 1.0 vCPU
- Memory: 512MB → 1GB

### Performance Tips

1. **Disable upscaling** for faster processing: `UPSCALE_ENABLED=false`
2. **Use local rembg** instead of API: `BACKGROUND_REMOVAL_PROVIDER=rembg`
3. **Database connection pool:** Already optimized (20 connections)
4. **Queue polling:** Workers poll every 5 seconds

---

## Cost Estimates

### Supabase (Free Tier)
- ✅ 500MB database
- ✅ 1GB file storage
- ✅ 50MB bandwidth

**Upgrade ($25/month):**
- 8GB database
- 100GB storage
- 250GB bandwidth

### Deployment Platform

**Railway:** $5/month credit (free trial), then ~$10-20/month

**Render:** Free tier available, $7/month per service for paid

**Fly.io:** $0-10/month (generous free tier)

**Cloud Run:** Pay per use, ~$5-15/month

**Total Estimated Cost:** $10-30/month for low-medium traffic

---

## Troubleshooting

### "Database connection failed"

**Check:**
1. DATABASE_URL format correct
2. Supabase project is active
3. IP whitelist disabled (or your IP added)

### "Storage operation failed"

**Check:**
1. SUPABASE_SERVICE_ROLE_KEY is correct
2. Storage buckets exist (raw, outputs, exports)
3. RLS policies allow service role access

### "No messages in queue"

**Check:**
1. Job was enqueued: `POST /v1/jobs/{id}/enqueue`
2. Queue backend is 'database': `QUEUE_BACKEND=database`
3. Orchestrator is running: Check logs

### "Workers not processing"

**Check:**
1. Environment variables set on worker services
2. DATABASE_URL accessible from workers
3. Check worker logs for errors

---

## Security Checklist

- [ ] Changed default API keys
- [ ] Used SUPABASE_SERVICE_ROLE_KEY (not anon key)
- [ ] Enabled RLS on Supabase tables
- [ ] HTTPS enabled on web API
- [ ] Secrets in environment variables (not code)
- [ ] Database connection uses SSL
- [ ] Rate limiting configured (if needed)

---

## Next Steps

1. **Deploy Backend** using one of the platforms above
2. **Update Frontend** environment variables:
   ```env
   VITE_API_URL=https://your-backend-url.com
   VITE_API_KEY=your_api_key
   ```
3. **Test End-to-End** workflow
4. **Monitor** logs and performance
5. **Scale** as needed

---

## Support

**Backend Issues:**
- Check logs first
- Verify environment variables
- Test database connectivity
- Review Supabase dashboard

**Performance:**
- Disable upscaling for faster processing
- Scale workers horizontally
- Optimize AI provider selection

**Costs:**
- Stay within Supabase free tier limits
- Use serverless platforms for auto-scaling
- Monitor bandwidth usage

---

**Documentation:**
- Frontend: See `FRONTEND-GUIDE.md`
- Security: See `CODE-REVIEW-FIXES.md`
- Infrastructure: See `DEPLOYMENT.md`

**Version:** OPAL Platform v0.2.1 with Supabase Support
