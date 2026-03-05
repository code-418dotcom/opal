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
