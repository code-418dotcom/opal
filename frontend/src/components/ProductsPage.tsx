import { useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Store, Image as ImageIcon, ArrowUpRight, Check, X,
  Loader2, ChevronRight, ChevronLeft, ArrowLeft,
} from 'lucide-react';
import { api } from '../api';
import type { Integration, ShopifyProduct, ShopifyImage } from '../types';

type View = 'stores' | 'products' | 'detail' | 'processing' | 'results';

interface ProcessedItem {
  item_id: string;
  filename: string;
  shopify_image_id: number;
  shopify_product_id: number;
}

export default function ProductsPage() {
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

  const { data: integrations, isLoading: loadingIntegrations } = useQuery({
    queryKey: ['integrations'],
    queryFn: () => api.listIntegrations(),
  });

  const activeStores = integrations?.filter(i => i.status === 'active') ?? [];

  // Auto-select if only one store
  const effectiveIntegration = activeIntegration ?? (activeStores.length === 1 ? activeStores[0] : null);
  const showStoreSelector = activeStores.length > 1 && !activeIntegration;

  const { data: productsData, isLoading: loadingProducts } = useQuery({
    queryKey: ['store-products', effectiveIntegration?.id, currentPageInfo],
    queryFn: () => api.listShopifyProducts(effectiveIntegration!.id, 20, currentPageInfo),
    enabled: !!effectiveIntegration && (view === 'products' || view === 'stores'),
  });

  const { data: jobData } = useQuery({
    queryKey: ['job', processingJobId],
    queryFn: () => api.getJob(processingJobId!),
    enabled: !!processingJobId && view === 'processing',
    refetchInterval: 3000,
  });

  // Auto-transition when job completes
  if (jobData && view === 'processing') {
    const status = jobData.status;
    if (status === 'completed' || status === 'partial' || status === 'failed') {
      setView('results');
    }
  }

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

  const handleProcessImages = async () => {
    if (!effectiveIntegration || !selectedProduct) return;
    setError(null);
    try {
      const imageIds = selectedImageIds.size > 0 ? Array.from(selectedImageIds) : undefined;
      const result = await api.processShopifyImages(
        effectiveIntegration.id,
        selectedProduct.id,
        imageIds,
      );
      setProcessingJobId(result.job_id);
      setProcessedItems(result.items);
      setView('processing');
      queryClient.invalidateQueries({ queryKey: ['balance'] });
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : t('integrations.processingFailed'));
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
      setError(err instanceof Error ? err.message : t('integrations.pushBackFailed'));
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

  const goBack = () => {
    if (view === 'results') {
      setView('detail');
      setProcessingJobId(null);
      setProcessedItems([]);
      setPushBackResults([]);
    } else if (view === 'detail') {
      setSelectedProduct(null);
      setView('products');
    } else if (view === 'products' && activeStores.length > 1) {
      setActiveIntegration(null);
      setCurrentPageInfo(undefined);
      setPageInfoStack([]);
      setView('stores');
    }
    // If single store on 'products' view, there's nowhere further back to go
  };

  // Determine the current breadcrumb path
  const storeName = effectiveIntegration
    ? (effectiveIntegration.provider_metadata?.shop_name || effectiveIntegration.store_url)
    : '';

  // Loading
  if (loadingIntegrations) {
    return (
      <div className="integrations-page">
        <div className="empty-state"><Loader2 size={24} className="spin" /> {t('common.loading', { defaultValue: 'Loading...' })}</div>
      </div>
    );
  }

  // No stores connected
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
      {showStoreSelector && (view === 'stores') && (
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

      {/* Product detail */}
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
                  onClick={handleProcessImages}
                  disabled={selectedProduct.images.length === 0}
                >
                  <ArrowUpRight size={14} />
                  {selectedImageIds.size > 0
                    ? t('integrations.processImages', { count: selectedImageIds.size, defaultValue: 'Process {{count}} images' })
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

      {/* Processing */}
      {view === 'processing' && (
        <div className="processing-view">
          <div className="view-header">
            <h2 className="section-title">{t('integrations.processingImages', { defaultValue: 'Processing images...' })}</h2>
          </div>
          <div className="processing-status">
            <Loader2 size={48} className="spin" />
            <p>{t('integrations.processingCount', { count: processedItems.length, defaultValue: 'Processing {{count}} items' })}</p>
            {jobData && (
              <div className="processing-progress">
                <span className={`status-badge status-${jobData.status}`}>{jobData.status}</span>
                <span>
                  {jobData.items.filter((i: { status: string }) => i.status === 'completed').length} / {jobData.items.length} {t('integrations.complete', { defaultValue: 'complete' })}
                </span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Results / push back */}
      {view === 'results' && jobData && (
        <div className="results-view">
          <div className="view-header">
            <button className="btn btn-secondary" onClick={goBack}>
              <ArrowLeft size={14} /> {t('products.backToProduct', { defaultValue: 'Back to product' })}
            </button>
            <h2 className="section-title">{t('results.title', { defaultValue: 'Results' })}</h2>
          </div>

          <div className="results-images-grid">
            {jobData.items.map((item: { item_id: string; filename: string; status: string; output_blob_path?: string }) => (
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
                  <input
                    type="radio"
                    name="pushBackMode"
                    value="add"
                    checked={pushBackMode === 'add'}
                    onChange={() => setPushBackMode('add')}
                  />
                  <span>{t('integrations.addAsNew', { defaultValue: 'Add as new images' })}</span>
                </label>
                <label className="push-back-option">
                  <input
                    type="radio"
                    name="pushBackMode"
                    value="replace"
                    checked={pushBackMode === 'replace'}
                    onChange={() => setPushBackMode('replace')}
                  />
                  <span>{t('integrations.replaceOriginal', { defaultValue: 'Replace original' })}</span>
                </label>
              </div>
              <button
                className="btn btn-primary"
                onClick={handlePushBack}
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
              <button className="btn btn-secondary" onClick={goBack} style={{ marginTop: '1rem' }}>
                {t('common.done', { defaultValue: 'Done' })}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
