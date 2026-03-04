import { useState, useRef } from 'react';
import { Upload, X, Loader, CheckCircle, AlertCircle } from 'lucide-react';
import { api } from '../api';
import ProcessingOptions, { type ProcessingOptionsType } from './ProcessingOptions';

interface Props {
  onJobCreated: (jobId: string) => void;
}

interface FileWithStatus {
  file: File;
  status: 'pending' | 'uploading' | 'completed' | 'failed';
  error?: string;
}

export default function UploadSection({ onJobCreated }: Props) {
  const [files, setFiles] = useState<FileWithStatus[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);
  const [processingOptions, setProcessingOptions] = useState<ProcessingOptionsType>({
    remove_background: true,
    generate_scene: true,
    upscale: true,
  });
  const [sceneCount, setSceneCount] = useState(1);
  const fileInputRef = useRef<HTMLInputElement>(null);

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

    const droppedFiles = Array.from(e.dataTransfer.files).filter(
      (file) => file.type.startsWith('image/')
    );

    addFiles(droppedFiles);
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const selectedFiles = Array.from(e.target.files);
      addFiles(selectedFiles);
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

    try {
      const filenames = files.map((f) => f.file.name);
      const sceneOptions = sceneCount > 1 ? { scene_count: sceneCount } : undefined;
      const job = await api.createJob(filenames, processingOptions, sceneOptions);

      setJobId(job.job_id);
      onJobCreated(job.job_id);

      // Group job items by filename — upload once per unique file
      const seenFilenames = new Set<string>();

      for (let i = 0; i < files.length; i++) {
        const fileItem = files[i];
        // Find the first item for this filename
        const item = job.items.find((it) => it.filename === fileItem.file.name && !seenFilenames.has(it.item_id));
        if (!item) continue;
        seenFilenames.add(item.item_id);

        try {
          setFiles((prev) =>
            prev.map((f, idx) =>
              idx === i ? { ...f, status: 'uploading' } : f
            )
          );

          await api.uploadDirect(job.job_id, item.item_id, fileItem.file, processingOptions);

          setFiles((prev) =>
            prev.map((f, idx) =>
              idx === i ? { ...f, status: 'completed' } : f
            )
          );
        } catch (error) {
          setFiles((prev) =>
            prev.map((f, idx) =>
              idx === i
                ? {
                    ...f,
                    status: 'failed',
                    error: error instanceof Error ? error.message : 'Upload failed',
                  }
                : f
            )
          );
        }
      }

      await api.enqueueJob(job.job_id);
    } catch (error) {
      alert(error instanceof Error ? error.message : 'Failed to create job');
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

  return (
    <div className="upload-section">
      <div className="section-header">
        <h2>Upload Images</h2>
        <p>Upload product images to process with AI</p>
      </div>

      <div
        className={`drop-zone ${isDragging ? 'dragging' : ''}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
      >
        <Upload size={48} />
        <h3>Drag & drop images here</h3>
        <p>or click to browse</p>
        <span className="hint">Supports: JPG, PNG, WebP</span>
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
            <h3>{files.length} image(s) selected</h3>
            {!isUploading && (
              <button
                className="button-secondary"
                onClick={() => setFiles([])}
              >
                Clear All
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
                {fileItem.error && (
                  <span className="error-text">{fileItem.error}</span>
                )}
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
          <ProcessingOptions
            options={processingOptions}
            onChange={setProcessingOptions}
            disabled={isUploading}
          />

          {processingOptions.generate_scene && (
            <div className="scene-count-selector" style={{ margin: '1rem 0' }}>
              <label htmlFor="scene-count" style={{ fontWeight: 600, marginRight: '0.5rem' }}>
                Scenes per image:
              </label>
              <input
                id="scene-count"
                type="number"
                min={1}
                max={10}
                value={sceneCount}
                onChange={(e) => setSceneCount(Math.max(1, Math.min(10, parseInt(e.target.value) || 1)))}
                className="input"
                style={{ width: '4rem', display: 'inline-block' }}
              />
              {sceneCount > 1 && (
                <span className="hint" style={{ marginLeft: '0.5rem' }}>
                  {sceneCount} scene variations will be generated per image
                </span>
              )}
            </div>
          )}

          <button className="button-primary" onClick={uploadFiles}>
            Upload & Process {files.length} Image(s)
            {sceneCount > 1 && processingOptions.generate_scene && ` (${sceneCount} scenes each)`}
          </button>
        </>
      )}

      {isUploading && (
        <div className="upload-status">
          <Loader className="spinning" size={24} />
          <span>Uploading and processing...</span>
        </div>
      )}

      {jobId && !isUploading && (
        <div className="success-message">
          <CheckCircle size={20} />
          <span>
            Job created successfully! ID: <strong>{jobId}</strong>
          </span>
        </div>
      )}
    </div>
  );
}
