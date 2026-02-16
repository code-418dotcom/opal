# 🚀 OPAL Platform - Complete Deployment Checklist

Use this checklist to deploy the entire OPAL platform from scratch.

---

## Prerequisites

- [ ] Supabase account created
- [ ] Netlify/Vercel account (for frontend)
- [ ] Railway/Render account (for backend)
- [ ] Domain name (optional)

---

## Phase 1: Supabase Setup

### 1.1 Create Project

- [ ] Go to [supabase.com](https://supabase.com)
- [ ] Create new project
- [ ] Choose region (closest to users)
- [ ] Wait for provisioning (~2 minutes)

### 1.2 Get Credentials

- [ ] Go to Settings → API
- [ ] Copy **Project URL**
- [ ] Copy **Service Role Key** (keep secret!)
- [ ] Copy **Anon Key**
- [ ] Go to Settings → Database
- [ ] Copy **Connection String** (Direct)

### 1.3 Verify Schema

- [ ] Go to Table Editor
- [ ] Check tables exist: `jobs`, `job_items`, `job_queue`
- [ ] Go to Storage
- [ ] Check buckets exist: `raw`, `outputs`, `exports`

**✅ If not visible:** Schema was already created during development session. Everything is ready!

---

## Phase 2: Backend Deployment

### Option A: Railway (Recommended)

#### 2.1 Install Railway CLI

```bash
npm install -g @railway/cli
railway login
```

- [ ] Installed Railway CLI
- [ ] Logged in

#### 2.2 Create Project

```bash
cd /path/to/opal-platform
railway init
```

- [ ] Created Railway project
- [ ] Linked to GitHub (optional)

#### 2.3 Deploy Services

```bash
# Deploy web API
railway up -d src/web_api/Dockerfile --service web-api

# Deploy orchestrator
railway up -d src/orchestrator/Dockerfile --service orchestrator

# Deploy export worker
railway up -d src/export_worker/Dockerfile --service export-worker
```

- [ ] Web API deployed
- [ ] Orchestrator deployed
- [ ] Export worker deployed

#### 2.4 Set Environment Variables

```bash
railway variables set DATABASE_URL="postgresql://..."
railway variables set SUPABASE_URL="https://..."
railway variables set SUPABASE_SERVICE_ROLE_KEY="..."
railway variables set SUPABASE_ANON_KEY="..."
railway variables set API_KEYS="prod_yourkey123"
railway variables set STORAGE_BACKEND="supabase"
railway variables set QUEUE_BACKEND="database"
railway variables set LOG_LEVEL="INFO"
```

- [ ] All environment variables set
- [ ] Verified in Railway dashboard

#### 2.5 Test Backend

- [ ] Get web API URL from Railway
- [ ] Test health: `curl https://your-api.railway.app/healthz`
- [ ] Expected: `{"status":"healthy"}`

### Option B: Render

#### 2.1 Connect Repository

- [ ] Go to [render.com](https://render.com)
- [ ] New → Web Service
- [ ] Connect GitHub repository

#### 2.2 Configure Web API

- [ ] Name: `opal-web-api`
- [ ] Runtime: Docker
- [ ] Dockerfile path: `src/web_api/Dockerfile`
- [ ] Instance type: Starter ($7/month) or Free
- [ ] Environment variables: Add all from .env.example

#### 2.3 Configure Workers

**Orchestrator:**
- [ ] New → Background Worker
- [ ] Name: `opal-orchestrator`
- [ ] Dockerfile: `src/orchestrator/Dockerfile`
- [ ] Instance type: Starter
- [ ] Environment variables: Same as web API

**Export Worker:**
- [ ] New → Background Worker
- [ ] Name: `opal-export-worker`
- [ ] Dockerfile: `src/export_worker/Dockerfile`
- [ ] Instance type: Starter
- [ ] Environment variables: Same as web API

#### 2.4 Deploy

- [ ] Click "Create Web Service"
- [ ] Wait for deployment
- [ ] Check logs for errors

#### 2.5 Test Backend

- [ ] Get URL from Render dashboard
- [ ] Test: `curl https://opal-web-api.onrender.com/healthz`

---

## Phase 3: Frontend Deployment

### Option A: Netlify (Recommended)

#### 3.1 Connect Repository

- [ ] Go to [netlify.com](https://netlify.com)
- [ ] New site from Git
- [ ] Connect GitHub repository

#### 3.2 Configure Build

**Already configured via `netlify.toml`!**

- [ ] Build command: `npm run build` ✅
- [ ] Publish directory: `dist` ✅
- [ ] Base directory: `frontend` ✅

#### 3.3 Set Environment Variables

- [ ] Go to Site settings → Environment variables
- [ ] Add `VITE_API_URL` = `https://your-backend-url.com`
- [ ] Add `VITE_API_KEY` = `prod_yourkey123`

#### 3.4 Deploy

- [ ] Click "Deploy site"
- [ ] Wait for build (~2 minutes)
- [ ] Get site URL

#### 3.5 Test Frontend

- [ ] Open site URL
- [ ] Upload tab should load
- [ ] Try uploading an image
- [ ] Check Monitor tab

### Option B: Vercel

#### 3.1 Import Project

- [ ] Go to [vercel.com](https://vercel.com)
- [ ] New Project
- [ ] Import Git repository

#### 3.2 Configure

**Already configured via `vercel.json`!**

- [ ] Framework: Vite ✅
- [ ] Root directory: `` (leave empty) ✅
- [ ] Build command: Auto-detected ✅

#### 3.3 Environment Variables

- [ ] Add `VITE_API_URL`
- [ ] Add `VITE_API_KEY`

#### 3.4 Deploy

- [ ] Click Deploy
- [ ] Wait for build
- [ ] Get deployment URL

---

## Phase 4: Testing

### 4.1 Frontend Tests

- [ ] Frontend loads successfully
- [ ] No console errors
- [ ] "API Connected" shows in header

### 4.2 Upload Test

- [ ] Go to Upload tab
- [ ] Drag & drop an image
- [ ] Click "Upload & Process"
- [ ] Job ID appears

### 4.3 Monitoring Test

- [ ] Go to Monitor tab
- [ ] Paste job ID
- [ ] Status shows "processing" → "completed"
- [ ] Items show progress

### 4.4 Debug Test

- [ ] Go to Debug tab
- [ ] Type: `health`
- [ ] Press Enter
- [ ] Response shows OK

### 4.5 Results Test

- [ ] Go to Results tab
- [ ] Enter job ID
- [ ] Completed images appear
- [ ] Click "View" or "Download"

---

## Phase 5: Configuration

### 5.1 Custom Domain (Optional)

**Netlify:**
- [ ] Go to Domain settings
- [ ] Add custom domain
- [ ] Configure DNS (CNAME or A record)
- [ ] Wait for SSL certificate (~1 hour)

**Backend:**
- [ ] Add custom domain in Railway/Render
- [ ] Update `VITE_API_URL` in frontend env vars
- [ ] Redeploy frontend

### 5.2 AI Provider Setup (Optional)

**If you want AI features:**

- [ ] Get FAL.AI API key: [fal.ai](https://fal.ai)
- [ ] Add to backend env: `FAL_API_KEY=...`
- [ ] Add to backend env: `IMAGE_GEN_PROVIDER=fal`
- [ ] Restart backend services

### 5.3 Monitoring Setup

**Supabase:**
- [ ] Enable database metrics
- [ ] Set up email alerts
- [ ] Configure backups (automatic on Pro)

**Backend Platform:**
- [ ] Enable health checks
- [ ] Set up email/Slack alerts
- [ ] Configure auto-restart

---

## Phase 6: Production Readiness

### 6.1 Security

- [ ] Changed default API keys
- [ ] Using strong Supabase passwords
- [ ] HTTPS enabled everywhere
- [ ] RLS enabled on Supabase (✅ already done)
- [ ] Service role key kept secret

### 6.2 Performance

- [ ] Workers scaled appropriately
- [ ] Database connection pool configured (✅ done)
- [ ] CDN enabled (Netlify/Vercel provide this)
- [ ] Images optimized

### 6.3 Monitoring

- [ ] Health checks configured
- [ ] Logs accessible
- [ ] Error tracking setup
- [ ] Uptime monitoring (UptimeRobot, etc.)

### 6.4 Backup

- [ ] Supabase automatic backups enabled
- [ ] Database export tested
- [ ] Storage backup strategy defined

---

## Phase 7: Documentation

### 7.1 User Documentation

- [ ] API key distribution process
- [ ] User onboarding guide
- [ ] Support channel defined

### 7.2 Operations

- [ ] Deployment runbook
- [ ] Incident response plan
- [ ] Scaling guidelines
- [ ] Cost monitoring setup

---

## Costs Summary

### Free Tier (Testing)

- **Supabase:** Free tier
- **Netlify/Vercel:** Free tier
- **Render:** Free tier (sleeps after 15min)
- **Total:** $0/month

### Production (Low Traffic)

- **Supabase:** Free tier or $25/month
- **Railway/Render:** $10-20/month
- **Netlify/Vercel:** Free tier
- **Total:** $10-45/month

### Production (Medium Traffic)

- **Supabase:** $25/month
- **Backend:** $30-50/month
- **Frontend:** Free
- **Total:** $55-75/month

---

## Troubleshooting

### Frontend Issues

**"Failed to fetch":**
- [ ] Check `VITE_API_URL` is correct
- [ ] Verify backend is running
- [ ] Check CORS settings
- [ ] Test health endpoint manually

**"Authentication failed":**
- [ ] Verify `VITE_API_KEY` matches backend
- [ ] Check API key format: `tenant_keystring`
- [ ] Ensure backend has `API_KEYS` env var

### Backend Issues

**"Database connection failed":**
- [ ] Verify `DATABASE_URL` format
- [ ] Check Supabase project is active
- [ ] Test connection from local machine
- [ ] Review Supabase logs

**"Storage operation failed":**
- [ ] Check `SUPABASE_SERVICE_ROLE_KEY` (not anon key!)
- [ ] Verify storage buckets exist
- [ ] Check RLS policies
- [ ] Review storage logs

**"Workers not processing":**
- [ ] Verify orchestrator is running
- [ ] Check worker logs for errors
- [ ] Ensure job was enqueued: `/jobs/{id}/enqueue`
- [ ] Check queue status in database

---

## Next Steps

After deployment:

1. **Share with team**
   - [ ] Send API keys
   - [ ] Share frontend URL
   - [ ] Document workflow

2. **Monitor for 24 hours**
   - [ ] Check logs regularly
   - [ ] Watch for errors
   - [ ] Verify processing works

3. **Optimize**
   - [ ] Disable upscaling if slow: `UPSCALE_ENABLED=false`
   - [ ] Adjust worker count based on load
   - [ ] Fine-tune AI provider settings

4. **Scale**
   - [ ] Add workers as needed
   - [ ] Upgrade Supabase plan if needed
   - [ ] Consider caching layer

---

## Support Resources

- **Documentation:** All markdown files in repo
- **Supabase Docs:** [supabase.com/docs](https://supabase.com/docs)
- **Railway Docs:** [docs.railway.app](https://docs.railway.app)
- **Render Docs:** [render.com/docs](https://render.com/docs)

---

## Success Criteria

You've successfully deployed OPAL when:

- ✅ Frontend loads at your URL
- ✅ Backend health check returns OK
- ✅ Can upload images through frontend
- ✅ Jobs process and complete
- ✅ Can view results in gallery
- ✅ All three tabs work (Upload, Monitor, Results, Debug)
- ✅ No errors in logs
- ✅ Performance is acceptable

---

**Deployment Date:** _______________

**Deployed By:** _______________

**Frontend URL:** _______________

**Backend URL:** _______________

**Notes:**
```
_________________________________________________________________
_________________________________________________________________
_________________________________________________________________
```

---

**🎉 Congratulations! Your OPAL platform is live!**

For questions or issues, check the documentation or open an issue on GitHub.
