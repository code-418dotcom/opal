export interface JobItem {
  item_id: string;
  filename: string;
  status: 'created' | 'uploaded' | 'processing' | 'completed' | 'failed';
  raw_blob_path?: string;
  output_blob_path?: string;
  error_message?: string;
  scene_prompt?: string;
  scene_index?: number;
  scene_type?: string;
  saved_background_path?: string;
  seo_alt_text?: string;
  seo_filename?: string;
}

export interface Job {
  job_id: string;
  tenant_id: string;
  brand_profile_id: string;
  status: 'created' | 'processing' | 'completed' | 'failed' | 'partial';
  correlation_id: string;
  export_blob_path?: string;
  items: JobItem[];
}

export interface CreateJobResponse {
  job_id: string;
  correlation_id: string;
  items: Array<{ item_id: string; filename: string; scene_index?: number; scene_type?: string }>;
}

export interface UploadSasResponse {
  upload_url: string;
  raw_blob_path: string;
}

export interface BrandProfile {
  id: string;
  tenant_id: string;
  name: string;
  default_scene_prompt?: string;
  style_keywords: string[];
  color_palette: string[];
  mood?: string;
  product_category?: string;
  default_scene_count?: number;
  default_scene_types?: string[];
  created_at: string;
  updated_at: string;
}

export interface SceneTemplate {
  id: string;
  tenant_id: string;
  brand_profile_id?: string;
  name: string;
  prompt: string;
  preview_blob_path?: string;
  preview_url?: string;
  scene_type?: string;
  created_at: string;
  updated_at: string;
}

export interface TokenPackage {
  id: string;
  name: string;
  tokens: number;
  price_cents: number;
  currency: string;
  active: boolean;
}

export interface TokenTransaction {
  id: string;
  amount: number;
  type: 'purchase' | 'usage' | 'refund' | 'bonus';
  description?: string;
  reference_id?: string;
  created_at: string;
}

export interface Integration {
  id: string;
  user_id: string;
  tenant_id: string;
  provider: 'shopify' | 'woocommerce' | 'etsy';
  store_url: string;
  scopes?: string;
  status: 'active' | 'disconnected' | 'expired';
  provider_metadata?: {
    shop_name?: string;
    shop_email?: string;
    shop_domain?: string;
    shop_plan?: string;
  };
  created_at: string;
  updated_at: string;
}

export interface ShopifyProduct {
  id: number;
  title: string;
  status: string;
  images: ShopifyImage[];
  variants?: Array<{ id: number; title: string; price: string }>;
}

export interface ShopifyImage {
  id: number;
  product_id: number;
  src: string;
  width: number;
  height: number;
  position: number;
}

export interface IntegrationCosts {
  process_image: number;
  push_back: number;
}

export interface PushBackItem {
  item_id: string;
  shopify_product_id: number;
  shopify_image_id?: number;
  mode: 'replace' | 'add';
}

export interface CatalogEstimateProduct {
  id: string;
  title: string;
  image_count: number;
}

export interface CatalogEstimate {
  total_products: number;
  products_with_images: number;
  total_images: number;
  cost_per_image: number;
  tokens_required: number;
  products: CatalogEstimateProduct[];
}

export interface CatalogJob {
  id: string;
  user_id: string;
  integration_id: string;
  status: 'created' | 'processing' | 'completed' | 'failed' | 'canceled';
  total_products: number;
  processed_count: number;
  failed_count: number;
  skipped_count: number;
  total_images: number;
  tokens_estimated: number;
  tokens_spent: number;
  settings: Record<string, unknown>;
  error_message?: string;
  created_at: string;
  updated_at: string;
}

export interface CatalogJobProduct {
  id: string;
  catalog_job_id: string;
  product_id: string;
  product_title?: string;
  job_id?: string;
  image_count: number;
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'skipped';
  error_message?: string;
}

export interface CatalogJobDetail extends CatalogJob {
  products: CatalogJobProduct[];
}

export interface ABTest {
  id: string;
  user_id: string;
  integration_id: string;
  product_id: string;
  product_title?: string;
  status: 'created' | 'running' | 'concluded' | 'canceled';
  variant_a_job_item_id: string;
  variant_b_job_item_id: string;
  variant_a_label: string;
  variant_b_label: string;
  active_variant: 'a' | 'b';
  winner?: string;
  original_image_id?: string;
  started_at?: string;
  ended_at?: string;
  created_at: string;
  updated_at: string;
}

export interface ABTestMetric {
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

export interface ABTestSignificance {
  confident: boolean;
  message: string;
  p_value: number | null;
  lift_percent: number | null;
  recommended_winner: string | null;
  conversion_rate_a?: number;
  conversion_rate_b?: number;
}

export interface ABTestDetail extends ABTest {
  metrics: Record<string, { views: number; clicks: number; add_to_carts: number; conversions: number; revenue_cents: number }>;
  daily_metrics: ABTestMetric[];
  significance: ABTestSignificance;
}

export interface ImageBenchmarkScores {
  resolution: number;
  background: number;
  lighting: number;
  composition: number;
  text_penalty: number;
  image_count: number;
}

export interface BenchmarkSuggestion {
  metric: string;
  action: string;
  message: string;
  priority: 'high' | 'medium' | 'low';
}

export interface ImageBenchmark {
  id: string;
  user_id: string;
  integration_id?: string;
  product_id?: string;
  product_title?: string;
  image_url?: string;
  job_item_id?: string;
  scores: ImageBenchmarkScores;
  overall_score: number;
  suggestions: BenchmarkSuggestion[];
  category: string;
  category_avg?: ImageBenchmarkScores;
  created_at: string;
}

export interface CategoryBenchmark {
  id: string;
  category: string;
  avg_scores: ImageBenchmarkScores;
  sample_size: number;
  updated_at: string;
}

export interface ApiKey {
  id: string;
  name: string;
  prefix: string;
  created_at: string;
  last_used_at: string | null;
}

export interface ApiKeyCreateResponse {
  id: string;
  key: string;
  name: string;
  prefix: string;
  created_at: string;
}

export interface AdminSetting {
  key: string;
  value: string;
  category: string;
  is_secret: boolean;
  description?: string;
  updated_by?: string;
  updated_at?: string;
}

export interface AdminUser {
  id: string;
  email: string;
  tenant_id: string;
  display_name?: string;
  token_balance: number;
  is_admin: boolean;
  created_at: string;
  updated_at: string;
}

export interface SystemInfo {
  env_name: string;
  storage_backend: string;
  queue_backend: string;
  image_gen_provider: string;
  upscale_provider: string;
  upscale_enabled: boolean;
  bg_removal_provider: string;
  has_entra_config: boolean;
  has_mollie_config: boolean;
  has_shopify_config: boolean;
  has_fal_config: boolean;
  has_encryption_key: boolean;
  public_base_url: string;
}

export interface PlatformStats {
  total_users: number;
  total_jobs: number;
  total_tokens_in_circulation: number;
  total_tokens_spent: number;
  total_revenue_cents: number;
  jobs_by_status: Record<string, number>;
}

export interface AdminJob {
  id: string;
  job_id: string;
  tenant_id: string;
  brand_profile_id: string;
  status: string;
  item_count: number;
  created_at: string;
  updated_at: string;
}

export interface AdminIntegration {
  id: string;
  user_id: string;
  tenant_id: string;
  provider: string;
  store_url: string;
  status: string;
  created_at: string;
}

export interface AdminTokenPackage {
  id: string;
  name: string;
  tokens: number;
  price_cents: number;
  currency: string;
  active: boolean;
  created_at: string;
}

export interface AdminTransaction {
  id: string;
  user_id: string;
  amount: number;
  type: string;
  description: string;
  created_at: string;
}

export interface AdminPayment {
  id: string;
  user_id: string;
  package_id: string;
  mollie_payment_id: string;
  amount_cents: number;
  currency: string;
  status: string;
  created_at: string;
}
