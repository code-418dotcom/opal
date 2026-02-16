# OPAL Edge Functions - Deployment Complete

## What Was Fixed

The API has been fully converted to Supabase Edge Functions. All endpoints are now serverless and ready to use.

### Issues Resolved
1. **JWT Verification**: Edge Functions were incorrectly configured to require JWT tokens. Changed to API key authentication.
2. **Test Page**: Updated `/test` page to use correct Supabase Edge Function URLs
3. **Upload Errors**: Fixed 404 errors by ensuring all functions use proper authentication headers

## Available Edge Functions

All functions are deployed and active at: `https://jbwbdfabuffiwdphzzon.supabase.co/functions/v1/`

### 1. create-job
**Endpoint:** `POST /functions/v1/create-job`
**Purpose:** Creates a new image processing job
**Headers:** `X-API-Key: dev_testkey123`

```json
{
  "items": [
    { "filename": "image1.jpg" },
    { "filename": "image2.jpg" }
  ]
}
```

### 2. upload-file
**Endpoint:** `POST /functions/v1/upload-file`
**Purpose:** Uploads files to Supabase Storage
**Headers:** `X-API-Key: dev_testkey123`
**Body:** FormData with `file`, `job_id`, `item_id`

### 3. enqueue-job
**Endpoint:** `POST /functions/v1/enqueue-job/{job_id}`
**Purpose:** Queues job for processing
**Headers:** `X-API-Key: dev_testkey123`

### 4. get-job
**Endpoint:** `GET /functions/v1/get-job/{job_id}`
**Purpose:** Retrieves job status and results
**Headers:** `X-API-Key: dev_testkey123`

### 5. get-download-url
**Endpoint:** `GET /functions/v1/get-download-url?item_id={id}&bucket=outputs`
**Purpose:** Generates signed download URL
**Headers:** `X-API-Key: dev_testkey123`

### 6. process-job-worker
**Endpoint:** `POST /functions/v1/process-job-worker`
**Purpose:** Processes queued jobs (background removal, compositing)
**Trigger:** Automatically called after enqueue-job

## Testing the API

### Option 1: Use the Test Page
Visit: `/test` in your browser

The test page now correctly targets Supabase Edge Functions and includes:
- Health check (CORS verification)
- Environment diagnostics
- Job creation test
- Endpoint availability checks

### Option 2: Use the Main Application
1. Visit the home page
2. Select files to upload
3. Click "Create Job" to start processing
4. Monitor tab shows real-time progress
5. Results tab displays completed images

### Option 3: cURL Examples

Create a job:
```bash
curl -X POST https://jbwbdfabuffiwdphzzon.supabase.co/functions/v1/create-job \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev_testkey123" \
  -d '{"items": [{"filename": "test.jpg"}]}'
```

Get job status:
```bash
curl https://jbwbdfabuffiwdphzzon.supabase.co/functions/v1/get-job/job_xxx \
  -H "X-API-Key: dev_testkey123"
```

## How It Works

### Job Processing Flow

1. **Frontend creates job** → `create-job` function
   - Creates job and items in database
   - Returns job_id and item IDs

2. **User uploads images** → `upload-file` function
   - Uploads to Supabase Storage (raw bucket)
   - Updates item status to "uploaded"

3. **Job gets queued** → `enqueue-job` function
   - Adds messages to job_queue table
   - Automatically triggers worker

4. **Worker processes** → `process-job-worker` function
   - Fetches messages from queue
   - Downloads input from storage
   - Processes image (currently pass-through mode)
   - Uploads output to storage
   - Updates job status

5. **Results retrieved** → `get-job` and `get-download-url`
   - Frontend polls for status
   - Downloads completed images

### Queue Processing

The worker function uses a database-backed queue:
- Messages stored in `job_queue` table
- Atomic locking with `FOR UPDATE SKIP LOCKED`
- Automatic retry on failure (max 3 attempts)
- Failed messages marked as "failed" in database

### Storage Buckets

Three Supabase Storage buckets:
- **raw**: Input files from users
- **outputs**: Processed images
- **exports**: Batch export files (future)

## Configuration

### Environment Variables

Already configured in `.env`:
```
SUPABASE_URL=https://jbwbdfabuffiwdphzzon.supabase.co
SUPABASE_ANON_KEY=eyJhbGc...
API_KEYS=dev_testkey123
```

### Frontend Configuration

The frontend automatically uses Supabase Edge Functions:
- API URL: `${SUPABASE_URL}/functions/v1`
- Authentication: X-API-Key header
- Worker trigger: Automatic after enqueue

## Migration Path to Azure

When ready to move to Azure, the transition is straightforward:

### Keep Using
- Database schema (works with Azure PostgreSQL)
- Python processing code in `/src/`
- Queue logic (adapt to Azure Service Bus)

### Replace
- Edge Functions → Azure Container Apps
- Supabase Storage → Azure Blob Storage
- Database queue → Azure Service Bus

### No Changes Needed
- Frontend (just update API_URL)
- Image processing pipeline
- Job/item data model

## Current Limitations

### Worker Processing
Currently in **pass-through mode**:
- Input image is copied to output unchanged
- No AI processing (background removal, generation, upscaling)
- This is because Edge Functions don't support heavy ML workloads

### To Enable Full Processing
You have two options:

**Option A: Keep Edge Functions (Limited)**
- Use external APIs (remove.bg, Replicate, etc.)
- Add API calls in `process-job-worker`
- Limited by Edge Function timeout (150s)

**Option B: Move to Azure (Recommended)**
- Deploy Python workers from `/src/` as Container Apps
- Full access to ML libraries (rembg, torch, etc.)
- No timeout limits
- Scalable processing

## What's Working Now

✅ Job creation
✅ File upload to Supabase Storage
✅ Queue management
✅ Worker processing (pass-through mode)
✅ Status polling
✅ Download URLs
✅ Database migrations
✅ RLS policies
✅ API key authentication

## Next Steps

1. **Test the system** using the test page or main UI
2. **Monitor the database** to see jobs and queue messages
3. **Add AI processing** when you're ready to integrate ML APIs
4. **Deploy to production** when satisfied with the setup
5. **Migrate to Azure** when you need full processing capabilities

---

**System Status:** ✅ All Edge Functions Active
**Build Status:** ✅ Frontend Built Successfully
**Ready for Testing:** ✅ Yes
