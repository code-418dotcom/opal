import type { Job, CreateJobResponse } from './types';

// Use relative URL if in production/hosted environment, otherwise use localhost
const getApiUrl = () => {
  if (import.meta.env.VITE_API_URL) {
    return import.meta.env.VITE_API_URL;
  }
  // In hosted environments (like Bolt), use relative path to proxy through the same domain
  if (window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1') {
    return ''; // Relative URL - will use same origin
  }
  return 'http://localhost:8080';
};

const API_URL = getApiUrl();
const API_KEY = import.meta.env.VITE_API_KEY || '';

// Log configuration for debugging
console.log('[API Client] Configuration:', {
  apiUrl: API_URL || '(relative path)',
  hostname: window.location.hostname,
  hasApiKey: !!API_KEY
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
      ...options.headers,
    };

    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || `HTTP ${response.status}: ${response.statusText}`);
    }

    return response.json();
  }

  async createJob(filenames: string[]): Promise<CreateJobResponse> {
    return this.request<CreateJobResponse>('/v1/jobs', {
      method: 'POST',
      body: JSON.stringify({
        items: filenames.map(filename => ({ filename })),
      }),
    });
  }

  async getJob(jobId: string): Promise<Job> {
    return this.request<Job>(`/v1/jobs/${jobId}`);
  }

  async uploadDirect(jobId: string, itemId: string, file: File): Promise<void> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('job_id', jobId);
    formData.append('item_id', itemId);

    const url = `${this.baseUrl}/v1/uploads/direct`;
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'X-API-Key': this.apiKey,
      },
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || `Upload failed: ${response.statusText}`);
    }
  }

  async enqueueJob(jobId: string): Promise<void> {
    await this.request(`/v1/jobs/${jobId}/enqueue`, {
      method: 'POST',
    });
  }

  async checkHealth(): Promise<{ status: string }> {
    return this.request('/healthz');
  }
}

export const api = new ApiClient();
