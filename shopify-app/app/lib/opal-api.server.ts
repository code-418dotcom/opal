/**
 * Opal API client — server-side only.
 * All calls go through this module so auth and error handling are centralized.
 *
 * Auth: Service API key via X-API-Key header.
 * The service key has access to all users' data; we scope by integration_id
 * which is looked up from the Shopify shop domain.
 */

const OPAL_API_URL = process.env.OPAL_API_URL || "https://dev.opaloptics.com";
const OPAL_SERVICE_KEY = process.env.OPAL_SERVICE_KEY || "";

interface OpalRequestOptions {
  method?: string;
  body?: unknown;
  params?: Record<string, string>;
}

class OpalApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(`Opal API error ${status}: ${detail}`);
    this.status = status;
    this.detail = detail;
  }
}

async function opalFetch<T = unknown>(
  path: string,
  options: OpalRequestOptions = {},
): Promise<T> {
  const { method = "GET", body, params } = options;

  let url = `${OPAL_API_URL}${path}`;
  if (params) {
    const searchParams = new URLSearchParams(params);
    url += `?${searchParams.toString()}`;
  }

  const headers: Record<string, string> = {
    "X-API-Key": OPAL_SERVICE_KEY,
    "Content-Type": "application/json",
  };

  const response = await fetch(url, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const errorBody = await response.json();
      detail = errorBody.detail || detail;
    } catch {
      // ignore parse errors
    }
    throw new OpalApiError(response.status, detail);
  }

  return response.json() as Promise<T>;
}

// ── Types ────────────────────────────────────────────────────────────

export interface ABTest {
  id: string;
  user_id: string;
  integration_id: string;
  product_id: string;
  product_title: string;
  status: "created" | "running" | "concluded" | "canceled";
  variant_a_job_item_id: string;
  variant_b_job_item_id: string;
  variant_a_label: string;
  variant_b_label: string;
  active_variant: "a" | "b";
  winner: "a" | "b" | null;
  original_image_id: string | null;
  tracking_mode: "manual" | "pixel";
  started_at: string | null;
  ended_at: string | null;
  created_at: string;
  updated_at: string;
  // Populated on GET /{id}
  metrics?: Record<string, VariantMetrics>;
  daily_metrics?: DailyMetric[];
  significance?: Significance;
}

export interface VariantMetrics {
  views: number;
  clicks: number;
  add_to_carts: number;
  conversions: number;
  revenue_cents: number;
}

export interface DailyMetric {
  id: string;
  ab_test_id: string;
  variant: string;
  date: string;
  views: number;
  clicks: number;
  add_to_carts: number;
  conversions: number;
  revenue_cents: number;
}

export interface Significance {
  confident: boolean;
  message: string;
  p_value: number | null;
  lift_percent: number | null;
  recommended_winner: "a" | "b" | null;
  conversion_rate_a: number;
  conversion_rate_b: number;
}

export interface Integration {
  id: string;
  user_id: string;
  provider: string;
  store_url: string;
  status: string;
  pixel_key: string | null;
}

// ── API Functions ────────────────────────────────────────────────────

/**
 * Find the Opal integration record for a Shopify shop domain.
 * Returns null if the shop hasn't connected to Opal yet.
 */
export async function getIntegrationByShop(
  shopDomain: string,
): Promise<Integration | null> {
  try {
    const data = await opalFetch<{ integrations: Integration[] }>(
      "/v1/integrations",
      { params: { store_url: shopDomain } },
    );
    return data.integrations?.[0] || null;
  } catch (err) {
    if (err instanceof OpalApiError && err.status === 404) return null;
    throw err;
  }
}

/**
 * List A/B tests for an integration.
 */
export async function listTests(
  integrationId: string,
  status?: string,
): Promise<ABTest[]> {
  const params: Record<string, string> = { integration_id: integrationId };
  if (status) params.status = status;
  const data = await opalFetch<{ tests: ABTest[] }>("/v1/ab-tests", { params });
  return data.tests;
}

/**
 * Get a single A/B test with metrics and significance.
 */
export async function getTest(testId: string): Promise<ABTest> {
  return opalFetch<ABTest>(`/v1/ab-tests/${testId}`);
}

/**
 * Create a new A/B test.
 */
export async function createTest(data: {
  integration_id: string;
  product_id: string;
  product_title?: string;
  variant_a_job_item_id: string;
  variant_b_job_item_id: string;
  variant_a_label?: string;
  variant_b_label?: string;
  original_image_id?: string;
}): Promise<ABTest> {
  return opalFetch<ABTest>("/v1/ab-tests", {
    method: "POST",
    body: data,
  });
}

/**
 * Start an A/B test (pushes variant A to store).
 */
export async function startTest(
  testId: string,
): Promise<{ ok: boolean; active_variant: string }> {
  return opalFetch(`/v1/ab-tests/${testId}/start`, { method: "POST" });
}

/**
 * Swap the active variant on the store.
 */
export async function swapVariant(
  testId: string,
): Promise<{ ok: boolean; active_variant: string }> {
  return opalFetch(`/v1/ab-tests/${testId}/swap`, { method: "POST" });
}

/**
 * Conclude the test and pick a winner.
 */
export async function concludeTest(
  testId: string,
  winner: "a" | "b",
): Promise<{ ok: boolean; winner: string }> {
  return opalFetch(`/v1/ab-tests/${testId}/conclude`, {
    method: "POST",
    body: { winner },
  });
}

/**
 * Cancel a test.
 */
export async function cancelTest(
  testId: string,
): Promise<{ ok: boolean }> {
  return opalFetch(`/v1/ab-tests/${testId}/cancel`, { method: "POST" });
}

/**
 * Get metrics for a test.
 */
export async function getTestMetrics(testId: string): Promise<{
  daily: DailyMetric[];
  aggregated: Record<string, VariantMetrics>;
  significance: Significance;
}> {
  return opalFetch(`/v1/ab-tests/${testId}/metrics`);
}

/**
 * Ensure a pixel key exists for an integration.
 * Called when the merchant enables pixel tracking.
 */
export async function ensurePixelKey(
  integrationId: string,
): Promise<string> {
  const data = await opalFetch<{ pixel_key: string }>(
    `/v1/shopify-app/integrations/${integrationId}/pixel-key`,
    { method: "POST" },
  );
  return data.pixel_key;
}

/**
 * Get statistical significance data for a test.
 */
export async function getSignificance(testId: string): Promise<Significance> {
  return opalFetch<Significance>(`/v1/ab-tests/${testId}/significance`);
}

/**
 * List all integrations for the service account.
 */
export async function listIntegrations(): Promise<Integration[]> {
  const data = await opalFetch<{ integrations: Integration[] }>(
    "/v1/integrations",
  );
  return data.integrations || [];
}

/**
 * List products from a connected store integration.
 */
export async function listProducts(
  integrationId: string,
): Promise<Array<{ id: string; title: string; images: Array<{ id: string; src: string }> }>> {
  const data = await opalFetch<{
    products: Array<{ id: string; title: string; images: Array<{ id: string; src: string }> }>;
  }>(`/v1/integrations/${integrationId}/products`);
  return data.products || [];
}

export { OpalApiError };
