import { useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { RefreshCw, Clock, CheckCircle, XCircle, Loader, AlertTriangle } from 'lucide-react';
import { api } from '../api';
import type { Job } from '../types';

interface Props {
  jobId: string | null;
}

const STATUS_WEIGHT: Record<string, number> = {
  created: 0,
  uploaded: 15,
  processing: 50,
  completed: 100,
  failed: 100,
};

export default function JobMonitor({ jobId }: Props) {
  const { data: job, isLoading, error, refetch } = useQuery<Job>({
    queryKey: ['job', jobId],
    queryFn: () => api.getJob(jobId!),
    enabled: !!jobId,
    refetchInterval: 3000,
  });

  // Invalidate related queries when job completes
  useEffect(() => {
    if (job && (job.status === 'completed' || job.status === 'partial')) {
      // Stop polling handled by parent auto-nav
    }
  }, [job]);

  const getStatusBadge = (status: string) => {
    const badges: Record<string, { icon: typeof Clock; cls: string; label: string }> = {
      created: { icon: Clock, cls: 'badge-default', label: 'Queued' },
      uploaded: { icon: Clock, cls: 'badge-default', label: 'Uploaded' },
      processing: { icon: Loader, cls: 'badge-processing', label: 'Processing' },
      completed: { icon: CheckCircle, cls: 'badge-success', label: 'Completed' },
      failed: { icon: XCircle, cls: 'badge-error', label: 'Failed' },
      partial: { icon: AlertTriangle, cls: 'badge-warning', label: 'Partial' },
    };

    const badge = badges[status] || badges.created;
    const Icon = badge.icon;

    return (
      <span className={`badge ${badge.cls}`}>
        <Icon size={14} className={status === 'processing' ? 'spinning' : ''} />
        {badge.label}
      </span>
    );
  };

  const getProgressStats = (job: Job) => {
    const total = job.items.length;
    if (total === 0) return { total: 0, completed: 0, failed: 0, processing: 0, percentage: 0 };

    const completed = job.items.filter((i) => i.status === 'completed').length;
    const failed = job.items.filter((i) => i.status === 'failed').length;
    const processing = job.items.filter((i) => i.status === 'processing').length;

    const weightedSum = job.items.reduce(
      (sum, item) => sum + (STATUS_WEIGHT[item.status] ?? 0),
      0
    );
    const percentage = Math.round(weightedSum / total);

    return { total, completed, failed, processing, percentage };
  };

  const getProgressBarClass = (job: Job) => {
    if (job.status === 'completed') return 'progress-fill progress-fill-success';
    if (job.status === 'failed') return 'progress-fill progress-fill-error';
    if (job.status === 'partial') return 'progress-fill progress-fill-warning';
    return 'progress-fill';
  };

  if (!jobId) {
    return (
      <div className="job-monitor">
        <div className="section-header">
          <h2>Job Monitor</h2>
          <p>Upload images to start tracking a job</p>
        </div>
        <div className="empty-state">
          <Loader size={48} />
          <h3>No active job</h3>
          <p>Upload images from the Upload tab to create a job</p>
        </div>
      </div>
    );
  }

  return (
    <div className="job-monitor">
      <div className="section-header">
        <div className="section-header-row">
          <div>
            <h2>Job Monitor</h2>
            <p>Tracking job progress in real-time</p>
          </div>
          <button
            className="button-secondary"
            onClick={() => refetch()}
            disabled={isLoading}
          >
            <RefreshCw size={16} className={isLoading ? 'spinning' : ''} />
            Refresh
          </button>
        </div>
      </div>

      {error && (
        <div className="error-box">
          <XCircle size={20} />
          <span>{error instanceof Error ? error.message : 'Failed to load job'}</span>
        </div>
      )}

      {isLoading && !job && (
        <div className="loading-box">
          <Loader className="spinning" size={32} />
          <span>Loading job details...</span>
        </div>
      )}

      {job && (
        <div className="job-details">
          <div className="job-header">
            <div>
              <h3>Job {job.job_id.slice(0, 16)}...</h3>
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
                className={getProgressBarClass(job)}
                style={{ width: `${getProgressStats(job).percentage}%` }}
              ></div>
            </div>
            <div className="progress-stats">
              <span className="stat-completed">{getProgressStats(job).completed} completed</span>
              <span className="stat-processing">{getProgressStats(job).processing} processing</span>
              {getProgressStats(job).failed > 0 && (
                <span className="stat-failed">{getProgressStats(job).failed} failed</span>
              )}
              <span className="stat-total">{getProgressStats(job).total} total</span>
            </div>
          </div>

          <div className="items-section">
            <h4>Items ({job.items.length})</h4>
            <div className="items-list">
              {job.items.map((item) => (
                <div key={item.item_id} className="item-card">
                  <div className="item-header">
                    <div>
                      <div className="item-filename">
                        {item.filename}
                        {item.scene_type && (
                          <span className="item-scene-tag">
                            {item.scene_type.charAt(0).toUpperCase() + item.scene_type.slice(1)}
                          </span>
                        )}
                        {item.scene_index != null && (
                          <span className="item-scene-index">#{item.scene_index + 1}</span>
                        )}
                      </div>
                    </div>
                    {getStatusBadge(item.status)}
                  </div>

                  {item.error_message && (
                    <div className="item-error">
                      <AlertTriangle size={16} />
                      <span>{item.error_message}</span>
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
