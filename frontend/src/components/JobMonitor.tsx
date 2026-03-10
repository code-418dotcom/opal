import { useEffect, useState, useRef } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import {
  RefreshCw, Clock, CheckCircle, XCircle, Loader, AlertTriangle,
  Copy, Check, Scissors, Sparkles, ArrowUpFromDot, Timer, Ban,
  Download, History,
} from 'lucide-react';
import { api } from '../api';
import type { Job } from '../types';

interface Props {
  jobId: string | null;
  onSelectJob?: (jobId: string) => void;
}

const STATUS_WEIGHT: Record<string, number> = {
  created: 0,
  uploaded: 15,
  processing: 50,
  completed: 100,
  failed: 100,
};

function formatElapsed(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  if (m === 0) return `${s}s`;
  return `${m}m ${s.toString().padStart(2, '0')}s`;
}

function formatTimeAgo(iso: string): string {
  const diff = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (diff < 60) return 'just now';
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

function useElapsedTimer(startIso: string | undefined, running: boolean) {
  const [elapsed, setElapsed] = useState(0);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (intervalRef.current) clearInterval(intervalRef.current);
    if (!startIso || !running) return;

    const start = new Date(startIso).getTime();
    const tick = () => setElapsed(Math.floor((Date.now() - start) / 1000));
    tick();
    intervalRef.current = setInterval(tick, 1000);
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, [startIso, running]);

  // Freeze elapsed when job finishes
  useEffect(() => {
    if (!running && startIso) {
      const start = new Date(startIso).getTime();
      setElapsed(Math.floor((Date.now() - start) / 1000));
    }
  }, [running, startIso]);

  return elapsed;
}

function getStepExplanation(
  job: Job,
  t: (key: string, fallback: string) => string,
): { icon: typeof Scissors; text: string } | null {
  const opts = job.processing_options;
  if (!opts) return null;

  const isTerminal = job.status === 'completed' || job.status === 'failed' || job.status === 'partial';
  if (isTerminal) return null;

  if (job.status === 'created') {
    return { icon: Clock, text: t('monitor.step.queued', 'Waiting in queue...') };
  }

  // Determine current step from item statuses
  const hasUploading = job.items.some(i => i.status === 'uploaded');
  const hasProcessing = job.items.some(i => i.status === 'processing');
  const completedCount = job.items.filter(i => i.status === 'completed').length;
  const total = job.items.length;

  if (hasUploading && !hasProcessing && completedCount === 0) {
    return { icon: Clock, text: t('monitor.step.uploading', 'Uploading images to storage...') };
  }

  // Infer pipeline stage from progress ratio
  if (hasProcessing || completedCount < total) {
    const progress = completedCount / total;

    if (opts.remove_background && progress < 0.33) {
      return { icon: Scissors, text: t('monitor.step.removingBg', 'Removing backgrounds — isolating your products...') };
    }
    if (opts.generate_scene && progress < 0.66) {
      return { icon: Sparkles, text: t('monitor.step.generatingScene', 'Generating AI scenes — compositing your products into professional settings...') };
    }
    if (opts.upscale) {
      return { icon: ArrowUpFromDot, text: t('monitor.step.upscaling', 'HD upscaling — sharpening images to high resolution...') };
    }

    // Fallback if only some steps enabled
    if (opts.remove_background) {
      return { icon: Scissors, text: t('monitor.step.removingBg', 'Removing backgrounds — isolating your products...') };
    }
    if (opts.generate_scene) {
      return { icon: Sparkles, text: t('monitor.step.generatingScene', 'Generating AI scenes — compositing your products into professional settings...') };
    }
  }

  return { icon: Loader, text: t('monitor.step.processing', 'Processing your images...') };
}

function DownloadButton({ itemId }: { itemId: string }) {
  const [downloading, setDownloading] = useState(false);

  const handleDownload = async () => {
    setDownloading(true);
    try {
      const url = await api.getDownloadUrl(itemId);
      window.open(url, '_blank');
    } catch (err) {
      console.error('Download failed:', err);
    } finally {
      setDownloading(false);
    }
  };

  return (
    <button className="button-icon button-sm" onClick={handleDownload} disabled={downloading} title="Download">
      <Download size={14} className={downloading ? 'spinning' : ''} />
    </button>
  );
}

export default function JobMonitor({ jobId, onSelectJob }: Props) {
  const { t } = useTranslation();
  const [copied, setCopied] = useState(false);
  const [cancelling, setCancelling] = useState(false);
  const [cancelResult, setCancelResult] = useState<{ cancelled_items: number; refunded_tokens: number } | null>(null);
  const [showHistory, setShowHistory] = useState(false);

  const copyJobId = (id: string) => {
    navigator.clipboard.writeText(id).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  };

  const handleCancel = async () => {
    if (!jobId || cancelling) return;
    setCancelling(true);
    try {
      const result = await api.cancelJob(jobId);
      setCancelResult(result);
      refetch();
    } catch (err) {
      console.error('Cancel failed:', err);
    } finally {
      setCancelling(false);
    }
  };

  const { data: job, isLoading, error, refetch } = useQuery<Job>({
    queryKey: ['job', jobId],
    queryFn: () => api.getJob(jobId!),
    enabled: !!jobId,
    refetchInterval: 3000,
  });

  // Job history — fetch recent jobs
  const { data: historyData } = useQuery({
    queryKey: ['job-history'],
    queryFn: () => api.listJobs(10),
    refetchInterval: 10000,
  });
  const jobHistory = historyData?.jobs ?? [];

  const isRunning = !!job && job.status !== 'completed' && job.status !== 'failed' && job.status !== 'partial';
  const elapsed = useElapsedTimer(job?.created_at, isRunning);

  const getStatusBadge = (status: string) => {
    const badges: Record<string, { icon: typeof Clock; cls: string; label: string }> = {
      created: { icon: Clock, cls: 'badge-default', label: t('monitor.status.queued') },
      uploaded: { icon: Clock, cls: 'badge-default', label: t('monitor.status.uploaded') },
      processing: { icon: Loader, cls: 'badge-processing', label: t('monitor.status.processing') },
      completed: { icon: CheckCircle, cls: 'badge-success', label: t('monitor.status.completed') },
      failed: { icon: XCircle, cls: 'badge-error', label: t('monitor.status.failed') },
      partial: { icon: AlertTriangle, cls: 'badge-warning', label: t('monitor.status.partial') },
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
          <h2>{t('monitor.title')}</h2>
          <p>{t('monitor.subtitle')}</p>
        </div>

        {/* Show history when no active job */}
        {jobHistory.length > 0 ? (
          <div className="job-history-section">
            <h4><History size={16} /> {t('monitor.recentJobs', 'Recent Jobs')}</h4>
            <div className="job-history-list">
              {jobHistory.map((j: { job_id: string; status: string; created_at?: string }) => (
                <button
                  key={j.job_id}
                  className="job-history-item"
                  onClick={() => onSelectJob?.(j.job_id)}
                >
                  <code className="job-history-id">{j.job_id.slice(4, 16)}...</code>
                  {getStatusBadge(j.status)}
                  {j.created_at && <span className="job-history-time">{formatTimeAgo(j.created_at)}</span>}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="empty-state">
            <Loader size={48} />
            <h3>{t('monitor.noActiveJob')}</h3>
            <p>{t('monitor.noActiveJobHint')}</p>
          </div>
        )}
      </div>
    );
  }

  const step = job ? getStepExplanation(job, t) : null;

  return (
    <div className="job-monitor">
      <div className="section-header">
        <div className="section-header-row">
          <div>
            <h2>{t('monitor.title')}</h2>
            <p>{t('monitor.trackingSubtitle')}</p>
          </div>
          <div className="monitor-actions">
            {isRunning && (
              <button
                className="button-danger"
                onClick={handleCancel}
                disabled={cancelling}
              >
                <Ban size={16} className={cancelling ? 'spinning' : ''} />
                {t('monitor.cancelJob', 'Cancel Job')}
              </button>
            )}
            <button
              className="button-secondary button-sm"
              onClick={() => setShowHistory(h => !h)}
            >
              <History size={16} />
              {t('monitor.history', 'History')}
            </button>
            <button
              className="button-secondary"
              onClick={() => refetch()}
              disabled={isLoading}
            >
              <RefreshCw size={16} className={isLoading ? 'spinning' : ''} />
              {t('common.refresh')}
            </button>
          </div>
        </div>
      </div>

      {/* Collapsible history panel */}
      {showHistory && jobHistory.length > 0 && (
        <div className="job-history-section job-history-inline">
          <div className="job-history-list">
            {jobHistory.map((j: { job_id: string; status: string; created_at?: string }) => (
              <button
                key={j.job_id}
                className={`job-history-item ${j.job_id === jobId ? 'job-history-active' : ''}`}
                onClick={() => { onSelectJob?.(j.job_id); setShowHistory(false); }}
              >
                <code className="job-history-id">{j.job_id.slice(4, 16)}...</code>
                {getStatusBadge(j.status)}
                {j.created_at && <span className="job-history-time">{formatTimeAgo(j.created_at)}</span>}
              </button>
            ))}
          </div>
        </div>
      )}

      {error && (
        <div className="error-box">
          <XCircle size={20} />
          <span>{error instanceof Error ? error.message : t('monitor.loadFailed')}</span>
        </div>
      )}

      {isLoading && !job && (
        <div className="loading-box">
          <Loader className="spinning" size={32} />
          <span>{t('monitor.loadingJob')}</span>
        </div>
      )}

      {job && (
        <div className="job-details">
          <div className="job-id-row">
            <code className="job-id-value">{job.job_id}</code>
            <button
              className="job-id-copy"
              onClick={() => copyJobId(job.job_id)}
              title={t('monitor.copyJobId', 'Copy Job ID')}
            >
              {copied ? <Check size={14} /> : <Copy size={14} />}
            </button>
            {getStatusBadge(job.status)}
          </div>

          {/* Timer + current step */}
          <div className="job-timer-row">
            <div className="job-timer">
              <Timer size={16} className={isRunning ? 'job-timer-pulse' : ''} />
              <span className="job-timer-value">{formatElapsed(elapsed)}</span>
            </div>
            {step && (
              <div className="job-step-explanation">
                <step.icon size={16} className={isRunning ? 'spinning' : ''} />
                <span>{step.text}</span>
              </div>
            )}
            {!isRunning && job.status === 'completed' && (
              <div className="job-step-explanation job-step-done">
                <CheckCircle size={16} />
                <span>{t('monitor.step.done', 'All images processed successfully!')}</span>
              </div>
            )}
            {!isRunning && job.status === 'failed' && (
              <div className="job-step-explanation job-step-error">
                <XCircle size={16} />
                <span>{t('monitor.step.failed', 'Processing failed. Check individual items for details.')}</span>
              </div>
            )}
            {!isRunning && job.status === 'partial' && (
              <div className="job-step-explanation job-step-warning">
                <AlertTriangle size={16} />
                <span>{t('monitor.step.partial', 'Some images completed, others failed. Check items below.')}</span>
              </div>
            )}
          </div>

          <div className="progress-section">
            <div className="progress-header">
              <span>{t('monitor.overallProgress')}</span>
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
              <span className="stat-completed">{getProgressStats(job).completed} {t('monitor.completed')}</span>
              <span className="stat-processing">{getProgressStats(job).processing} {t('monitor.processing')}</span>
              {getProgressStats(job).failed > 0 && (
                <span className="stat-failed">{getProgressStats(job).failed} {t('monitor.failed')}</span>
              )}
              <span className="stat-total">{getProgressStats(job).total} {t('monitor.total')}</span>
            </div>
          </div>

          {cancelResult && cancelResult.refunded_tokens > 0 && (
            <div className="refund-notice">
              <CheckCircle size={16} />
              <span>
                {t('monitor.refunded', {
                  tokens: cancelResult.refunded_tokens,
                  items: cancelResult.cancelled_items,
                  defaultValue: '{{tokens}} token(s) refunded for {{items}} cancelled item(s)',
                })}
              </span>
            </div>
          )}

          <div className="items-section">
            <h4>{t('monitor.items')} ({job.items.length})</h4>
            <div className="items-list">
              {(() => {
                // Group items by source filename
                const groups = new Map<string, typeof job.items>();
                for (const item of job.items) {
                  const key = item.filename;
                  if (!groups.has(key)) groups.set(key, []);
                  groups.get(key)!.push(item);
                }

                return Array.from(groups.entries()).map(([filename, items]) => {
                  const isSingle = items.length === 1;
                  return (
                    <div key={filename} className="item-group">
                      {!isSingle && (
                        <div className="item-group-header">
                          <span className="item-filename">{filename}</span>
                          <span className="item-group-count">{items.length} {t('monitor.variants', 'variants')}</span>
                        </div>
                      )}
                      {items.map((item) => (
                        <div key={item.item_id} className={`item-card ${!isSingle ? 'item-card-nested' : ''}`}>
                          <div className="item-header">
                            <div className="item-filename">
                              {isSingle && filename}
                              {!isSingle && (
                                <span className="item-variant-label">
                                  {item.angle_type && (
                                    <span className="item-angle-tag">
                                      {item.angle_type.split('-').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')}
                                    </span>
                                  )}
                                  {item.scene_type && (
                                    <span className="item-scene-tag">
                                      {item.scene_type.charAt(0).toUpperCase() + item.scene_type.slice(1)}
                                    </span>
                                  )}
                                  {item.scene_index != null && (
                                    <span className="item-scene-index">Scene #{item.scene_index + 1}</span>
                                  )}
                                  {!item.angle_type && !item.scene_type && item.scene_index == null && filename}
                                </span>
                              )}
                              {isSingle && item.angle_type && (
                                <span className="item-angle-tag">
                                  {item.angle_type.split('-').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')}
                                </span>
                              )}
                              {isSingle && item.scene_type && (
                                <span className="item-scene-tag">
                                  {item.scene_type.charAt(0).toUpperCase() + item.scene_type.slice(1)}
                                </span>
                              )}
                              {isSingle && item.scene_index != null && (
                                <span className="item-scene-index">#{item.scene_index + 1}</span>
                              )}
                            </div>
                            <div className="item-actions">
                              {item.status === 'completed' && item.output_blob_path && (
                                <DownloadButton itemId={item.item_id} />
                              )}
                              {getStatusBadge(item.status)}
                            </div>
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
                  );
                });
              })()}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
