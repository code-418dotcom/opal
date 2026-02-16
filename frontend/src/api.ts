import type { Job, CreateJobResponse, UploadSasResponse } from './types';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8080';
const API_KEY = import.meta.env.VITE_API_KEY || '';

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

  async getUploadSas(
    jobId: string,
    itemId: string,
    filename: string
  ): Promise<UploadSasResponse> {
    return this.request<UploadSasResponse>('/v1/uploads/sas', {
      method: 'POST',
      body: JSON.stringify({
        job_id: jobId,
        item_id: itemId,
        filename,
      }),
    });
  }

  async uploadToSas(sasUrl: string, file: File): Promise<void> {
    const response = await fetch(sasUrl, {
      method: 'PUT',
      headers: {
        'x-ms-blob-type': 'BlockBlob',
        'Content-Type': file.type || 'application/octet-stream',
      },
      body: file,
    });

    if (!response.ok) {
      throw new Error(`Upload failed: ${response.statusText}`);
    }
  }

  async completeUpload(jobId: string, itemId: string, filename: string): Promise<void> {
    await this.request('/v1/uploads/complete', {
      method: 'POST',
      body: JSON.stringify({
        job_id: jobId,
        item_id: itemId,
        filename,
      }),
    });
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
