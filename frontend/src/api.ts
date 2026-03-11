import type { Job, CreateJobResponse, BrandProfile, SceneTemplate, TokenPackage, TokenTransaction, Integration, ShopifyProduct, IntegrationCosts, PushBackItem, AdminSetting, AdminUser, SystemInfo, PlatformStats, AdminJob, AdminIntegration, AdminTokenPackage, AdminTransaction, AdminPayment, CatalogEstimate, CatalogJob, CatalogJobDetail, ABTest, ABTestDetail, ABTestMetric, ImageBenchmark, CategoryBenchmark, ApiKey, ApiKeyCreateResponse } from './types';

const API_URL = (import.meta.env.VITE_API_URL as string) || '';
const API_KEY = import.meta.env.VITE_API_KEY as string;

if (import.meta.env.DEV) {
  console.log('[API Client] Configuration:', {
    baseUrl: API_URL,
    hasApiKey: !!API_KEY,
  });
}

class ApiClient {
  private baseUrl: string;
  private apiKey: string;
  private accessToken: string | null = null;

  constructor() {
    this.baseUrl = API_URL;
    this.apiKey = API_KEY;
  }

  setAccessToken(token: string | null) {
    this.accessToken = token;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...options.headers as Record<string, string>,
    };

    // Prefer Bearer token (Entra auth), fall back to API key
    if (this.accessToken) {
      headers['Authorization'] = `Bearer ${this.accessToken}`;
    } else if (this.apiKey) {
      headers['X-API-Key'] = this.apiKey;
    }

    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      const msg = error.error || error.detail;
      const msgStr = typeof msg === 'string' ? msg : msg ? JSON.stringify(msg) : null;
      throw new Error(msgStr || `HTTP ${response.status}: ${response.statusText}`);
    }

    if (response.status === 204) return undefined as T;
    return response.json();
  }

  async createJob(
    filenames: string[],
    processingOptions?: {
      remove_background: boolean;
      generate_scene: boolean;
      upscale: boolean;
    },
    sceneOptions?: {
      scene_count?: number;
      scene_types?: string[];
      scene_template_ids?: string[];
      use_saved_background?: boolean;
      angle_types?: string[];
    },
    brandProfileId?: string,
  ): Promise<CreateJobResponse> {
    return this.request<CreateJobResponse>('/v1/jobs', {
      method: 'POST',
      body: JSON.stringify({
        brand_profile_id: brandProfileId || 'default',
        items: filenames.map(filename => ({
          filename,
          ...(sceneOptions?.scene_count && sceneOptions.scene_count > 1
            ? { scene_count: sceneOptions.scene_count }
            : {}),
          ...(sceneOptions?.scene_types ? { scene_types: sceneOptions.scene_types } : {}),
          ...(sceneOptions?.scene_template_ids ? {
            scene_template_ids: sceneOptions.scene_template_ids,
            use_saved_background: sceneOptions.use_saved_background || false,
          } : {}),
          ...(sceneOptions?.angle_types && sceneOptions.angle_types.length > 0
            ? { angle_types: sceneOptions.angle_types }
            : {}),
        })),
        processing_options: processingOptions || {
          remove_background: true,
          generate_scene: true,
          upscale: true
        },
      }),
    });
  }

  async getExportDownloadUrl(jobId: string): Promise<string> {
    const response = await this.request<{ download_url: string }>(
      `/v1/downloads/jobs/${jobId}/export`
    );
    return response.download_url;
  }

  async getExportPresets(): Promise<Array<{ key: string; name: string; width: number; height: number }>> {
    const resp = await this.request<{ presets: Array<{ key: string; name: string; width: number; height: number }> }>(
      '/v1/export-presets'
    );
    return resp.presets;
  }

  async requestFormatExport(jobId: string, formatKeys: string[]): Promise<{ status: string; job_id: string; format_keys: string[] }> {
    return this.request('/v1/downloads/jobs/' + jobId + '/export-formats', {
      method: 'POST',
      body: JSON.stringify({ format_keys: formatKeys }),
    });
  }

  async getJob(jobId: string): Promise<Job> {
    return this.request<Job>(`/v1/jobs/${jobId}`);
  }

  async listJobs(limit = 20, offset = 0): Promise<{ jobs: Job[]; limit: number; offset: number }> {
    return this.request(`/v1/jobs?limit=${limit}&offset=${offset}`);
  }

  async uploadDirect(jobId: string, itemId: string, file: File, processingOptions?: {
    remove_background: boolean;
    generate_scene: boolean;
    upscale: boolean;
  }): Promise<void> {
    // Step 1: Get SAS URL for upload (also sets raw_blob_path on all siblings)
    const sasResponse = await this.request<{ upload_url: string }>('/v1/uploads/sas', {
      method: 'POST',
      body: JSON.stringify({
        tenant_id: 'default',
        job_id: jobId,
        item_id: itemId,
        filename: file.name,
        content_type: file.type || 'image/jpeg',
      }),
    });

    // Step 2: Upload to blob storage using SAS URL
    const uploadResponse = await fetch(sasResponse.upload_url, {
      method: 'PUT',
      headers: {
        'x-ms-blob-type': 'BlockBlob',
        'Content-Type': file.type || 'image/jpeg',
      },
      body: file,
    });

    if (!uploadResponse.ok) {
      throw new Error(`Upload to Azure Blob failed: ${uploadResponse.statusText}`);
    }

    // Step 3: Finalize upload (sends queue messages for all siblings)
    await this.request('/v1/uploads/complete', {
      method: 'POST',
      body: JSON.stringify({
        tenant_id: 'default',
        job_id: jobId,
        item_id: itemId,
        filename: file.name,
        processing_options: processingOptions || {
          remove_background: true,
          generate_scene: true,
          upscale: true
        },
      }),
    });
  }

  async enqueueJob(_jobId: string): Promise<void> {
    // Azure backend automatically enqueues on upload completion
    console.log('[API Client] Job auto-enqueued on upload completion');
  }

  async cancelJob(jobId: string): Promise<{ cancelled_items: number; completed_items: number; refunded_tokens: number }> {
    return this.request(`/v1/jobs/${jobId}/cancel`, { method: 'POST' });
  }

  async cancelAllJobs(): Promise<{ cancelled_jobs: number; cancelled_items: number; refunded_tokens: number }> {
    return this.request('/v1/jobs/cancel-all', { method: 'POST' });
  }

  async getDownloadUrl(itemId: string, _bucket: string = 'outputs'): Promise<string> {
    const response = await this.request<{ download_url: string }>(
      `/v1/downloads/${itemId}`
    );
    return response.download_url;
  }

  async checkHealth(): Promise<{ status: string }> {
    try {
      return await this.request<{ status: string }>('/healthz');
    } catch {
      return { status: 'error' };
    }
  }

  // ── Brand Profiles ──────────────────────────────────────────────

  async listBrandProfiles(): Promise<BrandProfile[]> {
    return this.request<BrandProfile[]>('/v1/brand-profiles');
  }

  async createBrandProfile(data: Partial<BrandProfile>): Promise<BrandProfile> {
    return this.request<BrandProfile>('/v1/brand-profiles', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateBrandProfile(id: string, data: Partial<BrandProfile>): Promise<BrandProfile> {
    return this.request<BrandProfile>(`/v1/brand-profiles/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deleteBrandProfile(id: string): Promise<void> {
    await this.request(`/v1/brand-profiles/${id}`, { method: 'DELETE' });
  }

  // ── Brand Reference Images ─────────────────────────────────────

  async listReferenceImages(profileId: string): Promise<{ reference_images: Array<{ id: string; blob_path: string; download_url?: string; extracted_style?: { colors?: string[]; lighting?: string; mood?: string; keywords?: string[] }; created_at: string }> }> {
    return this.request(`/v1/brand-profiles/${profileId}/reference-images`);
  }

  async uploadReferenceImage(profileId: string, filename: string): Promise<{ upload_url: string; reference_image: { id: string } }> {
    return this.request(`/v1/brand-profiles/${profileId}/reference-images`, {
      method: 'POST',
      body: JSON.stringify({ filename }),
    });
  }

  async analyzeReferenceImage(profileId: string, imageId: string): Promise<{ extracted_style: { colors?: string[]; lighting?: string; mood?: string; keywords?: string[] } }> {
    return this.request(`/v1/brand-profiles/${profileId}/reference-images/${imageId}/analyze`, {
      method: 'POST',
    });
  }

  async deleteReferenceImage(profileId: string, imageId: string): Promise<void> {
    await this.request(`/v1/brand-profiles/${profileId}/reference-images/${imageId}`, { method: 'DELETE' });
  }

  // ── Scene Templates ─────────────────────────────────────────────

  async listSceneTemplates(brandProfileId?: string): Promise<SceneTemplate[]> {
    const params = brandProfileId ? `?brand_profile_id=${brandProfileId}` : '';
    return this.request<SceneTemplate[]>(`/v1/scene-templates${params}`);
  }

  async createSceneTemplate(data: { name: string; prompt: string; brand_profile_id?: string; scene_type?: string }): Promise<SceneTemplate> {
    return this.request<SceneTemplate>('/v1/scene-templates', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async deleteSceneTemplate(id: string): Promise<void> {
    await this.request(`/v1/scene-templates/${id}`, { method: 'DELETE' });
  }

  async generateScenePreview(prompt: string): Promise<{ preview_url: string; preview_blob_path: string }> {
    return this.request('/v1/scene-templates/preview', {
      method: 'POST',
      body: JSON.stringify({ prompt }),
    });
  }

  async setSceneTemplatePreview(id: string, previewBlobPath: string): Promise<SceneTemplate> {
    return this.request<SceneTemplate>(`/v1/scene-templates/${id}/set-preview`, {
      method: 'POST',
      body: JSON.stringify({ preview_blob_path: previewBlobPath }),
    });
  }

  // ── Billing ────────────────────────────────────────────────────────

  async getBalance(): Promise<{ token_balance: number; is_admin: boolean }> {
    return this.request('/v1/billing/balance');
  }

  async listPackages(): Promise<TokenPackage[]> {
    const resp = await this.request<{ packages: TokenPackage[] }>('/v1/billing/packages');
    return resp.packages;
  }

  async purchaseTokens(packageId: string, redirectUrl: string): Promise<{ payment_url: string; payment_id: string }> {
    return this.request('/v1/billing/purchase', {
      method: 'POST',
      body: JSON.stringify({ package_id: packageId, redirect_url: redirectUrl }),
    });
  }

  async getPaymentStatus(paymentId: string): Promise<{ id: string; status: string; amount_cents: number; currency: string }> {
    return this.request(`/v1/billing/payments/${paymentId}`);
  }

  async listTransactions(limit = 50, offset = 0): Promise<TokenTransaction[]> {
    const resp = await this.request<{ transactions: TokenTransaction[] }>(
      `/v1/billing/transactions?limit=${limit}&offset=${offset}`
    );
    return resp.transactions;
  }

  // ── Subscriptions ──────────────────────────────────────────────────

  async listSubscriptionPlans(): Promise<Array<{ id: string; name: string; tokens_per_month: number; price_cents: number; currency: string; interval: string }>> {
    const resp = await this.request<{ plans: Array<{ id: string; name: string; tokens_per_month: number; price_cents: number; currency: string; interval: string }> }>(
      '/v1/billing/subscription-plans'
    );
    return resp.plans;
  }

  async getSubscription(): Promise<{ subscription: { id: string; plan_id: string; status: string; plan?: { name: string; tokens_per_month: number; price_cents: number }; current_period_end?: string } | null }> {
    return this.request('/v1/billing/subscription');
  }

  async subscribe(planId: string, redirectUrl: string): Promise<{ payment_url: string; subscription_id: string }> {
    return this.request('/v1/billing/subscribe', {
      method: 'POST',
      body: JSON.stringify({ plan_id: planId, redirect_url: redirectUrl }),
    });
  }

  async cancelSubscription(): Promise<{ ok: boolean }> {
    return this.request('/v1/billing/subscription/cancel', { method: 'POST' });
  }

  // ── Integrations ──────────────────────────────────────────────────

  async listIntegrations(provider?: string): Promise<Integration[]> {
    const params = provider ? `?provider=${provider}` : '';
    const resp = await this.request<{ integrations: Integration[] }>(
      `/v1/integrations${params}`
    );
    return resp.integrations;
  }

  async connectShopify(shop: string): Promise<{ auth_url: string }> {
    return this.request('/v1/integrations/shopify/connect', {
      method: 'POST',
      body: JSON.stringify({ shop }),
    });
  }

  async disconnectIntegration(integrationId: string): Promise<void> {
    await this.request(`/v1/integrations/${integrationId}`, { method: 'DELETE' });
  }

  async getIntegrationCosts(provider: string): Promise<IntegrationCosts> {
    return this.request(`/v1/integrations/costs?provider=${provider}`);
  }

  async listShopifyProducts(
    integrationId: string,
    limit = 50,
    pageInfo?: string
  ): Promise<{ products: ShopifyProduct[]; next_page_info: string | null }> {
    const params = pageInfo ? `?limit=${limit}&page_info=${pageInfo}` : `?limit=${limit}`;
    return this.request(`/v1/integrations/${integrationId}/products${params}`);
  }

  async listShopifyProductImages(
    integrationId: string,
    productId: number
  ): Promise<{ images: Array<{ id: number; src: string; width: number; height: number; position: number }> }> {
    return this.request(`/v1/integrations/${integrationId}/products/${productId}/images`);
  }

  async processShopifyImages(
    integrationId: string,
    productId: number,
    imageIds?: number[],
    brandProfileId = 'default',
    processingOptions?: { remove_background: boolean; generate_scene: boolean; upscale: boolean },
    sceneOptions?: {
      scene_count?: number;
      scene_template_ids?: string[];
      use_saved_background?: boolean;
      angle_types?: string[];
    },
  ): Promise<{ job_id: string; correlation_id: string; items: Array<{ item_id: string; filename: string; shopify_image_id: number; shopify_product_id: number }> }> {
    return this.request(`/v1/integrations/${integrationId}/process`, {
      method: 'POST',
      body: JSON.stringify({
        product_id: productId,
        image_ids: imageIds || null,
        brand_profile_id: brandProfileId,
        processing_options: processingOptions || {
          remove_background: true,
          generate_scene: true,
          upscale: true,
        },
        ...(sceneOptions?.scene_count && sceneOptions.scene_count > 1 ? { scene_count: sceneOptions.scene_count } : {}),
        ...(sceneOptions?.scene_template_ids?.length ? { scene_template_ids: sceneOptions.scene_template_ids } : {}),
        ...(sceneOptions?.use_saved_background ? { use_saved_background: true } : {}),
        ...(sceneOptions?.angle_types?.length ? { angle_types: sceneOptions.angle_types } : {}),
      }),
    });
  }

  async pushBackToShopify(
    integrationId: string,
    jobId: string,
    items: PushBackItem[]
  ): Promise<{ results: Array<{ item_id: string; status: string; shopify_image_id?: number; error?: string }> }> {
    return this.request(`/v1/integrations/${integrationId}/push-back`, {
      method: 'POST',
      body: JSON.stringify({ job_id: jobId, items }),
    });
  }

  // ── WooCommerce Integration ──────────────────────────────────────

  async connectWooCommerce(storeUrl: string): Promise<{ auth_url: string }> {
    return this.request('/v1/integrations/woocommerce/connect', {
      method: 'POST',
      body: JSON.stringify({ store_url: storeUrl }),
    });
  }

  async listWooCommerceProducts(
    integrationId: string,
    perPage = 50,
    page = 1
  ): Promise<{ products: Array<{ id: number; name: string; status: string; images: Array<{ id: number; src: string; name: string; alt: string }> }>; total_pages: number; page: number }> {
    return this.request(`/v1/integrations/${integrationId}/wc-products?per_page=${perPage}&page=${page}`);
  }

  // ── Etsy Integration ─────────────────────────────────────────────

  async connectEtsy(shopId: string): Promise<{ auth_url: string }> {
    return this.request('/v1/integrations/etsy/connect', {
      method: 'POST',
      body: JSON.stringify({ shop_id: shopId }),
    });
  }

  async listEtsyListings(
    integrationId: string,
    limit = 25,
    offset = 0
  ): Promise<{ listings: Array<{ listing_id: number; title: string; state: string; images: Array<{ listing_image_id: number; url_570xN: string; rank: number }> }>; count: number }> {
    return this.request(`/v1/integrations/${integrationId}/etsy-listings?limit=${limit}&offset=${offset}`);
  }

  // ── Catalog Processing ──────────────────────────────────────────

  async estimateCatalog(integrationId: string): Promise<CatalogEstimate> {
    return this.request(`/v1/catalog/${integrationId}/estimate`);
  }

  async startCatalogJob(
    integrationId: string,
    options: {
      brand_profile_id?: string;
      auto_push_back?: boolean;
      product_ids?: string[];
      processing_options?: { remove_background: boolean; generate_scene: boolean; upscale: boolean };
    }
  ): Promise<{ catalog_job_id: string; total_products: number; total_images: number; tokens_estimated: number }> {
    return this.request(`/v1/catalog/${integrationId}/start`, {
      method: 'POST',
      body: JSON.stringify(options),
    });
  }

  async listCatalogJobs(integrationId: string): Promise<{ catalog_jobs: CatalogJob[] }> {
    return this.request(`/v1/catalog/${integrationId}/jobs`);
  }

  async getCatalogJobStatus(integrationId: string, catalogJobId: string): Promise<CatalogJobDetail> {
    return this.request(`/v1/catalog/${integrationId}/jobs/${catalogJobId}`);
  }

  async cancelCatalogJob(integrationId: string, catalogJobId: string): Promise<{ ok: boolean }> {
    return this.request(`/v1/catalog/${integrationId}/jobs/${catalogJobId}/cancel`, {
      method: 'POST',
    });
  }

  // ── A/B Tests ──────────────────────────────────────────────────────

  async createABTest(data: {
    integration_id: string;
    product_id: string;
    product_title?: string;
    variant_a_job_item_id: string;
    variant_b_job_item_id: string;
    variant_a_label?: string;
    variant_b_label?: string;
    original_image_id?: string;
  }): Promise<ABTest> {
    return this.request('/v1/ab-tests', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async listABTests(integrationId?: string, status?: string): Promise<{ tests: ABTest[] }> {
    const params = new URLSearchParams();
    if (integrationId) params.set('integration_id', integrationId);
    if (status) params.set('status', status);
    const qs = params.toString();
    return this.request(`/v1/ab-tests${qs ? '?' + qs : ''}`);
  }

  async getABTest(testId: string): Promise<ABTestDetail> {
    return this.request(`/v1/ab-tests/${testId}`);
  }

  async startABTest(testId: string): Promise<{ ok: boolean; active_variant: string }> {
    return this.request(`/v1/ab-tests/${testId}/start`, { method: 'POST' });
  }

  async swapABTestVariant(testId: string): Promise<{ ok: boolean; active_variant: string }> {
    return this.request(`/v1/ab-tests/${testId}/swap`, { method: 'POST' });
  }

  async concludeABTest(testId: string, winner: string): Promise<{ ok: boolean; winner: string }> {
    return this.request(`/v1/ab-tests/${testId}/conclude`, {
      method: 'POST',
      body: JSON.stringify({ winner }),
    });
  }

  async cancelABTest(testId: string): Promise<{ ok: boolean }> {
    return this.request(`/v1/ab-tests/${testId}/cancel`, { method: 'POST' });
  }

  async recordABTestMetric(testId: string, data: {
    variant: string;
    date: string;
    views?: number;
    clicks?: number;
    add_to_carts?: number;
    conversions?: number;
    revenue_cents?: number;
  }): Promise<ABTestMetric> {
    return this.request(`/v1/ab-tests/${testId}/metrics`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getABTestMetrics(testId: string): Promise<{ daily: ABTestMetric[]; aggregated: Record<string, Record<string, number>>; significance: Record<string, unknown> }> {
    return this.request(`/v1/ab-tests/${testId}/metrics`);
  }

  // ── Benchmarks ──────────────────────────────────────────────────

  async analyzeBenchmark(data: {
    job_item_id?: string;
    image_url?: string;
    product_title?: string;
    product_id?: string;
    integration_id?: string;
    category?: string;
    image_count?: number;
  }): Promise<ImageBenchmark> {
    return this.request('/v1/benchmarks/analyze', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async analyzeBenchmarkFile(file: File, category = 'general', imageCount = 1): Promise<ImageBenchmark> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('category', category);
    formData.append('image_count', String(imageCount));

    const url = `${this.baseUrl}/v1/benchmarks/analyze-upload`;
    const headers: Record<string, string> = {};
    if (this.accessToken) {
      headers['Authorization'] = `Bearer ${this.accessToken}`;
    } else if (this.apiKey) {
      headers['X-API-Key'] = this.apiKey;
    }

    const response = await fetch(url, { method: 'POST', body: formData, headers });
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }
    return response.json();
  }

  async listBenchmarks(integrationId?: string, category?: string): Promise<{ benchmarks: ImageBenchmark[] }> {
    const params = new URLSearchParams();
    if (integrationId) params.set('integration_id', integrationId);
    if (category) params.set('category', category);
    const qs = params.toString();
    return this.request(`/v1/benchmarks${qs ? '?' + qs : ''}`);
  }

  async getBenchmark(benchmarkId: string): Promise<ImageBenchmark> {
    return this.request(`/v1/benchmarks/${benchmarkId}`);
  }

  async listBenchmarkCategories(): Promise<{ categories: CategoryBenchmark[] }> {
    return this.request('/v1/benchmarks/categories');
  }

  // ── Admin ─────────────────────────────────────────────────────────

  async getSystemInfo(): Promise<SystemInfo> {
    return this.request('/v1/admin/system');
  }

  async listAdminSettings(category?: string): Promise<AdminSetting[]> {
    const params = category ? `?category=${category}` : '';
    const resp = await this.request<{ settings: AdminSetting[] }>(`/v1/admin/settings${params}`);
    return resp.settings;
  }

  async updateAdminSetting(key: string, value: string): Promise<AdminSetting> {
    return this.request(`/v1/admin/settings/${key}`, {
      method: 'PUT',
      body: JSON.stringify({ value }),
    });
  }

  async createAdminSetting(data: { key: string; value?: string; category?: string; is_secret?: boolean; description?: string }): Promise<AdminSetting> {
    return this.request('/v1/admin/settings', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async deleteAdminSetting(key: string): Promise<void> {
    await this.request(`/v1/admin/settings/${key}`, { method: 'DELETE' });
  }

  async listAdminUsers(limit = 100, offset = 0): Promise<AdminUser[]> {
    const resp = await this.request<{ users: AdminUser[] }>(
      `/v1/admin/users?limit=${limit}&offset=${offset}`
    );
    return resp.users;
  }

  async setUserAdmin(userId: string, isAdmin: boolean): Promise<AdminUser> {
    return this.request(`/v1/admin/users/${userId}/admin`, {
      method: 'PUT',
      body: JSON.stringify({ is_admin: isAdmin }),
    });
  }

  async setUserTokens(userId: string, tokenBalance: number): Promise<AdminUser> {
    return this.request(`/v1/admin/users/${userId}/tokens`, {
      method: 'PUT',
      body: JSON.stringify({ token_balance: tokenBalance }),
    });
  }

  async getPlatformStats(): Promise<PlatformStats> {
    return this.request('/v1/admin/stats');
  }

  async listAdminJobs(limit = 50, offset = 0, status?: string): Promise<AdminJob[]> {
    const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
    if (status) params.set('status', status);
    const resp = await this.request<{ jobs: AdminJob[] }>(`/v1/admin/jobs?${params}`);
    return resp.jobs;
  }

  async listAdminIntegrations(limit = 50, offset = 0): Promise<AdminIntegration[]> {
    const resp = await this.request<{ integrations: AdminIntegration[] }>(
      `/v1/admin/integrations?limit=${limit}&offset=${offset}`
    );
    return resp.integrations;
  }

  async listAdminPackages(): Promise<AdminTokenPackage[]> {
    const resp = await this.request<{ packages: AdminTokenPackage[] }>('/v1/admin/packages');
    return resp.packages;
  }

  async createAdminPackage(data: { name: string; tokens: number; price_cents: number; currency?: string; active?: boolean }): Promise<AdminTokenPackage> {
    return this.request('/v1/admin/packages', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateAdminPackage(id: string, data: Record<string, unknown>): Promise<AdminTokenPackage> {
    return this.request(`/v1/admin/packages/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deleteAdminPackage(id: string): Promise<void> {
    await this.request(`/v1/admin/packages/${id}`, { method: 'DELETE' });
  }

  async listAdminTransactions(limit = 50, offset = 0): Promise<AdminTransaction[]> {
    const resp = await this.request<{ transactions: AdminTransaction[] }>(
      `/v1/admin/transactions?limit=${limit}&offset=${offset}`
    );
    return resp.transactions;
  }

  async listAdminPayments(limit = 50, offset = 0): Promise<AdminPayment[]> {
    const resp = await this.request<{ payments: AdminPayment[] }>(
      `/v1/admin/payments?limit=${limit}&offset=${offset}`
    );
    return resp.payments;
  }

  // ── API Keys ──────────────────────────────────────────────────────

  async listApiKeys(): Promise<ApiKey[]> {
    const resp = await this.request<{ api_keys: ApiKey[] }>('/v1/account/api-keys');
    return resp.api_keys;
  }

  async createApiKey(name?: string): Promise<ApiKeyCreateResponse> {
    return this.request<ApiKeyCreateResponse>('/v1/account/api-keys', {
      method: 'POST',
      body: JSON.stringify({ name: name || undefined }),
    });
  }

  async revokeApiKey(keyId: string): Promise<void> {
    await this.request(`/v1/account/api-keys/${keyId}`, { method: 'DELETE' });
  }

  // ── Preferences ──────────────────────────────────────────────────

  async getPreferences(): Promise<{ preferences: Record<string, unknown> }> {
    return this.request('/v1/account/preferences');
  }

  async updatePreferences(prefs: Record<string, unknown>): Promise<{ preferences: Record<string, unknown> }> {
    return this.request('/v1/account/preferences', {
      method: 'PUT',
      body: JSON.stringify(prefs),
    });
  }
}

export const api = new ApiClient();
