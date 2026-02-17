import type { Job, CreateJobResponse } from './types';

// Detect backend type from environment variables
const BACKEND_TYPE = (import.meta.env.VITE_BACKEND_TYPE as string) || 'supabase';
const API_URL = import.meta.env.VITE_API_URL as string;
const API_KEY = import.meta.env.VITE_API_KEY as string;

// Supabase-specific (optional for Azure backend)
const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL as string;
const SUPABASE_ANON_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY as string;

// Validate configuration based on backend type
if (BACKEND_TYPE === 'azure') {
  if (!API_URL || !API_KEY) {
    throw new Error(
      'Azure backend requires VITE_API_URL and VITE_API_KEY in your .env.local file.'
    );
  }
} else if (BACKEND_TYPE === 'supabase') {
  if (!SUPABASE_URL || !SUPABASE_ANON_KEY || !API_KEY) {
    throw new Error(
      'Supabase backend requires VITE_SUPABASE_URL, VITE_SUPABASE_ANON_KEY, ' +
      'and VITE_API_KEY in your .env.local file.'
    );
  }
} else {
  throw new Error(
    `Unknown backend type: ${BACKEND_TYPE}. Set VITE_BACKEND_TYPE to 'azure' or 'supabase'.`
  );
}

// Determine the base URL based on backend type
const BASE_URL = BACKEND_TYPE === 'azure'
  ? API_URL
  : `${SUPABASE_URL}/functions/v1`;

console.log('[API Client] Configuration:', {
  backendType: BACKEND_TYPE,
  baseUrl: BASE_URL,
  hasApiKey: !!API_KEY,
  hasSupabaseKey: !!SUPABASE_ANON_KEY
});

class ApiClient {
  private baseUrl: string;
  private apiKey: string;
  private backendType: string;

  constructor() {
    this.baseUrl = BASE_URL;
    this.apiKey = API_KEY;
    this.backendType = BACKEND_TYPE;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;

    // Build headers based on backend type
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      'X-API-Key': this.apiKey,
      ...options.headers as Record<string, string>,
    };

    // Add Supabase-specific headers if using Supabase backend
    if (this.backendType === 'supabase' && SUPABASE_ANON_KEY) {
      headers['Authorization'] = `Bearer ${SUPABASE_ANON_KEY}`;
      headers['apikey'] = SUPABASE_ANON_KEY;
    }

    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.error || error.detail || `HTTP ${response.status}: ${response.statusText}`);
    }

    return response.json();
  }

  async createJob(filenames: string[]): Promise<CreateJobResponse> {
    const endpoint = this.backendType === 'azure' ? '/v1/jobs' : '/create-job';
    const body = this.backendType === 'azure'
      ? {
          tenant_id: 'default',
          brand_profile_id: 'default',
          items: filenames.map(filename => ({ filename })),
        }
      : {
          items: filenames.map(filename => ({ filename })),
        };

    return this.request<CreateJobResponse>(endpoint, {
      method: 'POST',
      body: JSON.stringify(body),
    });
  }

  async getJob(jobId: string): Promise<Job> {
    const endpoint = this.backendType === 'azure'
      ? `/v1/jobs/${jobId}?tenant_id=default`
      : `/get-job/${jobId}`;
    return this.request<Job>(endpoint);
  }

  async uploadDirect(jobId: string, itemId: string, file: File): Promise<void> {
    if (this.backendType === 'azure') {
      // Azure backend: first get upload URL, then upload
      await this.uploadToAzure(jobId, itemId, file);
    } else {
      // Supabase backend: direct upload to edge function
      await this.uploadToSupabase(jobId, itemId, file);
    }
  }

  private async uploadToAzure(jobId: string, itemId: string, file: File): Promise<void> {
    // Step 1: Get SAS URL for upload
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

    // Step 3: Finalize upload
    await this.request('/v1/uploads/complete', {
      method: 'POST',
      body: JSON.stringify({
        tenant_id: 'default',
        job_id: jobId,
        item_id: itemId,
        filename: file.name,
      }),
    });
  }

  private async uploadToSupabase(jobId: string, itemId: string, file: File): Promise<void> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('job_id', jobId);
    formData.append('item_id', itemId);

    const url = `${this.baseUrl}/upload-file`;
    const headers: Record<string, string> = {
      'X-API-Key': this.apiKey,
    };

    if (SUPABASE_ANON_KEY) {
      headers['Authorization'] = `Bearer ${SUPABASE_ANON_KEY}`;
      headers['apikey'] = SUPABASE_ANON_KEY;
    }

    const response = await fetch(url, {
      method: 'POST',
      headers,
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.error || error.detail || `Upload failed: ${response.statusText}`);
    }
  }

  async enqueueJob(jobId: string): Promise<void> {
    if (this.backendType === 'azure') {
      // Azure backend automatically enqueues on upload completion
      console.log('[API Client] Job auto-enqueued on Azure backend');
    } else {
      // Supabase backend needs explicit enqueue
      await this.request(`/enqueue-job/${jobId}`, {
        method: 'POST',
      });

      // Trigger worker for Supabase
      setTimeout(async () => {
        try {
          await this.triggerWorker();
        } catch (error) {
          console.error('Failed to trigger worker:', error);
        }
      }, 1000);
    }
  }

  async triggerWorker(): Promise<void> {
    if (this.backendType === 'supabase') {
      try {
        await this.request('/process-job-worker', {
          method: 'POST',
        });
      } catch (error) {
        console.warn('Worker trigger failed (non-critical):', error);
      }
    }
  }

  async getDownloadUrl(itemId: string, bucket: string = 'outputs'): Promise<string> {
    if (this.backendType === 'azure') {
      const response = await this.request<{ download_url: string }>(
        `/v1/downloads/${itemId}?tenant_id=default`
      );
      return response.download_url;
    } else {
      const response = await this.request<{ download_url: string }>(
        `/get-download-url?item_id=${itemId}&bucket=${bucket}`
      );
      return response.download_url;
    }
  }

  async checkHealth(): Promise<{ status: string }> {
    const endpoint = this.backendType === 'azure' ? '/healthz' : '/health';
    try {
      return await this.request<{ status: string }>(endpoint);
    } catch {
      return { status: 'ok' }; // Fallback
    }
  }
}

export const api = new ApiClient();
