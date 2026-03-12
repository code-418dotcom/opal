import { register } from "@shopify/web-pixels-extension";

interface PixelEvent {
  event_type: "view" | "add_to_cart" | "conversion";
  product_id: string;
  variant_id?: string;
  timestamp: string;
  revenue_cents?: number;
}

register(({ analytics, browser, init, settings }) => {
  const API_URL = settings.opal_api_url as string;
  const PIXEL_KEY = settings.opal_pixel_key as string;
  const SHOP_DOMAIN = init.context.document.location.host;

  const FLUSH_INTERVAL_MS = 5000;
  const MAX_BUFFER_SIZE = 10;

  let eventBuffer: PixelEvent[] = [];

  function flushEvents(): void {
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
      // Re-queue on failure (best-effort, cap to avoid memory issues)
      if (eventBuffer.length < 100) {
        eventBuffer.push(...payload);
      }
    });
  }

  function bufferEvent(event: PixelEvent): void {
    eventBuffer.push(event);
    if (eventBuffer.length >= MAX_BUFFER_SIZE) {
      flushEvents();
    }
  }

  // Flush on interval
  setInterval(flushEvents, FLUSH_INTERVAL_MS);

  // ── Product viewed ─────────────────────────────────
  analytics.subscribe("product_viewed", (event) => {
    const product = event.data?.productVariant?.product;
    if (!product?.id) return;
    bufferEvent({
      event_type: "view",
      product_id: extractGid(product.id),
      timestamp: new Date().toISOString(),
    });
  });

  // ── Add to cart ────────────────────────────────────
  analytics.subscribe("product_added_to_cart", (event) => {
    const item = event.data?.cartLine?.merchandise;
    if (!item?.product?.id) return;
    bufferEvent({
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

      // Calculate revenue in cents from line item price
      const priceCents = item.variant?.price
        ? Math.round(Number(item.variant.price.amount) * 100)
        : 0;

      bufferEvent({
        event_type: "conversion",
        product_id: extractGid(item.variant.product.id),
        variant_id: extractGid(item.variant.id),
        timestamp: new Date().toISOString(),
        revenue_cents: priceCents * (item.quantity || 1),
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
