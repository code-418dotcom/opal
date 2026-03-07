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
