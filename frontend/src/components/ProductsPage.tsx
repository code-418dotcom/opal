import { useState, useCallback, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Store, Image as ImageIcon, ArrowUpRight, Check, X,
  Loader2, ChevronRight, ChevronLeft, ArrowLeft,
  Minus, Plus, RotateCw, ChevronDown, ChevronUp,
} from 'lucide-react';
import { CheckCircle } from 'lucide-react';
import { api } from '../api';
import type { Integration, ShopifyProduct, ShopifyImage } from '../types';
import ProcessingOptions, { type ProcessingOptionsType } from './ProcessingOptions';
import CostPreview from './CostPreview';
import HelpTooltip from './HelpTooltip';
type View = 'stores' | 'products' | 'detail' | 'configure' | 'results';

interface ProcessedItem {
  item_id: string;
  filename: string;
  shopify_image_id: number;
  shopify_product_id: number;
}

interface Props {
  onJobCreated: (jobId: string) => void;
}

const ANGLE_OPTIONS = [
  { value: 'eye-level', label: 'Eye Level', desc: 'Balanced, even lighting' },
  { value: 'low-angle', label: 'Low Angle', desc: 'Dramatic, bold presence' },
  { value: 'overhead', label: 'Overhead', desc: 'Flat-lay, top-down' },
  { value: 'side-lit', label: 'Side Lit', desc: 'Deep shadows, texture' },
  { value: 'backlit', label: 'Backlit', desc: 'Soft glow, rim light' },
  { value: 'golden', label: 'Golden Hour', desc: 'Warm amber tones' },
];

export default function ProductsPage({ onJobCreated }: Props) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  const [view, setView] = useState<View>('stores');
  const [activeIntegration, setActiveIntegration] = useState<Integration | null>(null);
  const [selectedProduct, setSelectedProduct] = useState<ShopifyProduct | null>(null);
  const [selectedImageIds, setSelectedImageIds] = useState<Set<number>>(new Set());
  const [processingJobId, setProcessingJobId] = useState<string | null>(null);
  const [processedItems, setProcessedItems] = useState<ProcessedItem[]>([]);
  const [pushBackMode, setPushBackMode] = useState<'replace' | 'add'>('add');
  const [pushingBack, setPushingBack] = useState(false);
  const [pushBackResults, setPushBackResults] = useState<Array<{ item_id: string; status: string; error?: string }>>([]);
  const [pageInfoStack, setPageInfoStack] = useState<string[]>([]);
  const [currentPageInfo, setCurrentPageInfo] = useState<string | undefined>(undefined);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Processing options state
  const [processingOptions, setProcessingOptions] = useState<ProcessingOptionsType>({
    remove_background: true,
    generate_scene: true,
    upscale: true,
  });
  const [sceneCount, setSceneCount] = useState(1);
  const [selectedBrandId, setSelectedBrandId] = useState('');
  const [selectedTemplateIds, setSelectedTemplateIds] = useState<string[]>([]);
  const [useSavedBackground, setUseSavedBackground] = useState(false);
  const [showTemplatePicker, setShowTemplatePicker] = useState(false);
  const [selectedAngles, setSelectedAngles] = useState<string[]>([]);

  const { data: integrations, isLoading: loadingIntegrations } = useQuery({
    queryKey: ['integrations'],
    queryFn: () => api.listIntegrations(),
  });

  const { data: brandProfiles = [] } = useQuery({
    queryKey: ['brand-profiles'],
    queryFn: () => api.listBrandProfiles(),
  });

  const { data: sceneTemplates = [] } = useQuery({
    queryKey: ['scene-templates', selectedBrandId],
    queryFn: () => api.listSceneTemplates(selectedBrandId || undefined),
    enabled: processingOptions.generate_scene && view === 'configure',
  });

  const activeStores = integrations?.filter(i => i.status === 'active') ?? [];
  const effectiveIntegration = activeIntegration ?? (activeStores.length === 1 ? activeStores[0] : null);
  const showStoreSelector = activeStores.length > 1 && !activeIntegration;

  const { data: productsData, isLoading: loadingProducts } = useQuery({
    queryKey: ['store-products', effectiveIntegration?.id, currentPageInfo],
    queryFn: () => api.listShopifyProducts(effectiveIntegration!.id, 20, currentPageInfo),
    enabled: !!effectiveIntegration && (view === 'products' || view === 'stores'),
  });

  // Auto-populate scene count from brand profile
  useEffect(() => {
    if (!selectedBrandId) return;
    const bp = brandProfiles.find((p: { id: string; default_scene_count?: number }) => p.id === selectedBrandId);
    if (bp?.default_scene_count && bp.default_scene_count > 1) {
      setSceneCount(bp.default_scene_count);
    }
  }, [selectedBrandId, brandProfiles]);

  const handleSelectStore = (integration: Integration) => {
    setActiveIntegration(integration);
    setCurrentPageInfo(undefined);
    setPageInfoStack([]);
    setView('products');
  };

  const handleSelectProduct = (product: ShopifyProduct) => {
    setSelectedProduct(product);
    setSelectedImageIds(new Set());
    setView('detail');
  };

  const toggleImageSelection = (imageId: number) => {
    setSelectedImageIds(prev => {
      const next = new Set(prev);
      if (next.has(imageId)) next.delete(imageId);
      else next.add(imageId);
      return next;
    });
  };

  const selectAllImages = useCallback(() => {
    if (!selectedProduct) return;
    if (selectedImageIds.size === selectedProduct.images.length) {
      setSelectedImageIds(new Set());
    } else {
      setSelectedImageIds(new Set(selectedProduct.images.map(img => img.id)));
    }
  }, [selectedProduct, selectedImageIds.size]);

  const handleContinueToConfig = () => {
    setView('configure');
  };

  const handleProcessImages = async () => {
    if (!effectiveIntegration || !selectedProduct) return;
    setError(null);
    setIsSubmitting(true);
    try {
      const imageIds = selectedImageIds.size > 0 ? Array.from(selectedImageIds) : undefined;
      const hasSceneOptions = sceneCount > 1 || selectedTemplateIds.length > 0 || selectedAngles.length > 0;
      const sceneOptions = hasSceneOptions ? {
        scene_count: sceneCount,
        scene_template_ids: selectedTemplateIds.length > 0 ? selectedTemplateIds : undefined,
        use_saved_background: selectedTemplateIds.length > 0 ? useSavedBackground : undefined,
        angle_types: selectedAngles.length > 0 ? selectedAngles : undefined,
      } : undefined;

      const result = await api.processShopifyImages(
        effectiveIntegration.id,
        selectedProduct.id,
        imageIds,
        selectedBrandId || 'default',
        processingOptions,
        sceneOptions,
      );
      setProcessingJobId(result.job_id);
      setProcessedItems(result.items);
      queryClient.invalidateQueries({ queryKey: ['balance'] });

      // Navigate to Job Monitor
      onJobCreated(result.job_id);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : t('integrations.processingFailed', { defaultValue: 'Processing failed' }));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handlePushBack = async () => {
    if (!effectiveIntegration || !processingJobId) return;
    setPushingBack(true);
    setError(null);
    try {
      const items = processedItems.map(item => ({
        item_id: item.item_id,
        shopify_product_id: item.shopify_product_id,
        shopify_image_id: item.shopify_image_id,
        mode: pushBackMode,
      }));
      const result = await api.pushBackToShopify(effectiveIntegration.id, processingJobId, items);
      setPushBackResults(result.results);
      queryClient.invalidateQueries({ queryKey: ['balance'] });
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : t('integrations.pushBackFailed', { defaultValue: 'Push back failed' }));
    } finally {
      setPushingBack(false);
    }
  };

  const handleNextPage = () => {
    if (productsData?.next_page_info) {
      setPageInfoStack(prev => [...prev, currentPageInfo || '']);
      setCurrentPageInfo(productsData.next_page_info);
    }
  };

  const handlePrevPage = () => {
    const prev = pageInfoStack[pageInfoStack.length - 1];
    setPageInfoStack(s => s.slice(0, -1));
    setCurrentPageInfo(prev || undefined);
  };

  const adjustSceneCount = (delta: number) => {
    setSceneCount(prev => Math.max(1, Math.min(10, prev + delta)));
  };

  const goBack = () => {
    if (view === 'results') {
      setView('detail');
      setProcessingJobId(null);
      setProcessedItems([]);
      setPushBackResults([]);
    } else if (view === 'configure') {
      setView('detail');
    } else if (view === 'detail') {
      setSelectedProduct(null);
      setView('products');
    } else if (view === 'products' && activeStores.length > 1) {
      setActiveIntegration(null);
      setCurrentPageInfo(undefined);
      setPageInfoStack([]);
      setView('stores');
    }
  };

  const storeName = effectiveIntegration
    ? (effectiveIntegration.provider_metadata?.shop_name || effectiveIntegration.store_url)
    : '';

  const imageCount = selectedProduct
    ? (selectedImageIds.size > 0 ? selectedImageIds.size : selectedProduct.images.length)
    : 0;

  if (loadingIntegrations) {
    return (
      <div className="integrations-page">
        <div className="empty-state"><Loader2 size={24} className="spin" /> {t('common.loading', { defaultValue: 'Loading...' })}</div>
      </div>
    );
  }

  if (activeStores.length === 0) {
    return (
      <div className="integrations-page">
        <div className="empty-state">
          <Store size={48} />
          <p>{t('products.noStores', { defaultValue: 'No stores connected yet' })}</p>
          <p style={{ fontSize: '0.85rem', color: 'rgba(200,205,224,0.5)' }}>
            {t('products.connectHint', { defaultValue: 'Connect a store in Integrations to start browsing your products.' })}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="integrations-page">
      {error && (
        <div className="integration-error">
          <X size={14} />
          <span>{error}</span>
          <button onClick={() => setError(null)}>{t('common.dismiss', { defaultValue: 'Dismiss' })}</button>
        </div>
      )}

      {/* Store selector (multi-store only) */}
      {showStoreSelector && view === 'stores' && (
        <>
          <h2 className="section-title">{t('products.selectStore', { defaultValue: 'Select a store' })}</h2>
          <div className="integrations-grid">
            {activeStores.map(integ => (
              <div
                key={integ.id}
                className="integration-card"
                style={{ cursor: 'pointer' }}
                onClick={() => handleSelectStore(integ)}
              >
                <div className="integration-card-header">
                  <Store size={20} />
                  <div>
                    <div className="integration-store-name">
                      {integ.provider_metadata?.shop_name || integ.store_url}
                    </div>
                    <div className="integration-store-url">{integ.store_url}</div>
                  </div>
                  <ChevronRight size={16} style={{ marginLeft: 'auto', opacity: 0.5 }} />
                </div>
                <div className="integration-card-meta">
                  <span className="integration-provider">{integ.provider}</span>
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      {/* Product grid */}
      {(view === 'products' || (view === 'stores' && !showStoreSelector)) && effectiveIntegration && (
        <>
          <div className="view-header">
            {activeStores.length > 1 && (
              <button className="btn btn-secondary" onClick={goBack}>
                <ArrowLeft size={14} /> {t('products.allStores', { defaultValue: 'All stores' })}
              </button>
            )}
            <h2 className="section-title">{storeName}</h2>
          </div>

          {loadingProducts ? (
            <div className="empty-state"><Loader2 size={24} className="spin" /> {t('integrations.loadingProducts', { defaultValue: 'Loading products...' })}</div>
          ) : (
            <>
              <div className="products-grid">
                {productsData?.products.map((product: ShopifyProduct) => (
                  <div
                    key={product.id}
                    className="product-card"
                    onClick={() => handleSelectProduct(product)}
                  >
                    {product.images[0] ? (
                      <img
                        src={product.images[0].src}
                        alt={product.title}
                        className="product-card-image"
                      />
                    ) : (
                      <div className="product-card-no-image">
                        <ImageIcon size={32} />
                      </div>
                    )}
                    <div className="product-card-info">
                      <div className="product-card-title">{product.title}</div>
                      <div className="product-card-meta">
                        {t('integrations.imageCount', { count: product.images.length, defaultValue: '{{count}} images' })} &middot; {product.status}
                      </div>
                    </div>
                    <ChevronRight size={16} className="product-card-arrow" />
                  </div>
                ))}
              </div>
              <div className="pagination">
                <button
                  className="btn btn-secondary"
                  onClick={handlePrevPage}
                  disabled={pageInfoStack.length === 0}
                >
                  <ChevronLeft size={14} /> {t('common.previous', { defaultValue: 'Previous' })}
                </button>
                <button
                  className="btn btn-secondary"
                  onClick={handleNextPage}
                  disabled={!productsData?.next_page_info}
                >
                  {t('common.next', { defaultValue: 'Next' })} <ChevronRight size={14} />
                </button>
              </div>
            </>
          )}
        </>
      )}

      {/* Product detail — image selection */}
      {view === 'detail' && selectedProduct && effectiveIntegration && (
        <>
          <div className="view-header">
            <button className="btn btn-secondary" onClick={goBack}>
              <ArrowLeft size={14} /> {t('products.backToProducts', { defaultValue: 'Products' })}
            </button>
            <h2 className="section-title">{storeName}</h2>
          </div>
          <div className="product-detail">
            <div className="product-detail-header">
              <h3>{selectedProduct.title}</h3>
              <div className="product-detail-actions">
                <button className="btn btn-secondary" onClick={selectAllImages}>
                  {selectedImageIds.size === selectedProduct.images.length
                    ? t('integrations.deselectAll', { defaultValue: 'Deselect All' })
                    : t('integrations.selectAll', { defaultValue: 'Select All' })}
                </button>
                <button
                  className="btn btn-primary"
                  onClick={handleContinueToConfig}
                  disabled={selectedProduct.images.length === 0}
                >
                  <ArrowUpRight size={14} />
                  {selectedImageIds.size > 0
                    ? t('products.processSelected', { count: selectedImageIds.size, defaultValue: 'Process {{count}} images' })
                    : t('integrations.processAll', { defaultValue: 'Process All' })}
                </button>
              </div>
            </div>
            <div className="product-images-grid">
              {selectedProduct.images.map((img: ShopifyImage) => (
                <div
                  key={img.id}
                  className={`product-image-card ${selectedImageIds.has(img.id) ? 'selected' : ''}`}
                  onClick={() => toggleImageSelection(img.id)}
                >
                  <img src={img.src} alt={`Product image ${img.position}`} />
                  <div className="product-image-overlay">
                    {selectedImageIds.has(img.id) && <Check size={24} />}
                  </div>
                  <div className="product-image-info">
                    {img.width}x{img.height} &middot; #{img.position}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </>
      )}

      {/* Configure processing options */}
      {view === 'configure' && selectedProduct && effectiveIntegration && (
        <>
          <div className="view-header">
            <button className="btn btn-secondary" onClick={goBack}>
              <ArrowLeft size={14} /> {t('products.backToImages', { defaultValue: 'Back to images' })}
            </button>
            <h2 className="section-title">
              {selectedProduct.title} &middot; {imageCount} {t('products.imagesToProcess', { defaultValue: 'image(s)' })}
            </h2>
          </div>

          <div className="upload-section" style={{ maxWidth: '700px' }}>
            {brandProfiles.length > 0 && (
              <div className="brand-selector">
                <label className="form-label">
                  {t('upload.brandProfile', { defaultValue: 'Brand Profile' })}
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
                  <option value="">{t('upload.noneDefault', { defaultValue: 'None (default)' })}</option>
                  {brandProfiles.map((p: { id: string; name: string }) => (
                    <option key={p.id} value={p.id}>{p.name}</option>
                  ))}
                </select>
              </div>
            )}

            <ProcessingOptions
              options={processingOptions}
              onChange={setProcessingOptions}
              disabled={isSubmitting}
            />

            {processingOptions.generate_scene && (
              <>
                <div className="scene-count-section">
                  <label className="scene-count-label">
                    {t('upload.scenesPerImage', { defaultValue: 'Scenes per image' })}
                    <HelpTooltip text={t('help.scenesPerImage', 'Generate multiple different scene variations for each product image. More scenes = more options to choose from.')} />
                  </label>
                  <div className="scene-count-stepper">
                    <button className="stepper-btn" onClick={() => adjustSceneCount(-1)} disabled={sceneCount <= 1}>
                      <Minus size={16} />
                    </button>
                    <span className="stepper-value">{sceneCount}</span>
                    <button className="stepper-btn" onClick={() => adjustSceneCount(1)} disabled={sceneCount >= 10}>
                      <Plus size={16} />
                    </button>
                  </div>
                  {sceneCount > 1 && (
                    <span className="scene-count-hint">
                      {t('upload.sceneVariations', { count: sceneCount, defaultValue: '{{count}} scene variations per image' })}
                    </span>
                  )}
                </div>

                <div className="angle-picker-section">
                  <div className="angle-picker-header">
                    <RotateCw size={16} />
                    <label className="form-label" style={{ margin: 0 }}>
                      {t('upload.lightingStyles', { defaultValue: 'Lighting & Perspective' })}
                      <HelpTooltip text={t('help.lightingStyles', 'Generate extra variations with different lighting and composition styles.')} />
                    </label>
                  </div>
                  <p className="angle-picker-hint">
                    {t('upload.lightingStylesHint', { defaultValue: 'Add lighting and composition variations to each scene' })}
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
                      {t('upload.stylesSelected', { count: selectedAngles.length, defaultValue: '{{count}} style(s) selected' })}
                      {sceneCount > 1 && ` × ${sceneCount} ${t('upload.scenes', { defaultValue: 'scenes' })} = ${selectedAngles.length * sceneCount} ${t('upload.images', { defaultValue: 'images' })}`}
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
                      <span>{t('upload.chooseFromLibrary', { count: selectedTemplateIds.length, defaultValue: 'Choose from library ({{count}} selected)' })}</span>
                      {showTemplatePicker ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                    </button>

                    {showTemplatePicker && (
                      <div className="template-picker-grid">
                        {sceneTemplates.map((tmpl: { id: string; name: string; preview_url?: string }) => {
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
                        <span>{t('upload.useExactBackground', { defaultValue: 'Use exact background' })}</span>
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
              fileCount={imageCount}
              options={processingOptions}
              sceneCount={processingOptions.generate_scene ? sceneCount : 1}
              angleCount={processingOptions.generate_scene ? selectedAngles.length : 0}
            />

            <button
              className="button-primary"
              onClick={handleProcessImages}
              disabled={isSubmitting}
              style={{ width: '100%', marginTop: '0.5rem' }}
            >
              {isSubmitting ? (
                <><Loader2 size={16} className="spin" /> {t('products.submitting', { defaultValue: 'Submitting...' })}</>
              ) : (
                <><ArrowUpRight size={16} /> {t('products.startProcessing', { defaultValue: 'Start Processing' })}</>
              )}
            </button>
          </div>
        </>
      )}

      {/* Results / push back (accessible after returning from monitor) */}
      {view === 'results' && processingJobId && (
        <ResultsPushBack
          integrationId={effectiveIntegration?.id ?? ''}
          jobId={processingJobId}
          processedItems={processedItems}
          pushBackMode={pushBackMode}
          setPushBackMode={setPushBackMode}
          pushingBack={pushingBack}
          pushBackResults={pushBackResults}
          onPushBack={handlePushBack}
          onBack={goBack}
          error={error}
          setError={setError}
        />
      )}
    </div>
  );
}

// Extracted results/push-back into a sub-component
function ResultsPushBack({
  jobId,
  pushBackMode,
  setPushBackMode,
  pushingBack,
  pushBackResults,
  onPushBack,
  onBack,
}: {
  integrationId: string;
  jobId: string;
  processedItems: Array<{ item_id: string; filename: string; shopify_image_id: number; shopify_product_id: number }>;
  pushBackMode: 'replace' | 'add';
  setPushBackMode: (m: 'replace' | 'add') => void;
  pushingBack: boolean;
  pushBackResults: Array<{ item_id: string; status: string; error?: string }>;
  onPushBack: () => void;
  onBack: () => void;
  error: string | null;
  setError: (e: string | null) => void;
}) {
  const { t } = useTranslation();

  const { data: jobData } = useQuery({
    queryKey: ['job', jobId],
    queryFn: () => api.getJob(jobId),
  });

  if (!jobData) {
    return <div className="empty-state"><Loader2 size={24} className="spin" /></div>;
  }

  return (
    <div className="results-view">
      <div className="view-header">
        <button className="btn btn-secondary" onClick={onBack}>
          <ArrowLeft size={14} /> {t('products.backToProduct', { defaultValue: 'Back to product' })}
        </button>
        <h2 className="section-title">{t('results.title', { defaultValue: 'Results' })}</h2>
      </div>

      <div className="results-images-grid">
        {jobData.items.map((item: { item_id: string; filename: string; status: string }) => (
          <div key={item.item_id} className={`result-image-card status-${item.status}`}>
            <div className="result-image-filename">{item.filename}</div>
            <span className={`status-badge status-${item.status}`}>{item.status}</span>
          </div>
        ))}
      </div>

      {pushBackResults.length === 0 ? (
        <div className="push-back-section">
          <h3>{t('integrations.pushBackTitle', { defaultValue: 'Push images back to store' })}</h3>
          <div className="push-back-options">
            <label className="push-back-option">
              <input type="radio" name="pushBackMode" value="add" checked={pushBackMode === 'add'} onChange={() => setPushBackMode('add')} />
              <span>{t('integrations.addAsNew', { defaultValue: 'Add as new images' })}</span>
            </label>
            <label className="push-back-option">
              <input type="radio" name="pushBackMode" value="replace" checked={pushBackMode === 'replace'} onChange={() => setPushBackMode('replace')} />
              <span>{t('integrations.replaceOriginal', { defaultValue: 'Replace original' })}</span>
            </label>
          </div>
          <button
            className="btn btn-primary"
            onClick={onPushBack}
            disabled={pushingBack || jobData.status === 'failed'}
          >
            {pushingBack ? (
              <><Loader2 size={14} className="spin" /> {t('integrations.pushing', { defaultValue: 'Pushing...' })}</>
            ) : (
              <><ArrowUpRight size={14} /> {t('integrations.pushImages', { count: jobData.items.filter((i: { status: string }) => i.status === 'completed').length, defaultValue: 'Push {{count}} images' })}</>
            )}
          </button>
        </div>
      ) : (
        <div className="push-back-results">
          <h3>{t('integrations.pushBackResults', { defaultValue: 'Push back results' })}</h3>
          {pushBackResults.map((r, i) => (
            <div key={i} className={`push-back-result push-back-${r.status}`}>
              {r.status === 'success' ? <Check size={14} /> : <X size={14} />}
              <span>{r.item_id}: {r.status}</span>
              {r.error && <span className="push-back-error">{r.error}</span>}
            </div>
          ))}
          <button className="btn btn-secondary" onClick={onBack} style={{ marginTop: '1rem' }}>
            {t('common.done', { defaultValue: 'Done' })}
          </button>
        </div>
      )}
    </div>
  );
}
