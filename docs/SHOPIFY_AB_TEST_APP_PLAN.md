# Shopify A/B Image Testing App — Implementation Plan

> Separate project that extends Opal's existing A/B testing backend with
> automatic storefront tracking via Shopify Theme App Extension + Web Pixels.

---

## Overview

**Goal**: Let Shopify merchants run automated A/B tests on product images —
swap variant A/B on the storefront, automatically track views, add-to-carts,
and conversions, compute statistical significance, and declare a winner.

**What exists in Opal today**:
- A/B test CRUD, start/swap/conclude/cancel routes
- Image swap via Shopify Admin API (`update_image` / `upload_image`)
- Z-test statistical significance computation
- Manual metrics entry (user types in daily stats)

**What this project adds**:
- Automatic metric collection via Web Pixels API (no manual entry)
- Theme App Extension for storefront JS injection
- Real-time conversion tracking through checkout
- Merchant-facing settings in Shopify theme editor

---

## Architecture

```
┌─────────────────────────────────────┐
│         Shopify Storefront          │
│                                     │
│  ┌──────────────┐  ┌─────────────┐ │
│  │ App Embed     │  │ Web Pixel   │ │
│  │ Block (head)  │  │ (sandbox)   │ │
│  │               │  │             │ │
│  │ • Injects     │  │ • Listens:  │ │
│  │   product     │  │  product_   │ │
│  │   metafield   │  │  viewed     │ │
│  │   data into   │  │  product_   │ │
│  │   page for    │  │  added_to_  │ │
│  │   pixel to    │  │  cart       │ │
│  │   read        │  │  checkout_  │ │
│  │               │  │  completed  │ │
│  └──────┬───────┘  └──────┬──────┘ │
│         │                  │        │
└─────────┼──────────────────┼────────┘
          │                  │
          │    ┌─────────────▼──────┐
          │    │  Opal Backend      │
          │    │                    │
          │    │  POST /v1/ab-tests │
          │    │  /events (batch)   │
          │    │                    │
          │    │  • Upsert metrics  │
          │    │  • Compute sig.    │
          │    │  • Auto-conclude   │
          │    └────────────────────┘
          │
     Metafields written
     via Admin API when
     test starts/swaps
```

**Key insight**: Web Pixels run in a sandboxed iframe with NO DOM access.
They can subscribe to standard events (`product_viewed`, `checkout_completed`)
and access `init.data` (cart contents, customer info at page load). They
CANNOT read the page DOM or know which image variant is displayed. So we use
**product metafields** to tell the pixel which test/variant is active for
each product.

---

## Phase 1: Shopify App Setup

### 1.1 Create Shopify App

```bash
# In a new project directory (NOT inside opal)
npm init @shopify/app@latest -- --template node
cd opal-shopify-ab
```

This scaffolds:
- `shopify.app.toml` — app config
- `extensions/` — where theme extension + pixel live
- `web/` — app backend (we'll point this to Opal's API)

### 1.2 App Scopes

Update `shopify.app.toml` scopes:

```toml
[access_scopes]
scopes = "read_products,write_products,read_pixels,write_pixels,read_metaobjects,write_metaobjects"
```

| Scope | Why |
|-------|-----|
| `read_products, write_products` | Already have — swap images |
| `read_pixels, write_pixels` | Register the web pixel for event tracking |
| `read_metaobjects, write_metaobjects` | Store active test/variant info on products |

> **Note**: We may need `read_product_listings` too if we want to track
> which products are visible on the storefront.

### 1.3 App Backend

The Shopify app backend is a thin proxy to Opal's API. Two options:

**Option A (recommended)**: App backend lives in Opal's web_api as new routes
under `/v1/shopify-app/`. The Shopify app's `web/` directory just serves the
embedded admin UI and proxies API calls to Opal.

**Option B**: Standalone Node.js backend in the Shopify app project that calls
Opal's API with an API key. More separation but more moving parts.

Recommendation: **Option A** — fewer services to deploy, reuses existing auth
and database.

---

## Phase 2: Web Pixel Extension

### 2.1 Create the Extension

```bash
shopify app generate extension --type web_pixel --name opal-ab-tracker
```

This creates `extensions/opal-ab-tracker/` with:
```
extensions/opal-ab-tracker/
├── shopify.extension.toml
└── src/
    └── index.ts        # Pixel code (runs in sandbox)
```

### 2.2 Pixel Configuration

`shopify.extension.toml`:
```toml
api_version = "2024-10"

[[extensions]]
type = "web_pixel_extension"
name = "Opal A/B Image Tracker"

[extensions.settings]
  [extensions.settings.fields.opal_api_url]
  name = "Opal API URL"
  type = "single_line_text_field"

  [extensions.settings.fields.opal_pixel_key]
  name = "Pixel API Key"
  type = "single_line_text_field"
```

### 2.3 Pixel Implementation

`src/index.ts`:

```typescript
import { register } from "@shopify/web-pixels-extension";

register(({ analytics, browser, init, settings }) => {
  const API_URL = settings.opal_api_url;
  const PIXEL_KEY = settings.opal_pixel_key;
  const SHOP_DOMAIN = init.context.document.location.host;

  // Buffer events and flush in batches (every 5s or 10 events)
  let eventBuffer: Array<{
    event_type: string;
    product_id: string;
    variant_id?: string;
    timestamp: string;
    session_id?: string;
  }> = [];

  function flushEvents() {
    if (eventBuffer.length === 0) return;
    const payload = [...eventBuffer];
    eventBuffer = [];

    fetch(`${API_URL}/v1/ab-tests/pixel-events`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Pixel-Key": PIXEL_KEY,
      },
      body: JSON.stringify({
        shop_domain: SHOP_DOMAIN,
        events: payload,
      }),
      keepalive: true, // survives page navigation
    }).catch(() => {
      // Re-queue on failure (best-effort)
      eventBuffer.push(...payload);
    });
  }

  // Flush every 5 seconds
  setInterval(flushEvents, 5000);

  // ── Product viewed ─────────────────────────────────
  analytics.subscribe("product_viewed", (event) => {
    const product = event.data?.productVariant?.product;
    if (!product?.id) return;
    eventBuffer.push({
      event_type: "view",
      product_id: extractGid(product.id),
      timestamp: new Date().toISOString(),
    });
  });

  // ── Add to cart ────────────────────────────────────
  analytics.subscribe("product_added_to_cart", (event) => {
    const item = event.data?.cartLine?.merchandise;
    if (!item?.product?.id) return;
    eventBuffer.push({
      event_type: "add_to_cart",
      product_id: extractGid(item.product.id),
      variant_id: extractGid(item.id),
      timestamp: new Date().toISOString(),
    });
  });

  // ── Checkout completed (conversion) ────────────────
  analytics.subscribe("checkout_completed", (event) => {
    const lineItems = event.data?.checkout?.lineItems || [];
    for (const item of lineItems) {
      if (!item.variant?.product?.id) continue;
      eventBuffer.push({
        event_type: "conversion",
        product_id: extractGid(item.variant.product.id),
        variant_id: extractGid(item.variant.id),
        timestamp: new Date().toISOString(),
      });
    }
    // Flush immediately on conversion (most valuable event)
    flushEvents();
  });

  // Extract numeric ID from Shopify GID
  // "gid://shopify/Product/123456" → "123456"
  function extractGid(gid: string): string {
    return gid.split("/").pop() || gid;
  }
});
```

### 2.4 What the Pixel Tracks

| Event | Shopify Event | Data Available | Maps To |
|-------|--------------|----------------|---------|
| Product page view | `product_viewed` | product ID, variant ID | `views` metric |
| Add to cart | `product_added_to_cart` | product ID, variant ID, quantity | `add_to_carts` metric |
| Purchase | `checkout_completed` | line items with product IDs, prices | `conversions` + `revenue_cents` |

**Not tracked by pixel** (not needed):
- `page_viewed` — too generic, we only care about product pages
- `collection_viewed` — product thumbnails, not detailed enough for A/B

### 2.5 Variant Attribution

The pixel knows WHICH product was viewed but not WHICH image variant is
currently live. We solve this server-side:

1. When a test starts or swaps, Opal records `active_variant` + timestamp
2. When pixel events arrive, Opal looks up which variant was active for that
   product at that timestamp
3. Events are attributed to the variant that was live at the time

This avoids the need to pass variant info through the storefront (which would
require DOM access that pixels don't have).

**Edge case**: Events during a swap (±30 seconds) get attributed to whichever
variant was active at event timestamp. Acceptable margin of error.

---

## Phase 3: Opal Backend Changes

### 3.1 New Endpoints

Add to `routes_ab_tests.py`:

```python
# ── Pixel event ingestion (no user auth — pixel key auth) ──

@router.post("/pixel-events")
async def receive_pixel_events(
    request: Request,
    body: PixelEventsIn,
):
    """Receive batched events from the Shopify web pixel.

    Auth: X-Pixel-Key header validated against integration's pixel_key.
    No user JWT — this is called from the storefront sandbox.
    """
    # 1. Validate pixel key → find integration + user
    # 2. For each event:
    #    a. Find active A/B test for this product_id + integration
    #    b. Determine which variant was active at event timestamp
    #    c. Upsert into ab_test_metrics (date, variant, metric type)
    # 3. Return 202 Accepted
```

**Request schema**:
```python
class PixelEvent(BaseModel):
    event_type: Literal["view", "add_to_cart", "conversion"]
    product_id: str
    variant_id: str | None = None
    timestamp: str  # ISO 8601
    revenue_cents: int | None = None  # only for conversions

class PixelEventsIn(BaseModel):
    shop_domain: str
    events: list[PixelEvent]  # max 50 per batch
```

**Response**: `202 Accepted` (fire-and-forget from pixel's perspective)

### 3.2 Pixel Key Management

Each integration gets a `pixel_key` (random 32-char token) generated when
the merchant enables A/B testing. Stored in the `integrations` table.

```sql
-- Migration 02X
ALTER TABLE integrations ADD COLUMN pixel_key VARCHAR(64);
```

Generated on first A/B test creation for that integration:
```python
import secrets
pixel_key = secrets.token_urlsafe(32)
```

### 3.3 Variant History Table

To attribute events to the correct variant, we need a log of when swaps
happened:

```sql
-- Migration 02X
CREATE TABLE ab_test_variant_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    test_id UUID NOT NULL REFERENCES ab_tests(id) ON DELETE CASCADE,
    variant VARCHAR(1) NOT NULL,  -- 'a' or 'b'
    activated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (test_id, activated_at)
);
CREATE INDEX idx_variant_log_test ON ab_test_variant_log(test_id, activated_at);
```

Insert a row every time a test starts or swaps. To attribute an event:
```sql
SELECT variant FROM ab_test_variant_log
WHERE test_id = :test_id AND activated_at <= :event_timestamp
ORDER BY activated_at DESC LIMIT 1;
```

### 3.4 Auto-Conclude (Optional)

Add a background check that auto-concludes tests when significance is reached:

```python
# In a periodic task (every hour or on each event batch)
def check_auto_conclude(test_id):
    significance = compute_significance(test_id)
    if significance["confident"] and significance["total_views"] >= 200:
        # Auto-conclude with recommended winner
        conclude_test(test_id, winner=significance["recommended_winner"])
        # Notify merchant via Shopify Admin API notification or email
```

Configurable: merchant can set minimum sample size and confidence level.

### 3.5 Event Processing Flow

```
Pixel POST /v1/ab-tests/pixel-events
  │
  ├─ Validate X-Pixel-Key → find integration
  │
  ├─ For each event in batch:
  │   ├─ Find running ab_test WHERE integration_id AND product_id
  │   ├─ If no running test → skip (product not in a test)
  │   ├─ Look up active variant at event timestamp (variant_log)
  │   ├─ Upsert ab_test_metrics:
  │   │   event_type=view       → views += 1
  │   │   event_type=add_to_cart → add_to_carts += 1
  │   │   event_type=conversion  → conversions += 1, revenue_cents += amount
  │   └─ If auto_conclude enabled → check significance
  │
  └─ Return 202 Accepted
```

---

## Phase 4: Theme App Extension (App Embed Block)

### 4.1 Why We Need This

The Web Pixel alone is sufficient for tracking. But we also need an app embed
block for:

1. **Pixel registration** — the pixel needs `opal_api_url` and `opal_pixel_key`
   settings, which are configured when the merchant enables the app embed
2. **Future: client-side variant swap** — if we ever want to swap images
   client-side (faster than Admin API), the embed block can do DOM manipulation
3. **Status indicator** — optional small badge showing "A/B test running" in
   the theme editor preview

### 4.2 Create the Extension

```bash
shopify app generate extension --type theme_app_extension --name opal-ab-embed
```

Creates:
```
extensions/opal-ab-embed/
├── shopify.extension.toml
├── assets/
│   └── opal-ab.js          # Minimal JS (only if needed)
├── blocks/
│   └── ab-tracker.liquid    # App embed block
└── locales/
    └── en.default.json
```

### 4.3 App Embed Block

`blocks/ab-tracker.liquid`:
```liquid
{% comment %}
  Opal A/B Image Testing — App Embed Block
  Target: head (loads on every page, lightweight)
{% endcomment %}

{% comment %} No visible output — this block only ensures the pixel is active {% endcomment %}
{% comment %} Future: could inject variant swap logic here {% endcomment %}

{% schema %}
{
  "name": "Opal A/B Testing",
  "target": "head",
  "settings": [
    {
      "type": "checkbox",
      "id": "enabled",
      "label": "Enable A/B image tracking",
      "default": true
    }
  ]
}
{% endschema %}
```

For the initial version, the app embed block is minimal — just a presence
indicator. The real tracking is done by the Web Pixel extension.

---

## Phase 5: Shopify Embedded Admin UI

### 5.1 Overview

Merchants need a way to manage A/B tests from within their Shopify admin.
This is an **embedded app** that loads inside the Shopify admin panel.

**Build with**: Remix (Shopify's recommended framework) or a lightweight
React SPA that calls Opal's API.

### 5.2 Pages

| Page | URL | Description |
|------|-----|-------------|
| Dashboard | `/app` | List of all A/B tests with status badges |
| Create Test | `/app/tests/new` | Select product → pick two image variants |
| Test Detail | `/app/tests/:id` | Live metrics, significance gauge, swap/conclude |
| Settings | `/app/settings` | Pixel key display, auto-conclude config |

### 5.3 Create Test Flow

```
1. Merchant clicks "New A/B Test"
2. Product picker (Shopify Resource Picker) → select product
3. Show current product images
4. "Generate variants with Opal" → redirects to Opal app to process
   OR "Upload variant B" → manual image upload
5. Preview both variants side-by-side
6. Click "Start Test" → Opal API:
   a. Creates ab_test record
   b. Pushes variant A image to Shopify (replaces current)
   c. Logs variant activation in variant_log
   d. Returns test ID
7. Dashboard shows test as "Running" with live metrics
```

### 5.4 Test Detail View

```
┌──────────────────────────────────────────────┐
│  A/B Test: "Blue Running Shoes"    RUNNING   │
│  Started: Mar 10, 2026  •  Day 3 of test     │
├──────────────────────────────────────────────┤
│                                              │
│  ┌─────────────┐    ┌─────────────┐          │
│  │  Variant A   │    │  Variant B   │         │
│  │  [image]     │    │  [image]     │         │
│  │              │    │              │         │
│  │  Views: 342  │    │  Views: 338  │         │
│  │  ATC:   28   │    │  ATC:   41   │         │
│  │  Conv:  12   │    │  Conv:  19   │         │
│  │  Rate: 3.5%  │    │  Rate: 5.6%  │ ← +60% │
│  │  Rev: €240   │    │  Rev: €380   │         │
│  └─────────────┘    └─────────────┘          │
│                                              │
│  Significance: 94.2%  (need 95% to confirm)  │
│  ████████████████████████████░░  94.2%       │
│                                              │
│  [ Swap Now ]  [ Conclude: Pick B ]  [Cancel]│
└──────────────────────────────────────────────┘
```

---

## Phase 6: Deployment & App Store

### 6.1 Deployment Architecture

```
Shopify App (Cloudflare Workers or Vercel)
  ├── Embedded Admin UI (React/Remix)
  ├── OAuth callback handler
  └── Proxy to Opal API

Opal Backend (Azure Container Apps) — existing
  ├── /v1/ab-tests/* routes (existing)
  ├── /v1/ab-tests/pixel-events (new)
  └── /v1/shopify-app/* (new, app-specific)

Shopify CDN
  ├── Web Pixel JS bundle (auto-deployed)
  └── Theme App Extension assets (auto-deployed)
```

### 6.2 Deployment Steps

```bash
# Deploy extensions to Shopify
shopify app deploy

# This pushes:
# 1. Web Pixel extension → Shopify CDN
# 2. Theme App Extension → Shopify CDN
# 3. App config updates → Shopify Partner Dashboard
```

### 6.3 App Store Submission Checklist

- [ ] App listing: name, description, screenshots, video demo
- [ ] Privacy policy URL (GDPR-compliant, mention pixel tracking)
- [ ] App icon (1200x1200)
- [ ] Pricing plan (e.g., $19/mo or tied to Opal subscription)
- [ ] Test on a development store end-to-end
- [ ] GDPR webhooks (already implemented in Opal)
- [ ] Mandatory webhooks: `app/uninstalled`, `shop/redact`, `customers/redact`
- [ ] Performance: pixel JS < 10KB gzipped
- [ ] No console errors on storefront
- [ ] Works on mobile storefront
- [ ] Test with Online Store 2.0 theme (Dawn)

### 6.4 App Review Timeline

Shopify reviews typically take **5-10 business days**. Common rejection reasons:
- Pixel causes console errors
- Missing GDPR webhooks (we have these)
- App UI doesn't follow Polaris design guidelines
- Performance impact on storefront
- Missing privacy policy

---

## Phase 7: Testing Strategy

### 7.1 Development Store Testing

1. Create a Shopify Partner account (free)
2. Create a development store
3. Install the app on the dev store
4. Add test products with images
5. Run an A/B test end-to-end:
   - Create test → start → visit product page → add to cart → checkout
   - Verify events arrive at Opal backend
   - Verify metrics update correctly
   - Swap variant → verify image changes on storefront
   - Conclude → verify winner image persists

### 7.2 Edge Cases to Test

- [ ] Multiple concurrent tests on different products
- [ ] Test on a product that gets deleted during the test
- [ ] Pixel events during a variant swap (timing edge case)
- [ ] Merchant uninstalls app while tests are running
- [ ] High-traffic burst (100+ events/second)
- [ ] Shopify CDN image caching after swap (verify propagation delay)
- [ ] Product with no images → start test (should fail gracefully)
- [ ] Free Opal tier user tries to create test (should show upgrade prompt)

---

## Migration Path from Existing A/B Tests

The existing Opal A/B test feature (manual metrics) continues to work.
The Shopify app adds automatic tracking on top:

1. `ab_tests` table gains: `tracking_mode` ENUM ('manual', 'pixel')
2. Tests created from Shopify app default to `tracking_mode = 'pixel'`
3. Tests created from Opal dashboard stay `tracking_mode = 'manual'`
4. Both use the same `ab_test_metrics` table and significance logic
5. Dashboard shows tracking mode badge on each test

---

## Cost & Resource Estimates

| Item | Estimate |
|------|----------|
| Web Pixel extension | 2-3 days |
| Theme App Extension | 1 day |
| Backend: pixel events endpoint | 2 days |
| Backend: variant history + attribution | 1 day |
| Backend: pixel key management | 0.5 day |
| Embedded Admin UI (Remix/React) | 5-7 days |
| OAuth flow updates (new scopes) | 1 day |
| Shopify app manifest + config | 0.5 day |
| Testing on dev store | 2-3 days |
| App Store submission + review fixes | 3-5 days |
| **Total** | **~3-4 weeks** |

### Ongoing Costs

| Item | Cost |
|------|------|
| Pixel event ingestion | Negligible (batched, small payloads) |
| Database growth | ~1 row per product view per day per test (aggregated) |
| Shopify Partner account | Free |
| App hosting (if separate) | ~$5-20/mo (Vercel/CF Workers) |

---

## File Structure (New Project)

```
opal-shopify-ab/
├── shopify.app.toml                    # App config + scopes
├── extensions/
│   ├── opal-ab-tracker/                # Web Pixel
│   │   ├── shopify.extension.toml
│   │   └── src/
│   │       └── index.ts                # Event tracking code
│   └── opal-ab-embed/                  # Theme App Extension
│       ├── shopify.extension.toml
│       ├── blocks/
│       │   └── ab-tracker.liquid
│       └── assets/
│           └── opal-ab.js              # Minimal (if needed)
├── app/                                # Embedded Admin UI (Remix)
│   ├── routes/
│   │   ├── app._index.tsx              # Dashboard
│   │   ├── app.tests.new.tsx           # Create test
│   │   ├── app.tests.$id.tsx           # Test detail
│   │   └── app.settings.tsx            # Settings
│   └── components/
│       ├── TestCard.tsx
│       ├── VariantComparison.tsx
│       └── SignificanceGauge.tsx
└── package.json
```

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Shopify CDN caches images after swap | Visitors see old variant for minutes | Document expected delay; consider client-side swap via embed block in v2 |
| Pixel sandbox prevents DOM access | Can't detect which image is visible | Server-side attribution via variant_log timestamps |
| App review rejection | Delays launch by weeks | Follow Polaris guidelines strictly; test on Dawn theme; keep pixel minimal |
| High event volume overwhelms Opal API | Lost metrics | Batch events (already designed); add rate limiting; use queue for processing |
| Merchant runs test on product with variants (sizes/colors) | Confusing attribution | Track at product level (not variant level); document limitation |

---

## Open Questions

1. **Pricing**: Charge separately for Shopify app ($X/mo) or include in Opal subscription tiers?
2. **Client-side swap (v2)**: Use the app embed block to swap images via DOM instead of Admin API? Faster but more complex and fragile across themes.
3. **Multi-variant (v2)**: Support A/B/C/D testing? Current schema only supports A vs B.
4. **Scheduling**: Auto-swap variants on a schedule (e.g., 1 week each)?
5. **Segments**: Split by device type (mobile vs desktop) or geography?
