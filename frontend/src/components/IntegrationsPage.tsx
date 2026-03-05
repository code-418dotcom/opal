import { useState, useCallback } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Store, Link, Unlink, Image as ImageIcon, ArrowUpRight, Check, X, Loader2, ChevronRight, ChevronLeft } from 'lucide-react';
import { api } from '../api';
import type { Integration, ShopifyProduct, ShopifyImage } from '../types';

type View = 'list' | 'products' | 'processing' | 'results';

interface ProcessedItem {
  item_id: string;
  filename: string;
  shopify_image_id: number;
  shopify_product_id: number;
}

export default function IntegrationsPage() {
  const queryClient = useQueryClient();
  const [view, setView] = useState<View>('list');
  const [shopDomain, setShopDomain] = useState('');
  const [connecting, setConnecting] = useState(false);
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

  const { data: integrations, isLoading } = useQuery({
    queryKey: ['integrations'],
    queryFn: () => api.listIntegrations(),
  });

  const { data: costs } = useQuery({
    queryKey: ['integration-costs', 'shopify'],
    queryFn: () => api.getIntegrationCosts('shopify'),
  });

  const { data: productsData, isLoading: loadingProducts } = useQuery({
    queryKey: ['shopify-products', activeIntegration?.id, currentPageInfo],
    queryFn: () => api.listShopifyProducts(activeIntegration!.id, 20, currentPageInfo),
    enabled: !!activeIntegration && view === 'products',
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
      if (view === 'processing') {
        setView('results');
      }
    }
  }

  const handleConnect = async () => {
    if (!shopDomain) return;
    setConnecting(true);
    setError(null);
    try {
      const shop = shopDomain.includes('.myshopify.com')
        ? shopDomain
        : `${shopDomain}.myshopify.com`;
      const result = await api.connectShopify(shop);
      window.location.href = result.auth_url;
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Connection failed');
      setConnecting(false);
    }
  };

  const handleDisconnect = async (integrationId: string) => {
    if (!confirm('Disconnect this store? You can reconnect later.')) return;
    try {
      await api.disconnectIntegration(integrationId);
      queryClient.invalidateQueries({ queryKey: ['integrations'] });
      setActiveIntegration(null);
      setView('list');
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Disconnect failed');
    }
  };

  const handleBrowseProducts = (integration: Integration) => {
    setActiveIntegration(integration);
    setCurrentPageInfo(undefined);
    setPageInfoStack([]);
    setView('products');
  };

  const handleSelectProduct = (product: ShopifyProduct) => {
    setSelectedProduct(product);
    setSelectedImageIds(new Set());
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
    if (!activeIntegration || !selectedProduct) return;
    setError(null);
    try {
      const imageIds = selectedImageIds.size > 0 ? Array.from(selectedImageIds) : undefined;
      const result = await api.processShopifyImages(
        activeIntegration.id,
        selectedProduct.id,
        imageIds,
      );
      setProcessingJobId(result.job_id);
      setProcessedItems(result.items);
      setView('processing');
      queryClient.invalidateQueries({ queryKey: ['balance'] });
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Processing failed');
    }
  };

  const handlePushBack = async () => {
    if (!activeIntegration || !processingJobId) return;
    setPushingBack(true);
    setError(null);
    try {
      const items = processedItems.map(item => ({
        item_id: item.item_id,
        shopify_product_id: item.shopify_product_id,
        shopify_image_id: item.shopify_image_id,
        mode: pushBackMode,
      }));
      const result = await api.pushBackToShopify(activeIntegration.id, processingJobId, items);
      setPushBackResults(result.results);
      queryClient.invalidateQueries({ queryKey: ['balance'] });
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Push-back failed');
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
    if (view === 'results' || view === 'processing') {
      setView('products');
      setProcessingJobId(null);
      setProcessedItems([]);
      setPushBackResults([]);
      setSelectedProduct(null);
    } else if (view === 'products') {
      setView('list');
      setActiveIntegration(null);
    }
  };

  return (
    <div className="integrations-page">
      {error && (
        <div className="integration-error">
          <X size={14} />
          <span>{error}</span>
          <button onClick={() => setError(null)}>Dismiss</button>
        </div>
      )}

      {view === 'list' && (
        <>
          <h2 className="section-title">Connected Stores</h2>

          {isLoading ? (
            <div className="empty-state"><Loader2 size={24} className="spin" /> Loading...</div>
          ) : integrations && integrations.length > 0 ? (
            <div className="integrations-grid">
              {integrations.map(integ => (
                <div key={integ.id} className="integration-card">
                  <div className="integration-card-header">
                    <Store size={20} />
                    <div>
                      <div className="integration-store-name">
                        {integ.provider_metadata?.shop_name || integ.store_url}
                      </div>
                      <div className="integration-store-url">{integ.store_url}</div>
                    </div>
                    <span className={`integration-badge integration-badge-${integ.status}`}>
                      {integ.status}
                    </span>
                  </div>
                  <div className="integration-card-meta">
                    <span className="integration-provider">{integ.provider}</span>
                    <span className="integration-date">
                      Connected {new Date(integ.created_at).toLocaleDateString()}
                    </span>
                  </div>
                  <div className="integration-card-actions">
                    <button
                      className="btn btn-primary"
                      onClick={() => handleBrowseProducts(integ)}
                      disabled={integ.status !== 'active'}
                    >
                      <ImageIcon size={14} />
                      Browse Products
                    </button>
                    <button
                      className="btn btn-danger"
                      onClick={() => handleDisconnect(integ.id)}
                    >
                      <Unlink size={14} />
                      Disconnect
                    </button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-state">
              <Store size={48} />
              <p>No stores connected yet</p>
            </div>
          )}

          <h2 className="section-title" style={{ marginTop: '2rem' }}>Connect a Store</h2>
          <div className="connect-form">
            <div className="connect-input-group">
              <input
                type="text"
                placeholder="your-store.myshopify.com"
                value={shopDomain}
                onChange={e => setShopDomain(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleConnect()}
                className="connect-input"
              />
              <button
                className="btn btn-primary"
                onClick={handleConnect}
                disabled={connecting || !shopDomain}
              >
                {connecting ? (
                  <><Loader2 size={14} className="spin" /> Connecting...</>
                ) : (
                  <><Link size={14} /> Connect Shopify</>
                )}
              </button>
            </div>
            {costs && (
              <p className="connect-cost-info">
                Cost: {costs.process_image} token(s) per image processed
                {costs.push_back > 0 ? `, ${costs.push_back} token(s) per push-back` : ', push-back free'}
              </p>
            )}
          </div>
        </>
      )}

      {view === 'products' && activeIntegration && (
        <>
          <div className="view-header">
            <button className="btn btn-secondary" onClick={goBack}>
              <ChevronLeft size={14} /> Back
            </button>
            <h2 className="section-title">
              {activeIntegration.provider_metadata?.shop_name || activeIntegration.store_url}
            </h2>
          </div>

          {selectedProduct ? (
            <div className="product-detail">
              <div className="product-detail-header">
                <h3>{selectedProduct.title}</h3>
                <div className="product-detail-actions">
                  <button className="btn btn-secondary" onClick={selectAllImages}>
                    {selectedImageIds.size === selectedProduct.images.length ? 'Deselect All' : 'Select All'}
                  </button>
                  <button
                    className="btn btn-primary"
                    onClick={handleProcessImages}
                    disabled={selectedProduct.images.length === 0}
                  >
                    <ArrowUpRight size={14} />
                    Process {selectedImageIds.size > 0 ? selectedImageIds.size : 'All'} Image(s)
                  </button>
                  <button className="btn btn-secondary" onClick={() => setSelectedProduct(null)}>
                    <X size={14} /> Cancel
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
          ) : (
            <>
              {loadingProducts ? (
                <div className="empty-state"><Loader2 size={24} className="spin" /> Loading products...</div>
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
                            {product.images.length} image(s) &middot; {product.status}
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
                      <ChevronLeft size={14} /> Previous
                    </button>
                    <button
                      className="btn btn-secondary"
                      onClick={handleNextPage}
                      disabled={!productsData?.next_page_info}
                    >
                      Next <ChevronRight size={14} />
                    </button>
                  </div>
                </>
              )}
            </>
          )}
        </>
      )}

      {view === 'processing' && (
        <div className="processing-view">
          <div className="view-header">
            <h2 className="section-title">Processing Images</h2>
          </div>
          <div className="processing-status">
            <Loader2 size={48} className="spin" />
            <p>Processing {processedItems.length} image(s)...</p>
            {jobData && (
              <div className="processing-progress">
                <span className={`status-badge status-${jobData.status}`}>{jobData.status}</span>
                <span>
                  {jobData.items.filter((i: { status: string }) => i.status === 'completed').length} / {jobData.items.length} complete
                </span>
              </div>
            )}
          </div>
        </div>
      )}

      {view === 'results' && jobData && (
        <div className="results-view">
          <div className="view-header">
            <button className="btn btn-secondary" onClick={goBack}>
              <ChevronLeft size={14} /> Back to Products
            </button>
            <h2 className="section-title">Results</h2>
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
              <h3>Push Back to Shopify</h3>
              <div className="push-back-options">
                <label className="push-back-option">
                  <input
                    type="radio"
                    name="pushBackMode"
                    value="add"
                    checked={pushBackMode === 'add'}
                    onChange={() => setPushBackMode('add')}
                  />
                  <span>Add as new images</span>
                </label>
                <label className="push-back-option">
                  <input
                    type="radio"
                    name="pushBackMode"
                    value="replace"
                    checked={pushBackMode === 'replace'}
                    onChange={() => setPushBackMode('replace')}
                  />
                  <span>Replace original images</span>
                </label>
              </div>
              <button
                className="btn btn-primary"
                onClick={handlePushBack}
                disabled={pushingBack || jobData.status === 'failed'}
              >
                {pushingBack ? (
                  <><Loader2 size={14} className="spin" /> Pushing...</>
                ) : (
                  <><ArrowUpRight size={14} /> Push {jobData.items.filter((i: { status: string }) => i.status === 'completed').length} Image(s) to Shopify</>
                )}
              </button>
            </div>
          ) : (
            <div className="push-back-results">
              <h3>Push-Back Results</h3>
              {pushBackResults.map((r, i) => (
                <div key={i} className={`push-back-result push-back-${r.status}`}>
                  {r.status === 'success' ? <Check size={14} /> : <X size={14} />}
                  <span>{r.item_id}: {r.status}</span>
                  {r.error && <span className="push-back-error">{r.error}</span>}
                </div>
              ))}
              <button className="btn btn-secondary" onClick={goBack} style={{ marginTop: '1rem' }}>
                Done
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
