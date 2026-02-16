import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { RefreshCw, Clock, CheckCircle, XCircle, Loader, AlertTriangle } from 'lucide-react';
import { api } from '../api';
import type { Job } from '../types';

interface Props {
  jobId: string | null;
}

export default function JobMonitor({ jobId: initialJobId }: Props) {
  const [jobId, setJobId] = useState(initialJobId || '');
  const [autoRefresh, setAutoRefresh] = useState(true);

  useEffect(() => {
    if (initialJobId) {
      setJobId(initialJobId);
    }
  }, [initialJobId]);

  const { data: job, isLoading, error, refetch } = useQuery<Job>({
    queryKey: ['job', jobId],
    queryFn: () => api.getJob(jobId),
    enabled: !!jobId,
    refetchInterval: autoRefresh ? 3000 : false,
  });

  const getStatusBadge = (status: string) => {
    const badges = {
      created: { icon: Clock, class: 'badge-default', label: 'Created' },
      uploaded: { icon: Clock, class: 'badge-default', label: 'Uploaded' },
      processing: { icon: Loader, class: 'badge-processing', label: 'Processing' },
      completed: { icon: CheckCircle, class: 'badge-success', label: 'Completed' },
      failed: { icon: XCircle, class: 'badge-error', label: 'Failed' },
      partial: { icon: AlertTriangle, class: 'badge-warning', label: 'Partial' },
    };

    const badge = badges[status as keyof typeof badges] || badges.created;
    const Icon = badge.icon;

    return (
      <span className={`badge ${badge.class}`}>
        <Icon size={14} className={status === 'processing' ? 'spinning' : ''} />
        {badge.label}
      </span>
    );
  };

  const getProgressStats = (job: Job) => {
    const total = job.items.length;
    const completed = job.items.filter((i) => i.status === 'completed').length;
    const failed = job.items.filter((i) => i.status === 'failed').length;
    const processing = job.items.filter((i) => i.status === 'processing').length;
    const percentage = total > 0 ? Math.round((completed / total) * 100) : 0;

    return { total, completed, failed, processing, percentage };
  };

  return (
    <div className="job-monitor">
      <div className="section-header">
        <h2>Job Monitor</h2>
        <p>Track and monitor job processing status</p>
      </div>

      <div className="monitor-controls">
        <div className="input-group">
          <input
            type="text"
            placeholder="Enter Job ID"
            value={jobId}
            onChange={(e) => setJobId(e.target.value)}
            className="input"
          />
          <button
            className="button-secondary"
            onClick={() => refetch()}
            disabled={!jobId || isLoading}
          >
            <RefreshCw size={16} className={isLoading ? 'spinning' : ''} />
            Refresh
          </button>
        </div>

        <label className="checkbox-label">
          <input
            type="checkbox"
            checked={autoRefresh}
            onChange={(e) => setAutoRefresh(e.target.checked)}
          />
          Auto-refresh (3s)
        </label>
      </div>

      {error && (
        <div className="error-box">
          <XCircle size={20} />
          <span>{error instanceof Error ? error.message : 'Failed to load job'}</span>
        </div>
      )}

      {isLoading && (
        <div className="loading-box">
          <Loader className="spinning" size={32} />
          <span>Loading job details...</span>
        </div>
      )}

      {job && !isLoading && (
        <div className="job-details">
          <div className="job-header">
            <div>
              <h3>Job: {job.job_id}</h3>
              <p className="job-meta">
                Tenant: {job.tenant_id} • Profile: {job.brand_profile_id} •
                Correlation: {job.correlation_id}
              </p>
            </div>
            {getStatusBadge(job.status)}
          </div>

          <div className="progress-section">
            <div className="progress-header">
              <span>Overall Progress</span>
              <span className="progress-percentage">
                {getProgressStats(job).percentage}%
              </span>
            </div>
            <div className="progress-bar large">
              <div
                className="progress-fill"
                style={{ width: `${getProgressStats(job).percentage}%` }}
              ></div>
            </div>
            <div className="progress-stats">
              <span>✓ {getProgressStats(job).completed} completed</span>
              <span>⚙ {getProgressStats(job).processing} processing</span>
              <span>✗ {getProgressStats(job).failed} failed</span>
              <span>Total: {getProgressStats(job).total}</span>
            </div>
          </div>

          <div className="items-section">
            <h4>Items ({job.items.length})</h4>
            <div className="items-list">
              {job.items.map((item) => (
                <div key={item.item_id} className="item-card">
                  <div className="item-header">
                    <div>
                      <div className="item-filename">{item.filename}</div>
                      <div className="item-id">ID: {item.item_id}</div>
                    </div>
                    {getStatusBadge(item.status)}
                  </div>

                  {item.error_message && (
                    <div className="item-error">
                      <AlertTriangle size={16} />
                      <span>{item.error_message}</span>
                    </div>
                  )}

                  {item.raw_blob_path && (
                    <div className="item-path">
                      <strong>Input:</strong> {item.raw_blob_path}
                    </div>
                  )}

                  {item.output_blob_path && (
                    <div className="item-path success">
                      <strong>Output:</strong> {item.output_blob_path}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
