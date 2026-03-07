import { useState, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Plus, X, Trash2, Edit3, ChevronRight, ChevronLeft,
  Loader, Check, AlertCircle, Sparkles, Eye, EyeOff,
  ImagePlus, Palette, Zap,
} from 'lucide-react';
import { api } from '../api';
import type { BrandProfile } from '../types';

const MOODS = ['modern', 'rustic', 'luxury', 'minimal', 'playful', 'professional'] as const;

const PRODUCT_CATEGORIES = [
  'Jewelry & Accessories',
  'Clothing & Apparel',
  'Shoes & Footwear',
  'Beauty & Skincare',
  'Food & Beverages',
  'Electronics & Gadgets',
  'Home & Furniture',
  'Toys & Games',
  'Sports & Outdoor',
  'Art & Handmade',
] as const;

interface WizardState {
  name: string;
  product_category: string;
  mood: string;
  style_keywords: string[];
  color_palette: string[];
  default_scene_count: number;
  default_scene_types: string[];
  previews: { url: string; blob_path: string; selected: boolean; prompt: string }[];
}

const emptyWizard = (): WizardState => ({
  name: '',
  product_category: '',
  mood: '',
  style_keywords: [],
  color_palette: ['#2563eb', '#10b981', '#f59e0b'],
  default_scene_count: 1,
  default_scene_types: [],
  previews: [],
});

export default function BrandProfiles() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [showWizard, setShowWizard] = useState(false);
  const [wizardStep, setWizardStep] = useState(0);
  const [wizard, setWizard] = useState<WizardState>(emptyWizard());
  const [editingId, setEditingId] = useState<string | null>(null);
  const [keywordInput, setKeywordInput] = useState('');
  const [generatingPreviews, setGeneratingPreviews] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { data: profiles = [], isLoading } = useQuery({
    queryKey: ['brand-profiles'],
    queryFn: () => api.listBrandProfiles(),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.deleteBrandProfile(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['brand-profiles'] }),
  });

  const openCreate = () => {
    setEditingId(null);
    setWizard(emptyWizard());
    setWizardStep(0);
    setError(null);
    setShowWizard(true);
  };

  const openEdit = (profile: BrandProfile) => {
    setEditingId(profile.id);
    setWizard({
      name: profile.name,
      product_category: profile.product_category || '',
      mood: profile.mood || '',
      style_keywords: profile.style_keywords || [],
      color_palette: profile.color_palette?.length ? profile.color_palette : ['#2563eb', '#10b981', '#f59e0b'],
      default_scene_count: profile.default_scene_count || 1,
      default_scene_types: profile.default_scene_types || [],
      previews: [],
    });
    setWizardStep(0);
    setError(null);
    setShowWizard(true);
  };

  const closeWizard = () => {
    setShowWizard(false);
    setEditingId(null);
  };

  const addKeyword = () => {
    const kw = keywordInput.trim();
    if (kw && !wizard.style_keywords.includes(kw)) {
      setWizard(w => ({ ...w, style_keywords: [...w.style_keywords, kw] }));
    }
    setKeywordInput('');
  };

  const removeKeyword = (kw: string) => {
    setWizard(w => ({ ...w, style_keywords: w.style_keywords.filter(k => k !== kw) }));
  };

  const updateColor = (idx: number, hex: string) => {
    setWizard(w => {
      const pal = [...w.color_palette];
      pal[idx] = hex;
      return { ...w, color_palette: pal };
    });
  };

  const CATEGORY_SURFACES: Record<string, string> = {
    'Jewelry & Accessories': 'velvet fabric surface or polished stone slab',
    'Clothing & Apparel': 'plain linen or cotton fabric draped flat',
    'Shoes & Footwear': 'smooth concrete or plain wooden floor',
    'Beauty & Skincare': 'smooth marble or ceramic tile surface',
    'Food & Beverages': 'natural wood board or plain ceramic plate surface',
    'Electronics & Gadgets': 'matte dark desk surface or brushed metal',
    'Home & Furniture': 'plain hardwood floor or neutral carpet',
    'Toys & Games': 'plain light-colored tabletop',
    'Sports & Outdoor': 'grass turf or plain concrete surface',
    'Art & Handmade': 'raw linen canvas or natural wood table',
  };

  const buildPrompt = () => {
    const parts: string[] = [];
    if (wizard.product_category) {
      const surface = CATEGORY_SURFACES[wizard.product_category] || 'plain flat surface';
      parts.push(surface);
    }
    if (wizard.mood) parts.push(wizard.mood);
    if (wizard.style_keywords.length) parts.push(wizard.style_keywords.join(', '));
    parts.push('completely bare scene, nothing on the surface, shallow depth of field');
    return parts.join(', ');
  };

  const generatePreviews = async () => {
    setGeneratingPreviews(true);
    setError(null);
    const prompt = buildPrompt();
    const results: WizardState['previews'] = [];

    const variations = [
      `${prompt}, solid white seamless backdrop, single soft even light`,
      `${prompt}, blurred warm-toned room far in background, single side light`,
      `${prompt}, solid dark backdrop, single warm accent light, subtle surface reflection`,
      `${prompt}, blurred green foliage far in background, warm golden hour sunlight`,
    ];

    try {
      const settled = await Promise.allSettled(
        variations.map(p => api.generateScenePreview(p))
      );
      for (let i = 0; i < settled.length; i++) {
        const r = settled[i];
        if (r.status === 'fulfilled') {
          results.push({
            url: r.value.preview_url,
            blob_path: r.value.preview_blob_path,
            selected: true,
            prompt: variations[i],
          });
        }
      }
      if (results.length === 0) {
        setError(t('brands.previewFailed'));
      }
      setWizard(w => ({ ...w, previews: results }));
    } catch (e) {
      setError(e instanceof Error ? e.message : t('brands.previewFailed'));
    } finally {
      setGeneratingPreviews(false);
    }
  };

  const togglePreview = (idx: number) => {
    setWizard(w => ({
      ...w,
      previews: w.previews.map((p, i) => i === idx ? { ...p, selected: !p.selected } : p),
    }));
  };

  const saveBrand = async () => {
    setSaving(true);
    setError(null);
    try {
      const data: Partial<BrandProfile> = {
        name: wizard.name,
        product_category: wizard.product_category || undefined,
        mood: wizard.mood || undefined,
        style_keywords: wizard.style_keywords,
        color_palette: wizard.color_palette.filter(c => c),
        default_scene_count: wizard.default_scene_count,
        default_scene_types: wizard.default_scene_types.length ? wizard.default_scene_types : undefined,
      };

      let profile: BrandProfile;
      if (editingId) {
        profile = await api.updateBrandProfile(editingId, data);
      } else {
        profile = await api.createBrandProfile(data);
      }

      // Save selected previews as scene templates
      const selected = wizard.previews.filter(p => p.selected);
      for (const preview of selected) {
        const tmpl = await api.createSceneTemplate({
          name: `${wizard.name} — Scene`,
          prompt: preview.prompt,
          brand_profile_id: profile.id,
        });
        if (preview.blob_path) {
          await api.setSceneTemplatePreview(tmpl.id, preview.blob_path);
        }
      }

      queryClient.invalidateQueries({ queryKey: ['brand-profiles'] });
      queryClient.invalidateQueries({ queryKey: ['scene-templates'] });
      closeWizard();
    } catch (e) {
      setError(e instanceof Error ? e.message : t('brands.saveFailed'));
    } finally {
      setSaving(false);
    }
  };

  const canNext = () => {
    if (wizardStep === 0) return wizard.name.trim().length > 0;
    if (wizardStep === 1) return wizard.product_category.length > 0;
    if (wizardStep === 2) return true;
    if (wizardStep === 3) return true;
    return true;
  };

  const stepLabels = [t('brands.steps.name'), t('brands.steps.product'), t('brands.steps.style'), t('brands.steps.previews'), t('brands.steps.review')];

  if (isLoading) {
    return (
      <div className="loading-box">
        <Loader className="spinning" size={24} />
        <span>{t('brands.loading')}</span>
      </div>
    );
  }

  return (
    <div className="brand-profiles">
      <div className="section-header">
        <div className="section-header-row">
          <div>
            <h2>{t('brands.title')}</h2>
            <p>{t('brands.subtitle')}</p>
          </div>
          <button className="button-primary button-sm" onClick={openCreate}>
            <Plus size={16} /> {t('brands.newBrand')}
          </button>
        </div>
      </div>

      {profiles.length === 0 && !showWizard && (
        <div className="empty-state">
          <Sparkles size={48} />
          <h3>{t('brands.noBrands')}</h3>
          <p>{t('brands.noBrandsHint')}</p>
        </div>
      )}

      {!showWizard && (
        <div className="brand-grid">
          {profiles.map(profile => (
            <div key={profile.id} className="brand-card">
              <div className="brand-card-header">
                <h3 className="brand-card-name">{profile.name}</h3>
                <div className="brand-card-actions">
                  <button className="button-icon" onClick={() => openEdit(profile)} title={t('common.edit')}>
                    <Edit3 size={15} />
                  </button>
                  <button
                    className="button-icon"
                    onClick={() => deleteMutation.mutate(profile.id)}
                    title={t('common.delete')}
                  >
                    <Trash2 size={15} />
                  </button>
                </div>
              </div>

              {profile.product_category && (
                <span className="brand-category-badge">{profile.product_category}</span>
              )}

              {profile.mood && (
                <span className="brand-mood-badge">{profile.mood}</span>
              )}

              {profile.style_keywords?.length > 0 && (
                <div className="brand-keywords">
                  {profile.style_keywords.map(kw => (
                    <span key={kw} className="brand-keyword-chip">{kw}</span>
                  ))}
                </div>
              )}

              {profile.color_palette?.length > 0 && (
                <div className="brand-palette">
                  {profile.color_palette.map((c, i) => (
                    <span
                      key={i}
                      className="brand-swatch"
                      style={{ background: c }}
                      title={c}
                    />
                  ))}
                </div>
              )}

              <ReferenceImages profileId={profile.id} />

              <div className="brand-card-meta">
                {profile.default_scene_count && profile.default_scene_count > 1
                  ? t('brands.scenes', { count: profile.default_scene_count })
                  : t('brands.oneScene')}
              </div>
            </div>
          ))}
        </div>
      )}

      {showWizard && (
        <div className="wizard-overlay">
          <div className="wizard">
            <div className="wizard-header">
              <h3>{editingId ? t('brands.editTitle') : t('brands.createTitle')}</h3>
              <button className="button-icon" onClick={closeWizard}><X size={18} /></button>
            </div>

            <div className="wizard-steps">
              {stepLabels.map((label, i) => (
                <div key={i} className={`wizard-step-indicator ${i === wizardStep ? 'active' : ''} ${i < wizardStep ? 'done' : ''}`}>
                  <span className="wizard-step-num">{i < wizardStep ? <Check size={12} /> : i + 1}</span>
                  <span className="wizard-step-label">{label}</span>
                </div>
              ))}
            </div>

            {error && (
              <div className="error-box" style={{ margin: '0 0 1rem' }}>
                <AlertCircle size={16} />
                <span>{error}</span>
                <button className="button-icon" onClick={() => setError(null)} style={{ marginLeft: 'auto' }}>
                  <X size={14} />
                </button>
              </div>
            )}

            <div className="wizard-body">
              {wizardStep === 0 && (
                <div className="wizard-step-content">
                  <label className="form-label">{t('brands.brandName')}</label>
                  <input
                    className="input"
                    placeholder={t('brands.brandNamePlaceholder')}
                    value={wizard.name}
                    onChange={e => setWizard(w => ({ ...w, name: e.target.value }))}
                    autoFocus
                  />
                </div>
              )}

              {wizardStep === 1 && (
                <div className="wizard-step-content">
                  <label className="form-label">{t('brands.whatDoYouSell')}</label>
                  <p className="form-hint" style={{ marginBottom: '1rem' }}>
                    {t('brands.categoryHint')}
                  </p>
                  <div className="category-grid">
                    {PRODUCT_CATEGORIES.map(cat => (
                      <button
                        key={cat}
                        className={`category-btn ${wizard.product_category === cat ? 'selected' : ''}`}
                        onClick={() => setWizard(w => ({ ...w, product_category: w.product_category === cat ? '' : cat }))}
                      >
                        {cat}
                      </button>
                    ))}
                  </div>
                  <label className="form-label" style={{ marginTop: '1rem' }}>{t('brands.orTypeOwn')}</label>
                  <input
                    className="input"
                    placeholder={t('brands.categoryPlaceholder')}
                    value={PRODUCT_CATEGORIES.includes(wizard.product_category as any) ? '' : wizard.product_category}
                    onChange={e => setWizard(w => ({ ...w, product_category: e.target.value }))}
                  />
                </div>
              )}

              {wizardStep === 2 && (
                <div className="wizard-step-content">
                  <label className="form-label">{t('brands.mood')}</label>
                  <div className="mood-grid">
                    {MOODS.map(m => (
                      <button
                        key={m}
                        className={`mood-btn ${wizard.mood === m ? 'selected' : ''}`}
                        onClick={() => setWizard(w => ({ ...w, mood: w.mood === m ? '' : m }))}
                      >
                        {m}
                      </button>
                    ))}
                  </div>

                  <label className="form-label" style={{ marginTop: '1.25rem' }}>{t('brands.styleKeywords')}</label>
                  <div className="keyword-input-row">
                    <input
                      className="input"
                      placeholder={t('brands.keywordPlaceholder')}
                      value={keywordInput}
                      onChange={e => setKeywordInput(e.target.value)}
                      onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); addKeyword(); } }}
                    />
                  </div>
                  {wizard.style_keywords.length > 0 && (
                    <div className="brand-keywords" style={{ marginTop: '0.5rem' }}>
                      {wizard.style_keywords.map(kw => (
                        <span key={kw} className="brand-keyword-chip removable" onClick={() => removeKeyword(kw)}>
                          {kw} <X size={12} />
                        </span>
                      ))}
                    </div>
                  )}

                  <label className="form-label" style={{ marginTop: '1.25rem' }}>{t('brands.colorPalette')}</label>
                  <div className="palette-inputs">
                    {wizard.color_palette.map((c, i) => (
                      <div key={i} className="palette-input-group">
                        <input
                          type="color"
                          value={c}
                          onChange={e => updateColor(i, e.target.value)}
                          className="palette-color-picker"
                        />
                        <input
                          className="input palette-hex-input"
                          value={c}
                          onChange={e => updateColor(i, e.target.value)}
                          maxLength={7}
                        />
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {wizardStep === 3 && (
                <div className="wizard-step-content">
                  <p className="form-hint">
                    {t('brands.previewHint')}
                  </p>
                  {wizard.previews.length === 0 && !generatingPreviews && (
                    <button className="button-primary" onClick={generatePreviews} style={{ marginTop: '1rem' }}>
                      <Sparkles size={16} /> {t('brands.generate4')}
                    </button>
                  )}
                  {generatingPreviews && (
                    <div className="loading-box" style={{ margin: '1rem 0' }}>
                      <Loader className="spinning" size={24} />
                      <span>{t('brands.generatingScenes')}</span>
                    </div>
                  )}
                  {wizard.previews.length > 0 && (
                    <>
                      <div className="preview-grid">
                        {wizard.previews.map((p, i) => (
                          <div
                            key={i}
                            className={`preview-card ${p.selected ? 'selected' : 'deselected'}`}
                            onClick={() => togglePreview(i)}
                          >
                            <img src={p.url} alt={`Preview ${i + 1}`} className="preview-img" />
                            <div className="preview-toggle">
                              {p.selected ? <Eye size={14} /> : <EyeOff size={14} />}
                              {p.selected ? t('brands.selected') : t('brands.deselected')}
                            </div>
                          </div>
                        ))}
                      </div>
                      <button
                        className="button-secondary button-sm"
                        onClick={generatePreviews}
                        disabled={generatingPreviews}
                        style={{ marginTop: '1rem' }}
                      >
                        <Sparkles size={14} /> {t('brands.regenerate')}
                      </button>
                    </>
                  )}
                </div>
              )}

              {wizardStep === 4 && (
                <div className="wizard-step-content">
                  <div className="review-section">
                    <div className="review-row">
                      <span className="review-label">{t('brands.reviewName')}</span>
                      <span className="review-value">{wizard.name}</span>
                    </div>
                    {wizard.product_category && (
                      <div className="review-row">
                        <span className="review-label">{t('brands.reviewProduct')}</span>
                        <span className="review-value">{wizard.product_category}</span>
                      </div>
                    )}
                    {wizard.mood && (
                      <div className="review-row">
                        <span className="review-label">{t('brands.reviewMood')}</span>
                        <span className="brand-mood-badge">{wizard.mood}</span>
                      </div>
                    )}
                    {wizard.style_keywords.length > 0 && (
                      <div className="review-row">
                        <span className="review-label">{t('brands.reviewKeywords')}</span>
                        <div className="brand-keywords">
                          {wizard.style_keywords.map(kw => (
                            <span key={kw} className="brand-keyword-chip">{kw}</span>
                          ))}
                        </div>
                      </div>
                    )}
                    {wizard.color_palette.filter(c => c).length > 0 && (
                      <div className="review-row">
                        <span className="review-label">{t('brands.reviewPalette')}</span>
                        <div className="brand-palette">
                          {wizard.color_palette.filter(c => c).map((c, i) => (
                            <span key={i} className="brand-swatch" style={{ background: c }} title={c} />
                          ))}
                        </div>
                      </div>
                    )}
                    <div className="review-row">
                      <span className="review-label">{t('brands.scenesToSave')}</span>
                      <span className="review-value">{t('brands.scenesToSaveCount', { selected: wizard.previews.filter(p => p.selected).length, total: wizard.previews.length })}</span>
                    </div>
                  </div>
                </div>
              )}
            </div>

            <div className="wizard-footer">
              {wizardStep > 0 && (
                <button className="button-secondary button-sm" onClick={() => setWizardStep(s => s - 1)}>
                  <ChevronLeft size={16} /> {t('common.back')}
                </button>
              )}
              <div style={{ flex: 1 }} />
              {wizardStep < 4 ? (
                <button
                  className="button-primary button-sm"
                  onClick={() => setWizardStep(s => s + 1)}
                  disabled={!canNext()}
                >
                  {t('common.next')} <ChevronRight size={16} />
                </button>
              ) : (
                <button
                  className="button-primary button-sm"
                  onClick={saveBrand}
                  disabled={saving}
                >
                  {saving ? <><Loader className="spinning" size={14} /> {t('brands.saving')}</> : <><Check size={16} /> {t('brands.saveBrand')}</>}
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}


function ReferenceImages({ profileId }: { profileId: string }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const fileRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [analyzing, setAnalyzing] = useState<string | null>(null);

  const { data } = useQuery({
    queryKey: ['brand-refs', profileId],
    queryFn: () => api.listReferenceImages(profileId),
  });

  const images = data?.reference_images || [];

  const handleUpload = async (file: File) => {
    // Sanitize filename
    const safeName = file.name.replace(/[^a-zA-Z0-9_\-.]/g, '_');
    setUploading(true);
    try {
      const resp = await api.uploadReferenceImage(profileId, safeName);
      // Upload to blob storage
      await fetch(resp.upload_url, {
        method: 'PUT',
        headers: { 'x-ms-blob-type': 'BlockBlob', 'Content-Type': file.type || 'image/jpeg' },
        body: file,
      });
      // Auto-analyze
      setAnalyzing(resp.reference_image.id);
      await api.analyzeReferenceImage(profileId, resp.reference_image.id);
      queryClient.invalidateQueries({ queryKey: ['brand-refs', profileId] });
    } catch (e) {
      console.error('Reference upload failed:', e);
    } finally {
      setUploading(false);
      setAnalyzing(null);
    }
  };

  const handleDelete = async (imageId: string) => {
    await api.deleteReferenceImage(profileId, imageId);
    queryClient.invalidateQueries({ queryKey: ['brand-refs', profileId] });
  };

  return (
    <div className="brand-refs">
      <div className="brand-refs-header">
        <span className="brand-refs-label">
          <Palette size={12} />
          {t('brands.referenceImages', { defaultValue: 'Style References' })}
          {images.length > 0 && <span className="brand-refs-count">{images.length}/5</span>}
        </span>
        {images.length < 5 && (
          <button
            className="button-icon"
            onClick={() => fileRef.current?.click()}
            disabled={uploading}
            title={t('brands.addReference', { defaultValue: 'Add reference image' })}
          >
            {uploading ? <Loader className="spinning" size={14} /> : <ImagePlus size={14} />}
          </button>
        )}
        <input
          ref={fileRef}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          style={{ display: 'none' }}
          onChange={(e) => { if (e.target.files?.[0]) handleUpload(e.target.files[0]); e.target.value = ''; }}
        />
      </div>

      {images.length > 0 && (
        <div className="brand-refs-grid">
          {images.map((img) => (
            <div key={img.id} className="brand-ref-thumb">
              {img.download_url ? (
                <img src={img.download_url} alt="" className="brand-ref-img" />
              ) : (
                <div className="brand-ref-placeholder" />
              )}
              {img.extracted_style?.colors && (
                <div className="brand-ref-colors">
                  {img.extracted_style.colors.slice(0, 3).map((c, i) => (
                    <span key={i} className="brand-swatch-mini" style={{ background: c }} />
                  ))}
                </div>
              )}
              {analyzing === img.id && (
                <div className="brand-ref-analyzing">
                  <Zap size={10} />
                </div>
              )}
              <button className="brand-ref-delete" onClick={() => handleDelete(img.id)}>
                <X size={10} />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
