import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Image as ImageIcon,
  Download,
  ExternalLink,
  Loader,
  AlertCircle,
  Archive,
  X,
} from 'lucide-react';
import { api } from '../api';
import type { Job } from '../types';

function ResultImage({ itemId }: { itemId: string }) {
  const [src, setSrc] = useState<string | null>(null);
  const [error, setError] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    api
      .getDownloadUrl(itemId, 'outputs')
      .then((url) => {
        if (!cancelled) setSrc(url);
      })
      .catch(() => {
        if (!cancelled) setError(true);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [itemId]);

  if (loading) {
    return (
      <div className="result-placeholder">
        <Loader className="spinning" size={32} />
      </div>
    );
  }

  if (error || !src) {
    return (
      <div className="result-placeholder">
        <ImageIcon size={48} />
        <p>Preview unavailable</p>
      </div>
    );
  }

  return (
    <img className="result-image" src={src} alt="Processed result" onError={() => setError(true)} />
  );
}

interface Props {
  jobId: string | null;
}

export default function ResultsGallery({ jobId }: Props) {
  const [downloadError, setDownloadError] = useState<string | null>(null);

  const { data: job, isLoading, error } = useQuery<Job>({
    queryKey: ['job-results', jobId],
    queryFn: () => api.getJob(jobId!),
    enabled: !!jobId,
  });

  const completedItems = job?.items.filter((item) => item.status === 'completed') || [];

  const handleDownloadItem = async (itemId: string, filename: string) => {
    try {
      setDownloadError(null);
      const url = await api.getDownloadUrl(itemId, 'outputs');
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      link.click();
    } catch {
      setDownloadError('Failed to generate download URL. Please try again.');
    }
  };

  const handleViewItem = async (itemId: string) => {
    try {
      setDownloadError(null);
      const url = await api.getDownloadUrl(itemId, 'outputs');
      window.open(url, '_blank');
    } catch {
      setDownloadError('Failed to generate preview URL. Please try again.');
    }
  };

  const handleDownloadZip = async () => {
    if (!job) return;
    try {
      setDownloadError(null);
      const url = await api.getExportDownloadUrl(job.job_id);
      const link = document.createElement('a');
      link.href = url;
      link.download = `opal-export-${job.job_id.slice(4, 16)}.zip`;
      link.click();
    } catch {
      setDownloadError('Failed to generate export download URL. Please try again.');
    }
  };

  if (!jobId) {
    return (
      <div className="results-gallery">
        <div className="section-header">
          <h2>Results</h2>
          <p>View and download processed images</p>
        </div>
        <div className="empty-state">
          <ImageIcon size={48} />
          <h3>No results yet</h3>
          <p>Upload and process images to see results here</p>
        </div>
      </div>
    );
  }

  return (
    <div className="results-gallery">
      <div className="section-header">
        <h2>Results</h2>
        <p>View and download processed images</p>
      </div>

      {downloadError && (
        <div className="error-box" style={{ marginBottom: '1rem' }}>
          <AlertCircle size={20} />
          <span>{downloadError}</span>
          <button
            className="button-icon"
            onClick={() => setDownloadError(null)}
            style={{ marginLeft: 'auto' }}
          >
            <X size={16} />
          </button>
        </div>
      )}

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
          <p>
            {job.items.length} item(s) are being processed. Check back soon.
          </p>
        </div>
      )}

      {job && completedItems.length > 0 && (
        <>
          {job.export_blob_path && (
            <div className="export-banner">
              <div className="export-banner-info">
                <Archive size={20} />
                <span>
                  All {completedItems.length} image(s) ready for download
                </span>
              </div>
              <button className="button-primary button-sm" onClick={handleDownloadZip}>
                <Archive size={16} />
                Download ZIP
              </button>
            </div>
          )}

          <div className="results-grid">
            {completedItems.map((item) => (
              <div key={item.item_id} className="result-card">
                <div className="result-preview">
                  <ResultImage itemId={item.item_id} />
                </div>

                <div className="result-info">
                  <h4>
                    {item.filename}
                    {item.scene_type && (
                      <span className="result-scene-tag">
                        {item.scene_type.charAt(0).toUpperCase() + item.scene_type.slice(1)}
                      </span>
                    )}
                  </h4>

                  <div className="result-actions">
                    <button
                      className="button-secondary button-sm"
                      onClick={() => handleViewItem(item.item_id)}
                    >
                      <ExternalLink size={14} />
                      View
                    </button>
                    <button
                      className="button-secondary button-sm"
                      onClick={() => handleDownloadItem(item.item_id, item.filename)}
                    >
                      <Download size={14} />
                      Download
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>

          <div className="gallery-summary">
            <p>
              {completedItems.length} of {job.items.length} image(s) completed
            </p>
          </div>
        </>
      )}
    </div>
  );
}
