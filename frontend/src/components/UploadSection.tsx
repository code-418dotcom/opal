import { useState, useRef } from 'react';
import { Upload, X, Loader, CheckCircle, AlertCircle } from 'lucide-react';
import { api } from '../api';

interface Props {
  onJobCreated: (jobId: string) => void;
}

interface FileWithStatus {
  file: File;
  status: 'pending' | 'uploading' | 'completed' | 'failed';
  progress: number;
  error?: string;
}

export default function UploadSection({ onJobCreated }: Props) {
  const [files, setFiles] = useState<FileWithStatus[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);
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
      progress: 0,
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
      const job = await api.createJob(filenames);

      setJobId(job.job_id);
      onJobCreated(job.job_id);

      for (let i = 0; i < files.length; i++) {
        const fileItem = files[i];
        const item = job.items[i];

        try {
          setFiles((prev) =>
            prev.map((f, idx) =>
              idx === i ? { ...f, status: 'uploading', progress: 10 } : f
            )
          );

          const sasResponse = await api.getUploadSas(
            job.job_id,
            item.item_id,
            item.filename
          );

          setFiles((prev) =>
            prev.map((f, idx) =>
              idx === i ? { ...f, progress: 30 } : f
            )
          );

          await api.uploadToSas(sasResponse.upload_url, fileItem.file);

          setFiles((prev) =>
            prev.map((f, idx) =>
              idx === i ? { ...f, progress: 70 } : f
            )
          );

          await api.completeUpload(job.job_id, item.item_id, item.filename);

          setFiles((prev) =>
            prev.map((f, idx) =>
              idx === i ? { ...f, status: 'completed', progress: 100 } : f
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
                {fileItem.status === 'uploading' && (
                  <div className="progress-bar">
                    <div
                      className="progress-fill"
                      style={{ width: `${fileItem.progress}%` }}
                    ></div>
                  </div>
                )}
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
        <button className="button-primary" onClick={uploadFiles}>
          Upload & Process {files.length} Image(s)
        </button>
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
