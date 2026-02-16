# OPAL Platform Testing Guide

## Current Status

✅ **Backend**: Running locally on port 8080
✅ **Frontend**: Built and deployed
✅ **Database**: Connected to Supabase
✅ **Storage**: Connected to Supabase

## Test Options

### Option 1: Local Development (Recommended)

Run both frontend and backend locally for full functionality:

**Terminal 1 - Start Backend:**
```bash
cd /tmp/cc-agent/63778139/project
PYTHONPATH="$PWD/src/shared:$PWD/src/web_api:$PYTHONPATH" \
DATABASE_URL="" \
SUPABASE_URL="https://jbwbdfabuffiwdphzzon.supabase.co" \
SUPABASE_ANON_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
STORAGE_BACKEND="supabase" \
QUEUE_BACKEND="database" \
API_KEYS="dev_testkey123" \
python3 -m uvicorn web_api.main:app \
  --app-dir src/web_api \
  --host 0.0.0.0 \
  --port 8080
```

**Terminal 2 - Start Frontend:**
```bash
cd /tmp/cc-agent/63778139/project/frontend
npm run dev
```

Then open: `http://localhost:5173`

The Vite dev server will proxy API requests to the backend automatically.

### Option 2: Direct API Testing

Test the backend API directly using curl or the test page:

**Health Check:**
```bash
curl http://localhost:8080/healthz
```

**Debug Info:**
```bash
curl http://localhost:8080/debug/info
```

**Create Job:**
```bash
curl -X POST http://localhost:8080/v1/jobs \
  -H "X-API-Key: dev_testkey123" \
  -H "Content-Type: application/json" \
  -d '{"items": [{"filename": "test.jpg"}]}'
```

**Get Job Status:**
```bash
curl http://localhost:8080/v1/jobs/JOB_ID_HERE \
  -H "X-API-Key: dev_testkey123"
```

### Option 3: Test Page

Open the diagnostic test page (if backend is running):
```
http://localhost:5173/test.html
```

This page will:
- Show connection diagnostics
- Test all API endpoints
- Display detailed error messages
- Test different URL configurations

## What Can Be Tested

### 1. **Image Upload Flow**
- Drag and drop images
- Click to browse and select
- Multiple file selection
- File type validation (JPG, PNG, WebP)

### 2. **Job Creation**
- API creates job records in database
- Each file gets a unique item ID
- Correlation ID for batch tracking

### 3. **File Upload**
- Direct upload to Supabase Storage
- Files stored in `product-images` bucket
- Organized by job_id and item_id

### 4. **Job Monitoring**
- Poll job status endpoint
- Track processing stages
- Display progress indicators

### 5. **Database Operations**
- Job records in `jobs` table
- Item records in `job_items` table
- Queue records in `job_queue` table
- RLS policies enforced

### 6. **Error Handling**
- API key validation
- File size limits
- Invalid file types
- Network errors
- Backend unavailable

## Known Limitations

### Hosted Environment

The hosted preview at `https://code-418dotcom-opal-p5oc.bolt.host` has limitations:

❌ **Backend not accessible**: The Netlify proxy configuration tries to connect to `localhost:8080`, which doesn't exist in the hosted environment.

**Why**: In production/hosted environments, the backend needs to be:
- Deployed separately (e.g., Azure Container Apps, AWS ECS, fly.io)
- Accessible via public URL
- CORS configured for the frontend domain

**Solution**: Use Option 1 (Local Development) for full testing.

### Missing AI Processing

The following services are stubs and won't actually process images:
- Background removal (needs rembg or external API)
- Image generation (needs Stable Diffusion endpoint)
- Upscaling (needs Real-ESRGAN or external API)

These will need to be implemented or connected to external services.

## Database Inspection

Check jobs created in Supabase:

```bash
# List recent jobs
curl -s http://localhost:8080/v1/jobs | jq
```

Or query directly in Supabase Dashboard:
```sql
SELECT id, status, created_at
FROM jobs
ORDER BY created_at DESC
LIMIT 10;
```

## Troubleshooting

### Backend Won't Start

**Check Python modules:**
```bash
python3 -c "import fastapi, uvicorn, supabase; print('All modules OK')"
```

**Install if missing:**
```bash
pip install --break-system-packages uvicorn fastapi python-multipart supabase pydantic-settings
```

### Frontend Can't Connect

**Check backend is running:**
```bash
curl http://localhost:8080/healthz
```

**Check browser console for:**
```
[API Client] Configuration: { apiUrl: '...', ... }
```

### CORS Errors

Backend should return these headers:
```
Access-Control-Allow-Origin: *
Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS
Access-Control-Allow-Headers: content-type, x-api-key
```

Check with:
```bash
curl -v -X OPTIONS http://localhost:8080/v1/jobs
```

## Next Steps

### For Production Deployment:

1. **Deploy Backend**
   - Containerize with Docker
   - Deploy to cloud provider
   - Set environment variables
   - Configure health checks

2. **Update Frontend**
   - Set `VITE_API_URL` to backend URL
   - Set `VITE_API_KEY` for authentication
   - Update CORS allowed origins

3. **Implement AI Services**
   - Connect to background removal API
   - Set up Stable Diffusion endpoint
   - Add upscaling service

4. **Add Worker**
   - Deploy orchestrator worker
   - Process job queue
   - Update job statuses

5. **Enable Authentication**
   - Implement Supabase Auth
   - Protect API endpoints
   - Add user management

## Current Test Results

### Backend Status
```json
{
  "status": "ok",
  "db": "ok",
  "storage": "ok",
  "api_keys_configured": true,
  "storage_backend": "supabase",
  "queue_backend": "database"
}
```

### Jobs Created
8 test jobs successfully created in database
All in `created` status awaiting processing

### Storage
Supabase bucket `product-images` accessible
RLS policies configured for secure access

---

**Last Updated**: 2026-02-16
**Version**: 0.2.1
