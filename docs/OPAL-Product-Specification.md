# OPAL - Complete Product Specification

## Product Overview

OPAL is an AI-powered product photography platform that transforms plain product photos into professional lifestyle marketing images.

**Core Value:** Turn `[product.jpg]` into `[product-in-beautiful-scene.jpg]` in under 60 seconds for $0.03.

---

## Feature Set

### 1. AI Product Photography Pipeline

**User Experience:**
- User uploads product photo (white background, PNG/JPG)
- System automatically:
  - Removes background
  - Generates photorealistic lifestyle scene
  - Places product in scene
  - Upscales to high resolution
- User downloads professional marketing image

**Backend Implementation:**

**Services:**
- `orchestrator` - Executes 5-step pipeline

**Pipeline Steps:**
```
1. Download from blob storage
2. Background removal (rembg AI model, local)
3. Scene generation (FAL.AI FLUX.1 API)
4. Composite product onto scene (PIL)
5. Upscale 2x (Real-ESRGAN AI model, local)
```

**Technology Stack:**
- **rembg:** U²-Net segmentation model (PyTorch)
- **FAL.AI:** FLUX.1 schnell text-to-image API
- **PIL:** Python Imaging Library for compositing
- **Real-ESRGAN:** Super-resolution upscaling (PyTorch)

**APIs:**
```
POST /v1/jobs
  Body: { tenant_id, brand_profile_id, items: [{ filename }] }
  Returns: { job_id, items: [{ item_id }] }

POST /v1/uploads/sas
  Body: { tenant_id, job_id, item_id, filename }
  Returns: { upload_url }

PUT <upload_url>
  Body: <image bytes>
  Headers: { x-ms-blob-type: BlockBlob }

POST /v1/jobs/{job_id}/process
  Queues job for AI processing

GET /v1/jobs/{job_id}
  Returns: { status, items: [{ status, output_url }] }
```

**Database:**
```sql
CREATE TABLE jobs (
    id VARCHAR PRIMARY KEY,
    tenant_id VARCHAR,
    brand_profile_id VARCHAR,
    status VARCHAR,  -- created, processing, completed, failed
    created_at TIMESTAMP
);

CREATE TABLE job_items (
    id VARCHAR PRIMARY KEY,
    job_id VARCHAR REFERENCES jobs(id),
    filename VARCHAR,
    status VARCHAR,  -- created, uploaded, processing, completed, failed
    raw_blob_path VARCHAR,
    output_blob_path VARCHAR,
    error_message TEXT
);
```

**Blob Storage:**
- Container: `raw` - Input images
- Container: `outputs` - Processed images
- Security: SAS tokens with time-limited access

**Message Queue:**
- Azure Service Bus queue: `jobs`
- Message: `{ tenant_id, job_id, item_id, correlation_id }`

---

### 2. Brand Profiles

**User Experience:**
- User creates brand profile with:
  - Brand name
  - Default scene style (e.g., "minimalist modern", "rustic farmhouse")
  - Color preferences
  - Mood keywords
- All images for that brand automatically use these settings
- No need to specify scene on every upload

**Backend Implementation:**

**Database:**
```sql
CREATE TABLE brand_profiles (
    id VARCHAR PRIMARY KEY,
    tenant_id VARCHAR,
    name VARCHAR,
    default_scene_prompt TEXT,
    style_keywords VARCHAR[],
    color_palette VARCHAR[],
    mood VARCHAR,  -- modern, rustic, luxe, playful, etc.
    created_at TIMESTAMP
);

-- Example row:
{
  id: "brand_abc123",
  tenant_id: "tenant_xyz",
  name: "Acme Home Goods",
  default_scene_prompt: "modern minimalist living room, bright natural lighting, scandinavian design",
  style_keywords: ["minimal", "clean", "bright"],
  color_palette: ["#FFFFFF", "#F5F5F5", "#E0E0E0"],
  mood: "modern"
}
```

**API Updates:**
```
POST /v1/brand-profiles
  Body: { tenant_id, name, default_scene_prompt, style_keywords, color_palette, mood }
  Returns: { brand_profile_id }

GET /v1/brand-profiles
  Query: tenant_id
  Returns: [{ brand_profile_id, name, ... }]

PUT /v1/brand-profiles/{id}
  Body: { default_scene_prompt, style_keywords, ... }

DELETE /v1/brand-profiles/{id}
```

**Orchestrator Changes:**
- When processing item, load brand profile
- Use `default_scene_prompt` for image generation
- Append `style_keywords` to prompt
- Pass to FAL.AI: `{prompt}, {style_keywords}, {mood}`

---

### 3. Multi-Scene Generation

**User Experience:**
- User uploads one product
- System generates 5 different lifestyle scenes
- Examples:
  - Living room
  - Bedroom
  - Kitchen
  - Outdoor patio
  - Office
- User picks best one or uses all for A/B testing

**Backend Implementation:**

**Database Schema Change:**
```sql
-- Add scene_index to job_items
ALTER TABLE job_items ADD COLUMN scene_index INTEGER;
ALTER TABLE job_items ADD COLUMN scene_type VARCHAR;

-- One job_item per scene
-- job_abc123 → 5 items (same product, different scenes)
```

**API:**
```
POST /v1/jobs
  Body: { 
    tenant_id, 
    brand_profile_id,
    items: [{ 
      filename,
      scene_count: 5,  -- NEW
      scene_types: ["living_room", "bedroom", "kitchen", "patio", "office"]  -- OPTIONAL
    }]
  }
  
  -- Creates 1 job with 5 items (one per scene)
```

**Orchestrator Changes:**
- On job creation, if `scene_count > 1`:
  - Create N job_items (one per scene)
  - All reference same `raw_blob_path`
  - Each has different `scene_type`
- When processing:
  - Load scene-specific prompt
  - Generate different scene for each item
  - All composite same product

**Scene Prompts:**
```python
SCENE_PROMPTS = {
    "living_room": "modern living room, bright natural lighting, sofa, plants",
    "bedroom": "cozy bedroom, soft lighting, bed, minimalist decor",
    "kitchen": "clean modern kitchen, marble countertop, appliances",
    "patio": "outdoor patio, sunset, garden furniture, plants",
    "office": "home office, desk, bookshelf, natural light"
}
```

---

### 4. Custom Scene Prompts

**User Experience:**
- User can override default brand scene
- Specify exact scene per upload: "product on beach at sunset"
- Full creative control when needed

**Backend Implementation:**

**API:**
```
POST /v1/jobs
  Body: { 
    items: [{ 
      filename,
      scene_prompt: "luxury yacht deck, ocean view, golden hour"  -- OPTIONAL OVERRIDE
    }]
  }
```

**Orchestrator Logic:**
```python
# Priority order:
1. If item has custom scene_prompt → use it
2. Else if brand has default_scene_prompt → use it
3. Else use system default
```

---

### 5. Batch Upload

**User Experience:**
- User uploads CSV with product URLs and metadata
- System downloads and processes all products
- Progress tracking in dashboard
- Bulk download when complete

**Backend Implementation:**

**Database:**
```sql
CREATE TABLE batch_jobs (
    id VARCHAR PRIMARY KEY,
    tenant_id VARCHAR,
    brand_profile_id VARCHAR,
    status VARCHAR,  -- uploading, processing, completed
    total_items INTEGER,
    completed_items INTEGER,
    failed_items INTEGER,
    created_at TIMESTAMP
);

CREATE TABLE batch_items (
    id VARCHAR PRIMARY KEY,
    batch_job_id VARCHAR REFERENCES batch_jobs(id),
    source_url VARCHAR,  -- URL to download product image
    filename VARCHAR,
    status VARCHAR,
    job_item_id VARCHAR REFERENCES job_items(id)
);
```

**API:**
```
POST /v1/batch-jobs
  Body: { 
    tenant_id,
    brand_profile_id,
    items: [
      { source_url: "https://cdn.com/product1.jpg", filename: "product1.jpg" },
      { source_url: "https://cdn.com/product2.jpg", filename: "product2.jpg" },
      ...
    ]
  }
  Returns: { batch_job_id }

GET /v1/batch-jobs/{id}
  Returns: { 
    status, 
    total_items, 
    completed_items,
    failed_items,
    items: [{ filename, status, output_url }]
  }
```

**New Service: `batch-processor`**
- Listens to `batch-jobs` queue
- Downloads images from source URLs
- Creates individual jobs for each
- Tracks overall progress
- Sends completion notification

---

### 6. Output Delivery

**User Experience:**
- Auto-upload to Shopify product images
- Email ZIP of all processed images
- Webhook notification when job completes
- Google Drive sync

**Backend Implementation:**

**Database:**
```sql
CREATE TABLE delivery_configs (
    id VARCHAR PRIMARY KEY,
    tenant_id VARCHAR,
    type VARCHAR,  -- shopify, email, webhook, gdrive
    config JSONB,
    enabled BOOLEAN
);

-- Example Shopify config:
{
  type: "shopify",
  config: {
    shop_url: "acme-store.myshopify.com",
    api_key: "...",
    auto_upload: true,
    replace_existing: false
  }
}

-- Example webhook config:
{
  type: "webhook",
  config: {
    url: "https://customer.com/webhook",
    method: "POST",
    headers: { "Authorization": "Bearer ..." }
  }
}
```

**API:**
```
POST /v1/delivery-configs
  Body: { tenant_id, type, config }

GET /v1/delivery-configs
  Query: tenant_id
  Returns: [{ id, type, enabled }]

PUT /v1/delivery-configs/{id}
  Body: { enabled, config }
```

**Service: `export-worker`**
- Listens to `exports` queue
- Message: `{ tenant_id, job_id, item_id }`
- Loads delivery configs for tenant
- Executes deliveries:

**Shopify Integration:**
```python
def deliver_to_shopify(item, config):
    # 1. Get output image from blob storage
    image_bytes = download_blob(item.output_blob_path)
    
    # 2. Upload to Shopify via Admin API
    shopify.Product.image.create({
        'product_id': item.metadata['product_id'],
        'attachment': base64.encode(image_bytes)
    })
```

**Email Integration:**
```python
def deliver_via_email(job, config):
    # 1. Get all output images for job
    items = job.items
    
    # 2. Create ZIP
    zip_buffer = create_zip([item.output_blob_path for item in items])
    
    # 3. Send via SendGrid
    sendgrid.send_email(
        to=config['email'],
        subject=f"OPAL Job {job.id} Complete",
        attachments=[('images.zip', zip_buffer)]
    )
```

**Webhook Integration:**
```python
def deliver_via_webhook(item, config):
    # POST to customer webhook
    requests.post(
        config['url'],
        json={
            'job_id': item.job_id,
            'item_id': item.id,
            'output_url': generate_download_url(item.output_blob_path),
            'status': 'completed'
        },
        headers=config['headers']
    )
```

---

### 7. Usage Tracking & Billing

**User Experience:**
- Dashboard shows:
  - Images processed this month
  - Cost per image
  - Total spend
  - Credits remaining
- Auto-charge via Stripe when credits run low
- Usage alerts

**Backend Implementation:**

**Database:**
```sql
CREATE TABLE tenants (
    id VARCHAR PRIMARY KEY,
    name VARCHAR,
    email VARCHAR,
    stripe_customer_id VARCHAR,
    plan VARCHAR,  -- free, pro, enterprise
    credits_remaining INTEGER,
    created_at TIMESTAMP
);

CREATE TABLE usage_events (
    id VARCHAR PRIMARY KEY,
    tenant_id VARCHAR,
    job_id VARCHAR,
    item_id VARCHAR,
    event_type VARCHAR,  -- api_call, compute_seconds
    cost_usd DECIMAL(10,4),
    metadata JSONB,
    created_at TIMESTAMP
);

CREATE TABLE invoices (
    id VARCHAR PRIMARY KEY,
    tenant_id VARCHAR,
    period_start DATE,
    period_end DATE,
    total_images INTEGER,
    total_cost_usd DECIMAL(10,2),
    stripe_invoice_id VARCHAR,
    status VARCHAR,  -- draft, paid, failed
    created_at TIMESTAMP
);
```

**Service: `billing-service`**
- Listens to `billing-events` queue
- Tracks usage events:

```python
# When FAL.AI call completes
emit_billing_event({
    'tenant_id': 'tenant_xyz',
    'job_id': 'job_abc',
    'item_id': 'item_123',
    'event_type': 'fal_api_call',
    'cost_usd': 0.025
})

# When Real-ESRGAN upscales (free but track compute time)
emit_billing_event({
    'tenant_id': 'tenant_xyz',
    'job_id': 'job_abc',
    'item_id': 'item_123',
    'event_type': 'compute_seconds',
    'cost_usd': 0.0,
    'metadata': { 'seconds': 42, 'cpu_cores': 2 }
})
```

**Billing Logic:**
```python
# Monthly aggregation
def generate_monthly_invoice(tenant_id, month):
    events = get_usage_events(tenant_id, month)
    
    total_images = count(events, event_type='job_completed')
    total_cost = sum(events, 'cost_usd')
    
    # Create Stripe invoice
    stripe.Invoice.create(
        customer=tenant.stripe_customer_id,
        amount=total_cost * 100,  # cents
        description=f"{total_images} images processed"
    )
```

**API:**
```
GET /v1/billing/usage
  Query: tenant_id, start_date, end_date
  Returns: {
    total_images: 1250,
    total_cost_usd: 31.25,
    breakdown: [
      { date: "2024-01-01", images: 50, cost: 1.25 },
      ...
    ]
  }

GET /v1/billing/invoices
  Query: tenant_id
  Returns: [{ invoice_id, period, total_cost, status }]

POST /v1/billing/credits
  Body: { tenant_id, amount_usd }
  Action: Top up credits via Stripe
```

---

### 8. Analytics & A/B Testing

**User Experience:**
- Dashboard shows which scenes perform best
- Click tracking on generated images
- Conversion metrics per scene type
- Recommendation: "Living room scenes convert 32% better for your products"

**Backend Implementation:**

**Database:**
```sql
CREATE TABLE image_events (
    id VARCHAR PRIMARY KEY,
    tenant_id VARCHAR,
    job_id VARCHAR,
    item_id VARCHAR,
    event_type VARCHAR,  -- view, click, add_to_cart, purchase
    session_id VARCHAR,
    user_agent VARCHAR,
    referrer VARCHAR,
    metadata JSONB,
    created_at TIMESTAMP
);

CREATE TABLE scene_performance (
    tenant_id VARCHAR,
    scene_type VARCHAR,
    total_views INTEGER,
    total_clicks INTEGER,
    total_conversions INTEGER,
    ctr DECIMAL(5,2),  -- click-through rate
    cvr DECIMAL(5,2),  -- conversion rate
    updated_at TIMESTAMP,
    PRIMARY KEY (tenant_id, scene_type)
);
```

**Tracking Pixel:**
```html
<!-- Embed in customer's website -->
<img src="https://opal.ai/pixel?item_id=item_123&event=view" width="1" height="1" />

<!-- Click tracking -->
<a href="product.html" 
   onclick="fetch('https://opal.ai/track?item_id=item_123&event=click')">
   <img src="generated-image.jpg" />
</a>
```

**API:**
```
POST /v1/track
  Body: { item_id, event_type, session_id, metadata }
  
GET /pixel
  Query: item_id, event
  Returns: 1x1 transparent GIF

GET /v1/analytics/performance
  Query: tenant_id, start_date, end_date
  Returns: {
    overall: { views: 10000, clicks: 320, cvr: 3.2 },
    by_scene: [
      { scene_type: "living_room", views: 3000, clicks: 120, cvr: 4.0 },
      { scene_type: "bedroom", views: 2500, clicks: 60, cvr: 2.4 },
      ...
    ]
  }
```

**Service: `analytics-worker`**
- Listens to `tracking-events` queue
- Aggregates events into `scene_performance` table
- Runs nightly to compute metrics

---

### 9. API Rate Limiting & Quotas

**User Experience:**
- Free tier: 10 images/month
- Pro tier: 500 images/month
- Enterprise: Unlimited
- Clear error messages when quota exceeded

**Backend Implementation:**

**Database:**
```sql
ALTER TABLE tenants ADD COLUMN monthly_quota INTEGER;
ALTER TABLE tenants ADD COLUMN images_this_month INTEGER;
ALTER TABLE tenants ADD COLUMN quota_reset_date DATE;
```

**Middleware:**
```python
@app.middleware("http")
async def check_quota(request, call_next):
    tenant_id = request.headers.get('X-Tenant-ID')
    tenant = get_tenant(tenant_id)
    
    if tenant.images_this_month >= tenant.monthly_quota:
        return JSONResponse(
            status_code=429,
            content={
                "error": "Monthly quota exceeded",
                "quota": tenant.monthly_quota,
                "used": tenant.images_this_month,
                "reset_date": tenant.quota_reset_date
            }
        )
    
    response = await call_next(request)
    return response
```

**API:**
```
GET /v1/quota
  Query: tenant_id
  Returns: {
    quota: 500,
    used: 342,
    remaining: 158,
    reset_date: "2024-02-01"
  }
```

---

### 10. Admin Dashboard (Future)

**User Experience:**
- Web UI for managing brand profiles
- Upload interface (drag & drop)
- Job history with previews
- Usage charts
- Settings management

**Backend Implementation:**

**Tech Stack:**
- React frontend (SPA)
- Hosted on Azure Static Web Apps
- Calls existing REST API
- Authentication via Azure AD B2C or Auth0

**Pages:**
- `/dashboard` - Overview, recent jobs, usage
- `/brands` - Manage brand profiles
- `/upload` - New job creation
- `/jobs` - Job history
- `/settings` - Delivery configs, API keys
- `/billing` - Invoices, usage, credits

---

## Infrastructure Requirements

### Services

**web-api** (FastAPI)
- Handle all REST API requests
- Validate inputs
- Manage jobs/items in database
- Generate SAS tokens
- Send messages to queues

**orchestrator** (Python)
- Execute 5-step AI pipeline
- Process messages from `jobs` queue
- Update job/item status
- Upload outputs to blob storage

**export-worker** (Python)
- Process messages from `exports` queue
- Deliver outputs via Shopify, email, webhooks, etc.

**batch-processor** (Python)
- Process messages from `batch-jobs` queue
- Download images from URLs
- Create individual jobs

**billing-service** (Python)
- Process messages from `billing-events` queue
- Track usage
- Generate invoices via Stripe

**analytics-worker** (Python)
- Process messages from `tracking-events` queue
- Aggregate performance metrics
- Update `scene_performance` table

### Message Queues

- `jobs` - Job processing requests
- `exports` - Delivery requests
- `batch-jobs` - Batch upload requests
- `billing-events` - Usage tracking
- `tracking-events` - Analytics events

### Blob Storage

- `raw` - Input images
- `outputs` - Processed images
- Retention: 30 days (configurable per tenant)

### Database (PostgreSQL)

**Core Tables:**
- `tenants`
- `jobs`
- `job_items`
- `brand_profiles`
- `batch_jobs`
- `batch_items`
- `delivery_configs`
- `usage_events`
- `invoices`
- `image_events`
- `scene_performance`

### Third-Party APIs

**Required:**
- **FAL.AI** - Scene generation (FLUX.1)
- **Stripe** - Payments
- **SendGrid** - Email delivery

**Optional:**
- **Shopify Admin API** - Product image upload
- **Google Drive API** - File sync
- **Replicate** - Alternative AI provider
- **remove.bg** - Alternative background removal

### Compute Requirements

**orchestrator:**
- CPU: 2-4 cores (for Real-ESRGAN)
- RAM: 4-8 GB (model loading)
- GPU: Optional (speeds up upscaling 10x)

**Other services:**
- CPU: 0.5-1 core
- RAM: 1 GB

### Scaling Strategy

**0-100 jobs/day:**
- 1 orchestrator instance
- Use Real-ESRGAN (local, CPU)

**100-1K jobs/day:**
- 2-5 orchestrator instances
- Consider GPU for Real-ESRGAN

**1K-10K jobs/day:**
- 5-10 orchestrator instances
- Switch to FAL.AI upscaling API (faster, GPU)
- Just change env var: `UPSCALE_PROVIDER=fal`

**10K+ jobs/day:**
- 10+ orchestrator instances
- All AI via APIs (FAL.AI upscaling)
- Consider dedicated GPU instances

---

## API Summary

### Core Jobs API
```
POST   /v1/jobs                              Create job
GET    /v1/jobs/{job_id}                     Get job status
POST   /v1/jobs/{job_id}/process             Queue for processing
DELETE /v1/jobs/{job_id}                     Cancel job

POST   /v1/uploads/sas                       Get upload URL
POST   /v1/uploads/complete                  Mark upload complete

GET    /v1/jobs/{job_id}/items/{item_id}/download-sas   Get output URL
```

### Brand Profiles API
```
POST   /v1/brand-profiles                    Create brand profile
GET    /v1/brand-profiles                    List brand profiles
GET    /v1/brand-profiles/{id}               Get brand profile
PUT    /v1/brand-profiles/{id}               Update brand profile
DELETE /v1/brand-profiles/{id}               Delete brand profile
```

### Batch Processing API
```
POST   /v1/batch-jobs                        Create batch job
GET    /v1/batch-jobs/{id}                   Get batch job status
POST   /v1/batch-jobs/{id}/cancel            Cancel batch job
```

### Delivery API
```
POST   /v1/delivery-configs                  Create delivery config
GET    /v1/delivery-configs                  List delivery configs
PUT    /v1/delivery-configs/{id}             Update delivery config
DELETE /v1/delivery-configs/{id}             Delete delivery config
```

### Billing API
```
GET    /v1/billing/usage                     Get usage stats
GET    /v1/billing/invoices                  List invoices
POST   /v1/billing/credits                   Purchase credits
GET    /v1/quota                             Check quota
```

### Analytics API
```
POST   /v1/track                             Track event
GET    /pixel                                Tracking pixel
GET    /v1/analytics/performance             Get performance metrics
```

### Admin API
```
GET    /v1/tenants                           List tenants (admin)
POST   /v1/tenants                           Create tenant (admin)
PUT    /v1/tenants/{id}/quota                Update quota (admin)
```

---

## Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:pass@host:5432/opal

# Azure
AZURE_STORAGE_CONNECTION_STRING=...
AZURE_SERVICEBUS_CONNECTION_STRING=...

# AI Providers
FAL_API_KEY=...
REMOVEBG_API_KEY=...  # optional
REPLICATE_API_TOKEN=...  # optional

# Provider Selection
BACKGROUND_REMOVAL_PROVIDER=rembg  # or remove.bg
IMAGE_GEN_PROVIDER=fal  # or replicate
UPSCALE_PROVIDER=realesrgan  # or fal
UPSCALE_ENABLED=true

# Billing
STRIPE_SECRET_KEY=...
STRIPE_WEBHOOK_SECRET=...

# Delivery
SENDGRID_API_KEY=...
SHOPIFY_API_KEY=...  # optional
SHOPIFY_API_SECRET=...  # optional

# Monitoring
LOG_LEVEL=INFO
SENTRY_DSN=...  # optional
```

---

## Complete Feature List

1. ✅ AI Product Photography Pipeline (5 steps)
2. ✅ Pluggable AI Providers (swap services via config)
3. ✅ Secure Upload/Download (SAS tokens)
4. ⬜ Brand Profiles (customizable scene styles)
5. ⬜ Multi-Scene Generation (5 scenes per product)
6. ⬜ Custom Scene Prompts (override defaults)
7. ⬜ Batch Upload (CSV with URLs)
8. ⬜ Shopify Integration (auto-upload product images)
9. ⬜ Email Delivery (ZIP of outputs)
10. ⬜ Webhook Notifications (job completion)
11. ⬜ Google Drive Sync (auto-upload)
12. ⬜ Usage Tracking & Billing (Stripe integration)
13. ⬜ Analytics & A/B Testing (scene performance)
14. ⬜ API Rate Limiting (quota enforcement)
15. ⬜ Admin Dashboard (web UI)

---

This document describes OPAL's complete feature set and technical implementation. All backend services, APIs, database schemas, and integrations needed to build the full product.
