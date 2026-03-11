import { useState, useRef, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useQuery } from '@tanstack/react-query';
import { Upload, X, Loader, CheckCircle, AlertCircle, Minus, Plus, ChevronDown, ChevronUp, Image as ImageIcon, RotateCw } from 'lucide-react';
import { api } from '../api';
import ProcessingOptions, { type ProcessingOptionsType } from './ProcessingOptions';
import HelpTooltip from './HelpTooltip';
import CostPreview from './CostPreview';

interface Props {
  onJobCreated: (jobId: string) => void;
}

interface FileWithStatus {
  file: File;
  status: 'pending' | 'uploading' | 'completed' | 'failed';
  error?: string;
}

export default function UploadSection({ onJobCreated }: Props) {
  const { t } = useTranslation();
  const [files, setFiles] = useState<FileWithStatus[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [processingOptions, setProcessingOptions] = useState<ProcessingOptionsType>({
    remove_background: true,
    generate_scene: true,
    upscale: false,
  });
  const [sceneCount, setSceneCount] = useState(1);
  const [selectedBrandId, setSelectedBrandId] = useState('');
  const [selectedTemplateIds, setSelectedTemplateIds] = useState<string[]>([]);
  const [useSavedBackground, setUseSavedBackground] = useState(false);
  const [showTemplatePicker, setShowTemplatePicker] = useState(false);
  const [selectedAngles, setSelectedAngles] = useState<string[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const ANGLE_OPTIONS = [
    { value: 'eye-level', label: t('upload.angleEyeLevel', 'Eye Level'), desc: t('upload.angleEyeLevelDesc', 'Balanced, even lighting') },
    { value: 'low-angle', label: t('upload.angleLowAngle', 'Low Angle'), desc: t('upload.angleLowAngleDesc', 'Dramatic, bold presence') },
    { value: 'overhead', label: t('upload.angleOverhead', 'Overhead'), desc: t('upload.angleOverheadDesc', 'Flat-lay, top-down') },
    { value: 'side-lit', label: t('upload.angleSideLit', 'Side Lit'), desc: t('upload.angleSideLitDesc', 'Deep shadows, texture') },
    { value: 'backlit', label: t('upload.angleBacklit', 'Backlit'), desc: t('upload.angleBacklitDesc', 'Soft glow, rim light') },
    { value: 'golden', label: t('upload.angleGolden', 'Golden Hour'), desc: t('upload.angleGoldenDesc', 'Warm amber tones') },
  ];

  const { data: brandProfiles = [] } = useQuery({
    queryKey: ['brand-profiles'],
    queryFn: () => api.listBrandProfiles(),
  });

  const { data: sceneTemplates = [] } = useQuery({
    queryKey: ['scene-templates', selectedBrandId],
    queryFn: () => api.listSceneTemplates(selectedBrandId || undefined),
    enabled: processingOptions.generate_scene,
  });

  // Auto-populate scene count from brand profile
  useEffect(() => {
    if (!selectedBrandId) return;
    const bp = brandProfiles.find(p => p.id === selectedBrandId);
    if (bp?.default_scene_count && bp.default_scene_count > 1) {
      setSceneCount(bp.default_scene_count);
    }
  }, [selectedBrandId, brandProfiles]);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    setUploadError(null);

    const droppedFiles = Array.from(e.dataTransfer.files).filter(
      (file) => file.type.startsWith('image/')
    );

    addFiles(droppedFiles);
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setUploadError(null);
      addFiles(Array.from(e.target.files));
    }
  };

  const addFiles = (newFiles: File[]) => {
    const filesWithStatus: FileWithStatus[] = newFiles.map((file) => ({
      file,
      status: 'pending',
    }));
    setFiles((prev) => [...prev, ...filesWithStatus]);
  };

  const removeFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const uploadFiles = async () => {
    if (files.length === 0) return;

    setIsUploading(true);
    setUploadError(null);

    try {
      const filenames = files.map((f) => f.file.name);
      const hasSceneOptions = sceneCount > 1 || selectedTemplateIds.length > 0 || selectedAngles.length > 0;
      const sceneOptions = hasSceneOptions ? {
        scene_count: sceneCount,
        scene_template_ids: selectedTemplateIds.length > 0 ? selectedTemplateIds : undefined,
        use_saved_background: selectedTemplateIds.length > 0 ? useSavedBackground : undefined,
        angle_types: selectedAngles.length > 0 ? selectedAngles : undefined,
      } : undefined;
      const job = await api.createJob(
        filenames,
        processingOptions,
        sceneOptions,
        selectedBrandId || undefined,
      );

      onJobCreated(job.job_id);

      const seenFilenames = new Set<string>();

      for (let i = 0; i < files.length; i++) {
        const fileItem = files[i];
        const item = job.items.find(
          (it) => it.filename === fileItem.file.name && !seenFilenames.has(it.item_id)
        );
        if (!item) continue;
        seenFilenames.add(item.item_id);

        try {
          setFiles((prev) =>
            prev.map((f, idx) => (idx === i ? { ...f, status: 'uploading' } : f))
          );

          await api.uploadDirect(job.job_id, item.item_id, fileItem.file, processingOptions);

          setFiles((prev) =>
            prev.map((f, idx) => (idx === i ? { ...f, status: 'completed' } : f))
          );
        } catch (error) {
          setFiles((prev) =>
            prev.map((f, idx) =>
              idx === i
                ? {
                    ...f,
                    status: 'failed',
                    error: error instanceof Error ? error.message : t('upload.uploadFailed'),
                  }
                : f
            )
          );
        }
      }

      await api.enqueueJob(job.job_id);
    } catch (error) {
      setUploadError(error instanceof Error ? error.message : t('upload.createJobFailed'));
    } finally {
      setIsUploading(false);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'uploading':
        return <Loader className="status-icon spinning" size={16} />;
      case 'completed':
        return <CheckCircle className="status-icon success" size={16} />;
      case 'failed':
        return <AlertCircle className="status-icon error" size={16} />;
      default:
        return null;
    }
  };

  const adjustSceneCount = (delta: number) => {
    setSceneCount((prev) => Math.max(1, Math.min(10, prev + delta)));
  };

  return (
    <div className="upload-section">
      <div className="section-header">
        <h2>{t('upload.title')}</h2>
        <p>{t('upload.subtitle')}</p>
      </div>

      {uploadError && (
        <div className="error-box" style={{ marginBottom: '1rem' }}>
          <AlertCircle size={20} />
          <span>{uploadError}</span>
          <button
            className="button-icon"
            onClick={() => setUploadError(null)}
            style={{ marginLeft: 'auto' }}
          >
            <X size={16} />
          </button>
        </div>
      )}

      <div
        className={`drop-zone ${isDragging ? 'dragging' : ''}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
      >
        <Upload size={48} />
        <h3>{t('upload.dragDrop')}</h3>
        <p>{t('upload.orBrowse')}</p>
        <span className="hint">{t('upload.formats')}</span>
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          multiple
          onChange={handleFileSelect}
          style={{ display: 'none' }}
        />
      </div>

      {files.length > 0 && (
        <div className="file-list">
          <div className="file-list-header">
            <h3>{t('upload.imagesSelected', { count: files.length })}</h3>
            {!isUploading && (
              <button className="button-secondary" onClick={() => setFiles([])}>
                {t('common.clearAll')}
              </button>
            )}
          </div>

          {files.map((fileItem, index) => (
            <div key={index} className="file-item">
              <div className="file-info">
                <div className="file-name">{fileItem.file.name}</div>
                <div className="file-meta">
                  {(fileItem.file.size / 1024 / 1024).toFixed(2)} MB
                </div>
              </div>
              <div className="file-status">
                {getStatusIcon(fileItem.status)}
                {fileItem.error && <span className="error-text">{fileItem.error}</span>}
              </div>
              {!isUploading && fileItem.status === 'pending' && (
                <button
                  className="button-icon"
                  onClick={(e) => {
                    e.stopPropagation();
                    removeFile(index);
                  }}
                >
                  <X size={16} />
                </button>
              )}
            </div>
          ))}
        </div>
      )}

      {files.length > 0 && !isUploading && (
        <>
          {brandProfiles.length > 0 && (
            <div className="brand-selector">
              <label className="form-label">
                {t('upload.brandProfile')}
                <HelpTooltip text={t('help.brandProfile', 'Select a brand profile to apply consistent colors, mood, and style to all generated scenes.')} />
              </label>
              <select
                className="input"
                value={selectedBrandId}
                onChange={e => {
                  setSelectedBrandId(e.target.value);
                  setSelectedTemplateIds([]);
                }}
              >
                <option value="">{t('upload.noneDefault')}</option>
                {brandProfiles.map(p => (
                  <option key={p.id} value={p.id}>{p.name}</option>
                ))}
              </select>
            </div>
          )}

          <ProcessingOptions
            options={processingOptions}
            onChange={setProcessingOptions}
            disabled={isUploading}
          />

          {processingOptions.generate_scene && (
            <>
            <div className="scene-count-section">
              <label className="scene-count-label">
                {t('upload.scenesPerImage')}
                <HelpTooltip text={t('help.scenesPerImage', 'Generate multiple different scene variations for each product image. More scenes = more options to choose from.')} />
              </label>
              <div className="scene-count-stepper">
                <button
                  className="stepper-btn"
                  onClick={() => adjustSceneCount(-1)}
                  disabled={sceneCount <= 1}
                >
                  <Minus size={16} />
                </button>
                <span className="stepper-value">{sceneCount}</span>
                <button
                  className="stepper-btn"
                  onClick={() => adjustSceneCount(1)}
                  disabled={sceneCount >= 10}
                >
                  <Plus size={16} />
                </button>
              </div>
              {sceneCount > 1 && (
                <span className="scene-count-hint">
                  {t('upload.sceneVariations', { count: sceneCount })}
                </span>
              )}
            </div>

            <div className="angle-picker-section">
              <div className="angle-picker-header">
                <RotateCw size={16} />
                <label className="form-label" style={{ margin: 0 }}>
                  {t('upload.lightingStyles', 'Lighting & Perspective')}
                  <HelpTooltip text={t('help.lightingStyles', 'Generate extra variations with different lighting and composition styles — dramatic side-lit, warm golden hour, overhead flat-lay, and more.')} />
                </label>
              </div>
              <p className="angle-picker-hint">
                {t('upload.lightingStylesHint', 'Add lighting and composition variations to each scene')}
              </p>
              <div className="style-picker-grid">
                {ANGLE_OPTIONS.map(opt => {
                  const isSelected = selectedAngles.includes(opt.value);
                  return (
                    <button
                      key={opt.value}
                      className={`style-card ${isSelected ? 'selected' : ''}`}
                      onClick={() => {
                        setSelectedAngles(prev =>
                          isSelected ? prev.filter(a => a !== opt.value) : [...prev, opt.value]
                        );
                      }}
                    >
                      <div className={`style-card-thumb style-thumb-${opt.value}`} />
                      <div className="style-card-label">{opt.label}</div>
                      <div className="style-card-desc">{opt.desc}</div>
                    </button>
                  );
                })}
              </div>
              {selectedAngles.length > 0 && (
                <span className="angle-picker-count">
                  {t('upload.stylesSelected', '{{count}} style(s) selected', { count: selectedAngles.length })}
                  {sceneCount > 1 && ` × ${sceneCount} ${t('upload.scenes', 'scenes')} = ${selectedAngles.length * sceneCount} ${t('upload.images', 'images')}`}
                </span>
              )}
            </div>

            {sceneTemplates.length > 0 && (
              <div className="template-picker">
                <button
                  className="template-picker-toggle"
                  onClick={() => setShowTemplatePicker(!showTemplatePicker)}
                >
                  <ImageIcon size={16} />
                  <span>{t('upload.chooseFromLibrary', { count: selectedTemplateIds.length })}</span>
                  {showTemplatePicker ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                </button>

                {showTemplatePicker && (
                  <div className="template-picker-grid">
                    {sceneTemplates.map(tmpl => {
                      const isSelected = selectedTemplateIds.includes(tmpl.id);
                      return (
                        <div
                          key={tmpl.id}
                          className={`template-picker-card ${isSelected ? 'selected' : ''}`}
                          onClick={() => {
                            setSelectedTemplateIds(prev =>
                              isSelected ? prev.filter(id => id !== tmpl.id) : [...prev, tmpl.id]
                            );
                          }}
                        >
                          {tmpl.preview_url ? (
                            <img src={tmpl.preview_url} alt={tmpl.name} className="template-picker-img" />
                          ) : (
                            <div className="template-picker-placeholder"><ImageIcon size={16} /></div>
                          )}
                          <span className="template-picker-name">{tmpl.name}</span>
                          {isSelected && <CheckCircle size={14} className="template-picker-check" />}
                        </div>
                      );
                    })}
                  </div>
                )}

                {selectedTemplateIds.length > 0 && (
                  <div className="template-picker-option">
                    <span>{t('upload.useExactBackground')}</span>
                    <div
                      className={`toggle-switch ${useSavedBackground ? 'toggle-on' : ''}`}
                      onClick={() => setUseSavedBackground(!useSavedBackground)}
                    >
                      <div className="toggle-thumb" />
                    </div>
                  </div>
                )}
              </div>
            )}
          </>
          )}

          <CostPreview
            fileCount={files.length}
            options={processingOptions}
            sceneCount={processingOptions.generate_scene ? sceneCount : 1}
            angleCount={processingOptions.generate_scene ? selectedAngles.length : 0}
          />

          <button className="button-primary" onClick={uploadFiles}>
            {t('upload.uploadProcess', { count: files.length })}
            {sceneCount > 1 && processingOptions.generate_scene && t('upload.scenesEach', { count: sceneCount })}
            {selectedAngles.length > 0 && processingOptions.generate_scene && ` · ${selectedAngles.length} ${t('upload.styles', 'styles')}`}
          </button>
        </>
      )}

      {isUploading && (
        <div className="upload-status">
          <Loader className="spinning" size={24} />
          <span>{t('upload.uploading')}</span>
        </div>
      )}
    </div>
  );
}
