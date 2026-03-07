import { useState, useEffect } from 'react';
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
} from 'lucide-react';
import { api } from '../api';
import type { Job } from '../types';

function ResultImage({ itemId }: { itemId: string }) {
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
    <img className="result-image" src={src} alt={t('results.processedResult')} onError={() => setError(true)} />
  );
}

interface Props {
  jobId: string | null;
}

interface ExportPreset {
  key: string;
  name: string;
  width: number;
  height: number;
}

export default function ResultsGallery({ jobId }: Props) {
  const { t } = useTranslation();
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const [showFormatPicker, setShowFormatPicker] = useState(false);
  const [selectedFormats, setSelectedFormats] = useState<Set<string>>(new Set());
  const [formatExportStatus, setFormatExportStatus] = useState<'idle' | 'loading' | 'queued'>('idle');

  const { data: presets } = useQuery<ExportPreset[]>({
    queryKey: ['export-presets'],
    queryFn: () => api.getExportPresets(),
    staleTime: Infinity,
  });

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
      setDownloadError(t('results.downloadFailed'));
    }
  };

  const handleViewItem = async (itemId: string) => {
    try {
      setDownloadError(null);
      const url = await api.getDownloadUrl(itemId, 'outputs');
      window.open(url, '_blank');
    } catch {
      setDownloadError(t('results.previewFailed'));
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

  if (!jobId) {
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
                      {t('common.view')}
                    </button>
                    <button
                      className="button-secondary button-sm"
                      onClick={() => handleDownloadItem(item.item_id, item.filename)}
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
        </>
      )}
    </div>
  );
}
