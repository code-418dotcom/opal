export interface JobItem {
  item_id: string;
  filename: string;
  status: 'created' | 'uploaded' | 'processing' | 'completed' | 'failed';
  raw_blob_path?: string;
  output_blob_path?: string;
  error_message?: string;
}

export interface Job {
  job_id: string;
  tenant_id: string;
  brand_profile_id: string;
  status: 'created' | 'processing' | 'completed' | 'failed' | 'partial';
  correlation_id: string;
  items: JobItem[];
}

export interface CreateJobResponse {
  job_id: string;
  correlation_id: string;
  items: Array<{ item_id: string; filename: string }>;
}

export interface UploadSasResponse {
  upload_url: string;
  raw_blob_path: string;
}
