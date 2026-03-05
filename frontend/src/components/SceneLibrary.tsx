import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Plus, X, Trash2, Loader, Sparkles, AlertCircle, RefreshCw, Image as ImageIcon,
} from 'lucide-react';
import { api } from '../api';
import type { SceneTemplate } from '../types';

export default function SceneLibrary() {
  const queryClient = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [filterBrand, setFilterBrand] = useState('');
  const [name, setName] = useState('');
  const [prompt, setPrompt] = useState('');
  const [brandId, setBrandId] = useState('');
  const [previewUrl, setPreviewUrl] = useState('');
  const [previewBlobPath, setPreviewBlobPath] = useState('');
  const [generating, setGenerating] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [regeneratingId, setRegeneratingId] = useState<string | null>(null);

  const { data: templates = [], isLoading } = useQuery({
    queryKey: ['scene-templates', filterBrand],
    queryFn: () => api.listSceneTemplates(filterBrand || undefined),
  });

  const { data: profiles = [] } = useQuery({
    queryKey: ['brand-profiles'],
    queryFn: () => api.listBrandProfiles(),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.deleteSceneTemplate(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['scene-templates'] }),
  });

  const brandName = (template: SceneTemplate) => {
    if (!template.brand_profile_id) return null;
    const bp = profiles.find(p => p.id === template.brand_profile_id);
    return bp?.name || null;
  };

  const openForm = () => {
    setName('');
    setPrompt('');
    setBrandId('');
    setPreviewUrl('');
    setPreviewBlobPath('');
    setError(null);
    setShowForm(true);
  };

  const generatePreview = async () => {
    if (!prompt.trim()) return;
    setGenerating(true);
    setError(null);
    try {
      const result = await api.generateScenePreview(prompt);
      setPreviewUrl(result.preview_url);
      setPreviewBlobPath(result.preview_blob_path);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Preview generation failed');
    } finally {
      setGenerating(false);
    }
  };

  const saveTemplate = async () => {
    if (!name.trim() || !prompt.trim()) return;
    setSaving(true);
    setError(null);
    try {
      const tmpl = await api.createSceneTemplate({
        name: name.trim(),
        prompt: prompt.trim(),
        brand_profile_id: brandId || undefined,
      });
      if (previewBlobPath) {
        await api.setSceneTemplatePreview(tmpl.id, previewBlobPath);
      }
      queryClient.invalidateQueries({ queryKey: ['scene-templates'] });
      setShowForm(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Save failed');
    } finally {
      setSaving(false);
    }
  };

  const regeneratePreview = async (template: SceneTemplate) => {
    setRegeneratingId(template.id);
    try {
      const result = await api.generateScenePreview(template.prompt);
      await api.setSceneTemplatePreview(template.id, result.preview_blob_path);
      queryClient.invalidateQueries({ queryKey: ['scene-templates'] });
    } catch (e) {
      console.error('Regenerate failed:', e);
    } finally {
      setRegeneratingId(null);
    }
  };

  if (isLoading) {
    return (
      <div className="loading-box">
        <Loader className="spinning" size={24} />
        <span>Loading scene library...</span>
      </div>
    );
  }

  return (
    <div className="scene-library">
      <div className="section-header">
        <div className="section-header-row">
          <div>
            <h2>Scene Library</h2>
            <p>Saved scene templates with AI-generated previews</p>
          </div>
          <button className="button-primary button-sm" onClick={openForm}>
            <Plus size={16} /> New Scene
          </button>
        </div>
      </div>

      <div className="library-toolbar">
        <select
          className="input library-filter-select"
          value={filterBrand}
          onChange={e => setFilterBrand(e.target.value)}
        >
          <option value="">All brands</option>
          {profiles.map(p => (
            <option key={p.id} value={p.id}>{p.name}</option>
          ))}
        </select>
      </div>

      {showForm && (
        <div className="scene-form-card">
          <div className="scene-form-header">
            <h3>New Scene Template</h3>
            <button className="button-icon" onClick={() => setShowForm(false)}><X size={16} /></button>
          </div>

          {error && (
            <div className="error-box" style={{ marginBottom: '1rem' }}>
              <AlertCircle size={16} />
              <span>{error}</span>
              <button className="button-icon" onClick={() => setError(null)} style={{ marginLeft: 'auto' }}>
                <X size={14} />
              </button>
            </div>
          )}

          <label className="form-label">Name</label>
          <input
            className="input"
            placeholder="e.g. Cozy Living Room"
            value={name}
            onChange={e => setName(e.target.value)}
          />

          <label className="form-label" style={{ marginTop: '1rem' }}>Prompt</label>
          <textarea
            className="input scene-prompt-textarea"
            placeholder="Describe the scene..."
            value={prompt}
            onChange={e => setPrompt(e.target.value)}
            rows={3}
          />

          <label className="form-label" style={{ marginTop: '1rem' }}>Brand Profile (optional)</label>
          <select
            className="input"
            value={brandId}
            onChange={e => setBrandId(e.target.value)}
          >
            <option value="">None</option>
            {profiles.map(p => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>

          <div className="scene-form-preview-area">
            {previewUrl ? (
              <img src={previewUrl} alt="Preview" className="scene-form-preview-img" />
            ) : (
              <div className="scene-form-preview-placeholder">
                <ImageIcon size={32} />
                <span>Generate a preview</span>
              </div>
            )}
          </div>

          <div className="scene-form-actions">
            <button
              className="button-secondary button-sm"
              onClick={generatePreview}
              disabled={generating || !prompt.trim()}
            >
              {generating
                ? <><Loader className="spinning" size={14} /> Generating...</>
                : <><Sparkles size={14} /> Generate Preview</>
              }
            </button>
            <button
              className="button-primary button-sm"
              onClick={saveTemplate}
              disabled={saving || !name.trim() || !prompt.trim()}
            >
              {saving ? <><Loader className="spinning" size={14} /> Saving...</> : 'Save to Library'}
            </button>
          </div>
        </div>
      )}

      {templates.length === 0 && !showForm && (
        <div className="empty-state">
          <ImageIcon size={48} />
          <h3>No scene templates yet</h3>
          <p>Create scene templates to reuse in your product jobs</p>
        </div>
      )}

      <div className="scene-grid">
        {templates.map(tmpl => (
          <div key={tmpl.id} className="scene-card">
            <div className="scene-card-preview">
              {tmpl.preview_url ? (
                <img src={tmpl.preview_url} alt={tmpl.name} className="scene-card-img" />
              ) : (
                <div className="scene-card-placeholder">
                  <ImageIcon size={24} />
                  <span className="scene-card-prompt-text">{tmpl.prompt.slice(0, 80)}...</span>
                </div>
              )}
            </div>
            <div className="scene-card-info">
              <h4 className="scene-card-name">{tmpl.name}</h4>
              <div className="scene-card-badges">
                {tmpl.scene_type && (
                  <span className="item-scene-tag">{tmpl.scene_type}</span>
                )}
                {brandName(tmpl) && (
                  <span className="brand-badge-sm">{brandName(tmpl)}</span>
                )}
              </div>
            </div>
            <div className="scene-card-actions">
              <button
                className="button-icon"
                onClick={() => regeneratePreview(tmpl)}
                disabled={regeneratingId === tmpl.id}
                title="Regenerate preview"
              >
                {regeneratingId === tmpl.id
                  ? <Loader className="spinning" size={14} />
                  : <RefreshCw size={14} />
                }
              </button>
              <button
                className="button-icon"
                onClick={() => deleteMutation.mutate(tmpl.id)}
                title="Delete"
              >
                <Trash2 size={14} />
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
