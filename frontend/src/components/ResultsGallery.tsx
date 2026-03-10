import { useState, useEffect, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import {
  Image as ImageIcon,
  Download,
  ExternalLink,
  Loader,
  AlertCircle,
  Archive,
  X,
  Monitor,
  Check,
  Copy,
  FileText,
  Crown,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import { api } from '../api';
import type { Job, JobItem } from '../types';

function ResultImage({ itemId, onClick }: { itemId: string; onClick?: () => void }) {
  const { t } = useTranslation();
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
        <p>{t('results.previewUnavailable')}</p>
      </div>
    );
  }

  return (
    <img
      className="result-image"
      src={src}
      alt={t('results.processedResult')}
      onError={() => setError(true)}
      onClick={onClick}
      style={onClick ? { cursor: 'pointer' } : undefined}
    />
  );
}

// ── Lightbox ─────────────────────────────────────────────────────

function Lightbox({
  items,
  startIndex,
  onClose,
}: {
  items: JobItem[];
  startIndex: number;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const [index, setIndex] = useState(startIndex);
  const [src, setSrc] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const item = items[index];
  const hasNext = index < items.length - 1;
  const hasPrev = index > 0;

  const goNext = useCallback(() => { if (hasNext) setIndex(i => i + 1); }, [hasNext]);
  const goPrev = useCallback(() => { if (hasPrev) setIndex(i => i - 1); }, [hasPrev]);

  // Fetch image URL when index changes
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setSrc(null);
    api.getDownloadUrl(item.item_id, 'outputs')
      .then(url => { if (!cancelled) setSrc(url); })
      .catch(() => { if (!cancelled) setSrc(null); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [item.item_id]);

  // Keyboard navigation
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
      else if (e.key === 'ArrowRight' || e.key === 'ArrowDown') goNext();
      else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') goPrev();
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [onClose, goNext, goPrev]);

  // Prevent body scroll while lightbox is open
  useEffect(() => {
    document.body.style.overflow = 'hidden';
    return () => { document.body.style.overflow = ''; };
  }, []);

  const handleDownload = async () => {
    try {
      const url = await api.getDownloadUrl(item.item_id, 'outputs');
      const link = document.createElement('a');
      link.href = url;
      link.download = item.seo_filename || item.filename;
      link.click();
    } catch { /* ignore */ }
  };

  return (
    <div className="lightbox-overlay" onClick={onClose}>
      <div className="lightbox-content" onClick={e => e.stopPropagation()}>
        {/* Close button */}
        <button className="lightbox-close" onClick={onClose}>
          <X size={20} />
        </button>

        {/* Navigation */}
        {hasPrev && (
          <button className="lightbox-nav lightbox-prev" onClick={goPrev}>
            <ChevronLeft size={32} />
          </button>
        )}
        {hasNext && (
          <button className="lightbox-nav lightbox-next" onClick={goNext}>
            <ChevronRight size={32} />
          </button>
        )}

        {/* Image */}
        <div className="lightbox-image-container">
          {loading ? (
            <Loader className="spinning" size={48} />
          ) : src ? (
            <img className="lightbox-image" src={src} alt={item.seo_alt_text || item.filename} />
          ) : (
            <div className="lightbox-error">
              <ImageIcon size={48} />
              <p>{t('results.previewUnavailable')}</p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="lightbox-footer">
          <div className="lightbox-info">
            <span className="lightbox-filename">{item.filename}</span>
            {item.scene_type && (
              <span className="result-scene-tag">{item.scene_type.charAt(0).toUpperCase() + item.scene_type.slice(1)}</span>
            )}
            {item.angle_type && (
              <span className="item-angle-tag">{item.angle_type.split('-').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')}</span>
            )}
            <span className="lightbox-counter">{index + 1} / {items.length}</span>
          </div>
          <button className="button-secondary button-sm" onClick={handleDownload}>
            <Download size={14} />
            {t('common.download')}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Main Component ───────────────────────────────────────────────

interface Props {
  jobId: string | null;
  tokenBalance?: number | null;
}

interface ExportPreset {
  key: string;
  name: string;
  width: number;
  height: number;
}

export default function ResultsGallery({ jobId, tokenBalance }: Props) {
  const { t } = useTranslation();
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const [showFormatPicker, setShowFormatPicker] = useState(false);
  const [selectedFormats, setSelectedFormats] = useState<Set<string>>(new Set());
  const [formatExportStatus, setFormatExportStatus] = useState<'idle' | 'loading' | 'queued'>('idle');
  const [selectedJobId, setSelectedJobId] = useState<string | null>(jobId);
  const [lightboxIndex, setLightboxIndex] = useState<number | null>(null);

  // Update selectedJobId when jobId prop changes (new job created)
  useEffect(() => {
    if (jobId) setSelectedJobId(jobId);
  }, [jobId]);

  const { data: presets } = useQuery<ExportPreset[]>({
    queryKey: ['export-presets'],
    queryFn: () => api.getExportPresets(),
    staleTime: Infinity,
  });

  // Fetch all recent jobs
  const { data: jobsData } = useQuery({
    queryKey: ['all-jobs'],
    queryFn: () => api.listJobs(20),
  });

  const recentJobs = jobsData?.jobs?.filter(
    (j: Job) => j.items?.some((i) => i.status === 'completed')
  ) || [];

  const { data: job, isLoading, error } = useQuery<Job>({
    queryKey: ['job-results', selectedJobId],
    queryFn: () => api.getJob(selectedJobId!),
    enabled: !!selectedJobId,
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
      setDownloadError(t('results.downloadFailed'));
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
      setDownloadError(t('results.exportFailed'));
    }
  };

  const toggleFormat = (key: string) => {
    setSelectedFormats((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const handleFormatExport = async () => {
    if (!job || selectedFormats.size === 0) return;
    try {
      setFormatExportStatus('loading');
      setDownloadError(null);
      await api.requestFormatExport(job.job_id, Array.from(selectedFormats));
      setFormatExportStatus('queued');
      setShowFormatPicker(false);
      setSelectedFormats(new Set());
    } catch {
      setDownloadError(t('results.exportFailed'));
      setFormatExportStatus('idle');
    }
  };

  if (!selectedJobId && recentJobs.length === 0) {
    return (
      <div className="results-gallery">
        <div className="section-header">
          <h2>{t('results.title')}</h2>
          <p>{t('results.subtitle')}</p>
        </div>
        <div className="empty-state">
          <ImageIcon size={48} />
          <h3>{t('results.noResults')}</h3>
          <p>{t('results.noResultsHint')}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="results-gallery">
      <div className="section-header">
        <h2>{t('results.title')}</h2>
        <p>{t('results.subtitle')}</p>
      </div>

      {recentJobs.length > 1 && (
        <div className="results-job-tabs">
          {recentJobs.map((j: Job) => (
            <button
              key={j.job_id}
              className={`results-job-tab ${selectedJobId === j.job_id ? 'active' : ''}`}
              onClick={() => setSelectedJobId(j.job_id)}
            >
              <span className="results-job-tab-name">
                {j.items?.[0]?.filename || j.job_id.slice(4, 16)}
              </span>
              <span className="results-job-tab-count">
                {j.items?.filter((i) => i.status === 'completed').length} image{j.items?.filter((i) => i.status === 'completed').length !== 1 ? 's' : ''}
              </span>
            </button>
          ))}
        </div>
      )}

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
          <span>{error instanceof Error ? error.message : t('results.loadFailed')}</span>
        </div>
      )}

      {isLoading && (
        <div className="loading-box">
          <Loader className="spinning" size={32} />
          <span>{t('results.loadingResults')}</span>
        </div>
      )}

      {job && !isLoading && completedItems.length === 0 && (
        <div className="empty-state">
          <ImageIcon size={48} />
          <h3>{t('results.noCompleted')}</h3>
          <p>
            {t('results.beingProcessed', { count: job.items.length })}
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
                  {t('results.readyForDownload', { count: completedItems.length })}
                </span>
              </div>
              <div style={{ display: 'flex', gap: '0.5rem' }}>
                <button className="button-secondary button-sm" onClick={() => setShowFormatPicker(!showFormatPicker)}>
                  <Monitor size={16} />
                  {t('results.exportFormats', { defaultValue: 'Export for Platform' })}
                </button>
                <button className="button-primary button-sm" onClick={handleDownloadZip}>
                  <Archive size={16} />
                  {t('results.downloadZip')}
                </button>
              </div>
            </div>
          )}

          {showFormatPicker && presets && (
            <div className="format-picker">
              <div className="format-picker-header">
                <h4>{t('results.selectPlatforms', { defaultValue: 'Select platforms to export for' })}</h4>
                <button className="button-icon" onClick={() => setShowFormatPicker(false)}>
                  <X size={16} />
                </button>
              </div>
              <div className="format-grid">
                {presets.map((preset) => (
                  <label key={preset.key} className={`format-option ${selectedFormats.has(preset.key) ? 'selected' : ''}`}>
                    <input
                      type="checkbox"
                      checked={selectedFormats.has(preset.key)}
                      onChange={() => toggleFormat(preset.key)}
                    />
                    <div className="format-option-info">
                      <span className="format-name">{preset.name}</span>
                      <span className="format-size">{preset.width} × {preset.height}</span>
                    </div>
                    {selectedFormats.has(preset.key) && <Check size={16} className="format-check" />}
                  </label>
                ))}
              </div>
              <div className="format-picker-actions">
                <button
                  className="button-primary button-sm"
                  disabled={selectedFormats.size === 0 || formatExportStatus === 'loading'}
                  onClick={handleFormatExport}
                >
                  {formatExportStatus === 'loading' ? (
                    <><Loader className="spinning" size={14} /> {t('common.processing', { defaultValue: 'Processing...' })}</>
                  ) : (
                    <><Download size={14} /> {t('results.exportSelected', { defaultValue: `Export ${selectedFormats.size} format(s)` })}</>
                  )}
                </button>
              </div>
              {formatExportStatus === 'queued' && (
                <div className="success-box" style={{ marginTop: '0.5rem' }}>
                  <Check size={16} />
                  <span>{t('results.formatExportQueued', { defaultValue: 'Export queued! Your resized images will be ready shortly.' })}</span>
                </div>
              )}
            </div>
          )}

          {tokenBalance !== undefined && tokenBalance !== null && tokenBalance <= 0 && (
            <div className="watermark-upgrade-banner">
              <Crown size={18} />
              <div>
                <strong>{t('results.watermarkNotice', { defaultValue: 'Preview images are watermarked' })}</strong>
                <span>{t('results.watermarkUpgrade', { defaultValue: 'Purchase tokens or subscribe to get clean, unwatermarked images.' })}</span>
              </div>
            </div>
          )}

          <div className="results-grid">
            {completedItems.map((item, idx) => (
              <div key={item.item_id} className="result-card">
                <div className="result-preview" onClick={() => setLightboxIndex(idx)}>
                  <ResultImage itemId={item.item_id} onClick={() => setLightboxIndex(idx)} />
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

                  {(item.seo_alt_text || item.seo_filename) && (
                    <div className="seo-metadata">
                      {item.seo_alt_text && (
                        <div className="seo-field">
                          <FileText size={12} />
                          <span className="seo-label">{t('results.altText', { defaultValue: 'Alt text' })}:</span>
                          <span className="seo-value">{item.seo_alt_text}</span>
                          <button
                            className="button-icon seo-copy"
                            title={t('common.copy', { defaultValue: 'Copy' })}
                            onClick={() => navigator.clipboard.writeText(item.seo_alt_text!)}
                          >
                            <Copy size={12} />
                          </button>
                        </div>
                      )}
                      {item.seo_filename && (
                        <div className="seo-field">
                          <FileText size={12} />
                          <span className="seo-label">{t('results.seoFilename', { defaultValue: 'SEO filename' })}:</span>
                          <span className="seo-value">{item.seo_filename}</span>
                          <button
                            className="button-icon seo-copy"
                            title={t('common.copy', { defaultValue: 'Copy' })}
                            onClick={() => navigator.clipboard.writeText(item.seo_filename!)}
                          >
                            <Copy size={12} />
                          </button>
                        </div>
                      )}
                    </div>
                  )}

                  <div className="result-actions">
                    <button
                      className="button-secondary button-sm"
                      onClick={() => setLightboxIndex(idx)}
                    >
                      <ExternalLink size={14} />
                      {t('common.view')}
                    </button>
                    <button
                      className="button-secondary button-sm"
                      onClick={() => handleDownloadItem(item.item_id, item.seo_filename || item.filename)}
                    >
                      <Download size={14} />
                      {t('common.download')}
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>

          <div className="gallery-summary">
            <p>
              {t('results.completedOf', { completed: completedItems.length, total: job.items.length })}
            </p>
          </div>

          {/* Lightbox */}
          {lightboxIndex !== null && (
            <Lightbox
              items={completedItems}
              startIndex={lightboxIndex}
              onClose={() => setLightboxIndex(null)}
            />
          )}
        </>
      )}
    </div>
  );
}
