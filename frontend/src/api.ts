import type { Job, CreateJobResponse } from './types';

// API configuration - environment variables are REQUIRED
// @ts-expect-error - Vite env variables are available at runtime
const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL as string;
// @ts-expect-error - Vite env variables are available at runtime
const SUPABASE_ANON_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY as string;
// @ts-expect-error - Vite env variables are available at runtime
const API_KEY = import.meta.env.VITE_API_KEY as string;

// Validate required environment variables
if (!SUPABASE_URL || !SUPABASE_ANON_KEY || !API_KEY) {
  throw new Error(
    'Missing required environment variables. Please ensure VITE_SUPABASE_URL, ' +
    'VITE_SUPABASE_ANON_KEY, and VITE_API_KEY are set in your .env.local file.'
  );
}

const API_URL = `${SUPABASE_URL}/functions/v1`;

console.log('[API Client] Configuration:', {
  supabaseUrl: SUPABASE_URL,
  apiUrl: API_URL,
  hasApiKey: !!API_KEY,
  hasAnonKey: !!SUPABASE_ANON_KEY
});

class ApiClient {
  private baseUrl: string;
  private apiKey: string;

  constructor() {
    this.baseUrl = API_URL;
    this.apiKey = API_KEY;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    const headers = {
      'Content-Type': 'application/json',
      'X-API-Key': this.apiKey,
      'Authorization': `Bearer ${SUPABASE_ANON_KEY}`,
      'apikey': SUPABASE_ANON_KEY,
      ...options.headers,
    };

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
    return this.request<CreateJobResponse>('/create-job', {
      method: 'POST',
      body: JSON.stringify({
        items: filenames.map(filename => ({ filename })),
      }),
    });
  }

  async getJob(jobId: string): Promise<Job> {
    return this.request<Job>(`/get-job/${jobId}`);
  }

  async uploadDirect(jobId: string, itemId: string, file: File): Promise<void> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('job_id', jobId);
    formData.append('item_id', itemId);

    const url = `${this.baseUrl}/upload-file`;
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'X-API-Key': this.apiKey,
        'Authorization': `Bearer ${SUPABASE_ANON_KEY}`,
        'apikey': SUPABASE_ANON_KEY,
      },
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.error || error.detail || `Upload failed: ${response.statusText}`);
    }
  }

  async enqueueJob(jobId: string): Promise<void> {
    await this.request(`/enqueue-job/${jobId}`, {
      method: 'POST',
    });

    setTimeout(async () => {
      try {
        await this.triggerWorker();
      } catch (error) {
        console.error('Failed to trigger worker:', error);
      }
    }, 1000);
  }

  async triggerWorker(): Promise<void> {
    try {
      await this.request('/process-job-worker', {
        method: 'POST',
      });
    } catch (error) {
      console.warn('Worker trigger failed (non-critical):', error);
    }
  }

  async getDownloadUrl(itemId: string, bucket: string = 'outputs'): Promise<string> {
    const response = await this.request<{ download_url: string }>(`/get-download-url?item_id=${itemId}&bucket=${bucket}`);
    return response.download_url;
  }

  async checkHealth(): Promise<{ status: string }> {
    return { status: 'ok' };
  }
}

export const api = new ApiClient();
