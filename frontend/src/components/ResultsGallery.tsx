import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Image as ImageIcon, Download, ExternalLink, Loader, AlertCircle } from 'lucide-react';
import { api } from '../api';
import type { Job } from '../types';

interface Props {
  jobId: string | null;
}

export default function ResultsGallery({ jobId: initialJobId }: Props) {
  const [jobId, setJobId] = useState(initialJobId || '');

  useEffect(() => {
    if (initialJobId) {
      setJobId(initialJobId);
    }
  }, [initialJobId]);

  const { data: job, isLoading, error } = useQuery<Job>({
    queryKey: ['job-results', jobId],
    queryFn: () => api.getJob(jobId),
    enabled: !!jobId,
  });

  const completedItems = job?.items.filter((item) => item.status === 'completed') || [];

  return (
    <div className="results-gallery">
      <div className="section-header">
        <h2>Results Gallery</h2>
        <p>View and download processed images</p>
      </div>

      <div className="gallery-controls">
        <input
          type="text"
          placeholder="Enter Job ID to view results"
          value={jobId}
          onChange={(e) => setJobId(e.target.value)}
          className="input"
        />
      </div>

      {error && (
        <div className="error-box">
          <AlertCircle size={20} />
          <span>{error instanceof Error ? error.message : 'Failed to load results'}</span>
        </div>
      )}

      {isLoading && (
        <div className="loading-box">
          <Loader className="spinning" size={32} />
          <span>Loading results...</span>
        </div>
      )}

      {job && !isLoading && completedItems.length === 0 && (
        <div className="empty-state">
          <ImageIcon size={48} />
          <h3>No completed images yet</h3>
          <p>This job has {job.items.length} item(s), but none are completed yet.</p>
          <p className="hint">Check the Monitor tab to see processing status</p>
        </div>
      )}

      {job && completedItems.length > 0 && (
        <div className="results-grid">
          {completedItems.map((item) => (
            <div key={item.item_id} className="result-card">
              <div className="result-preview">
                <div className="result-placeholder">
                  <ImageIcon size={48} />
                  <p>Image Preview</p>
                  <span className="hint">
                    Output available at: {item.output_blob_path}
                  </span>
                </div>
              </div>

              <div className="result-info">
                <h4>{item.filename}</h4>
                <p className="result-meta">ID: {item.item_id}</p>

                <div className="result-actions">
                  <button
                    className="button-secondary button-sm"
                    onClick={async () => {
                      if (item.output_blob_path) {
                        try {
                          const url = await api.getDownloadUrl(item.item_id, 'outputs');
                          window.open(url, '_blank');
                        } catch (error) {
                          console.error('Failed to get download URL:', error);
                          alert('Failed to generate download URL');
                        }
                      }
                    }}
                  >
                    <ExternalLink size={14} />
                    View
                  </button>
                  <button
                    className="button-secondary button-sm"
                    onClick={async () => {
                      if (item.output_blob_path) {
                        try {
                          const url = await api.getDownloadUrl(item.item_id, 'outputs');
                          const link = document.createElement('a');
                          link.href = url;
                          link.download = item.filename;
                          link.click();
                        } catch (error) {
                          console.error('Failed to get download URL:', error);
                          alert('Failed to generate download URL');
                        }
                      }
                    }}
                  >
                    <Download size={14} />
                    Download
                  </button>
                </div>

                <div className="result-paths">
                  <div className="path-item">
                    <span className="path-label">Input:</span>
                    <span className="path-value">{item.raw_blob_path}</span>
                  </div>
                  <div className="path-item">
                    <span className="path-label">Output:</span>
                    <span className="path-value">{item.output_blob_path}</span>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {job && completedItems.length > 0 && (
        <div className="gallery-summary">
          <p>
            Showing {completedItems.length} of {job.items.length} completed image(s)
          </p>
        </div>
      )}
    </div>
  );
}
