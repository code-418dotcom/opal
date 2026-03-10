import { useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { useQuery, useQueryClient, useMutation } from '@tanstack/react-query';
import {
  Store, Link, Unlink, Image as ImageIcon, ArrowUpRight, Check, X,
  Loader2, ChevronRight, ChevronLeft, Layers, Download, Key, Plus,
  Copy, Trash2, AlertTriangle, Puzzle,
} from 'lucide-react';
import { api } from '../api';
import type { Integration, ShopifyProduct, ShopifyImage, ApiKeyCreateResponse } from '../types';
import CatalogProcessor from './CatalogProcessor';
import HelpTooltip from './HelpTooltip';

type View = 'list' | 'products' | 'processing' | 'results' | 'catalog';

interface ProcessedItem {
  item_id: string;
  filename: string;
  shopify_image_id: number;
  shopify_product_id: number;
}

function ApiKeysSection() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [newKeyName, setNewKeyName] = useState('');
  const [showGenerateForm, setShowGenerateForm] = useState(false);
  const [newlyCreatedKey, setNewlyCreatedKey] = useState<ApiKeyCreateResponse | null>(null);
  const [copied, setCopied] = useState(false);

  const { data: apiKeys, isLoading } = useQuery({
    queryKey: ['api-keys'],
    queryFn: () => api.listApiKeys(),
  });

  const createMutation = useMutation({
    mutationFn: (name?: string) => api.createApiKey(name),
    onSuccess: (data) => {
      setNewlyCreatedKey(data);
      setShowGenerateForm(false);
      setNewKeyName('');
      queryClient.invalidateQueries({ queryKey: ['api-keys'] });
    },
    onError: (err: Error) => {
      alert(err.message || 'Failed to generate API key');
    },
  });

  const revokeMutation = useMutation({
    mutationFn: (keyId: string) => api.revokeApiKey(keyId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['api-keys'] });
    },
  });

  const handleCopy = async () => {
    if (!newlyCreatedKey) return;
    try {
      await navigator.clipboard.writeText(newlyCreatedKey.key);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      const input = document.querySelector('.apikey-reveal-input') as HTMLInputElement;
      if (input) { input.select(); document.execCommand('copy'); setCopied(true); setTimeout(() => setCopied(false), 2000); }
    }
  };

  return (
    <div className="apikeys-section">
      <h2 className="section-title" style={{ marginTop: '2rem' }}>
        <Key size={20} style={{ marginRight: '0.5rem', verticalAlign: 'middle' }} />
        {t('integrations.apiKeys.title', { defaultValue: 'API Keys' })}
      </h2>
      <p className="apikeys-description">{t('integrations.apiKeys.description', { defaultValue: 'Generate API keys to connect plugins and external integrations to your Opal account.' })}</p>

      {newlyCreatedKey && (
        <div className="apikey-reveal">
          <div className="apikey-reveal-header">
            <AlertTriangle size={18} />
            <strong>{t('billing.apiKeys.newKeyTitle', { defaultValue: 'Your new API key' })}</strong>
          </div>
          <p className="apikey-reveal-warning">{t('billing.apiKeys.newKeyWarning', { defaultValue: 'Copy this key now. You won\'t be able to see it again.' })}</p>
          <div className="apikey-reveal-box">
            <input type="text" readOnly value={newlyCreatedKey.key} className="apikey-reveal-input" onClick={(e) => (e.target as HTMLInputElement).select()} />
            <button className="btn btn-sm apikey-copy-btn" onClick={handleCopy}>
              <Copy size={14} />
              {copied ? t('billing.apiKeys.copied', { defaultValue: 'Copied!' }) : t('billing.apiKeys.copyKey', { defaultValue: 'Copy' })}
            </button>
          </div>
          <button className="btn btn-sm apikey-done-btn" onClick={() => setNewlyCreatedKey(null)}>
            {t('billing.apiKeys.done', { defaultValue: 'Done' })}
          </button>
        </div>
      )}

      {showGenerateForm && !newlyCreatedKey && (
        <div className="apikey-generate-form">
          <input
            type="text"
            value={newKeyName}
            onChange={(e) => setNewKeyName(e.target.value)}
            placeholder={t('billing.apiKeys.namePlaceholder', { defaultValue: 'Key name (e.g. WooCommerce Store)' })}
            className="apikey-name-input"
          />
          <div className="apikey-generate-actions">
            <button className="btn btn-primary" onClick={() => createMutation.mutate(newKeyName || undefined)} disabled={createMutation.isPending}>
              {createMutation.isPending ? t('billing.apiKeys.generating', { defaultValue: 'Generating...' }) : t('billing.apiKeys.generateNew', { defaultValue: 'Generate New' })}
            </button>
            <button className="btn btn-secondary" onClick={() => { setShowGenerateForm(false); setNewKeyName(''); }}>
              {t('common.cancel', { defaultValue: 'Cancel' })}
            </button>
          </div>
        </div>
      )}

      {!showGenerateForm && !newlyCreatedKey && (
        <button className="apikey-generate-btn" onClick={() => setShowGenerateForm(true)}>
          <Plus size={16} />
          {t('billing.apiKeys.generateNew', { defaultValue: 'Generate New' })}
        </button>
      )}

      {isLoading ? (
        <p style={{ color: 'rgba(200,205,224,0.6)', padding: '1rem 0' }}>{t('common.loading', { defaultValue: 'Loading...' })}</p>
      ) : apiKeys && apiKeys.length > 0 ? (
        <div className="billing-transactions">
          <table className="billing-tx-table apikeys-table">
            <thead>
              <tr>
                <th>{t('billing.apiKeys.name', { defaultValue: 'Name' })}</th>
                <th>{t('billing.apiKeys.prefix', { defaultValue: 'Key' })}</th>
                <th>{t('billing.apiKeys.created', { defaultValue: 'Created' })}</th>
                <th>{t('billing.apiKeys.lastUsed', { defaultValue: 'Last Used' })}</th>
                <th>{t('billing.apiKeys.actions', { defaultValue: 'Actions' })}</th>
              </tr>
            </thead>
            <tbody>
              {apiKeys.map((key) => (
                <tr key={key.id}>
                  <td>{key.name || '—'}</td>
                  <td><code className="apikey-prefix">{key.prefix}...</code></td>
                  <td>{new Date(key.created_at).toLocaleDateString()}</td>
                  <td>{key.last_used_at ? new Date(key.last_used_at).toLocaleDateString() : t('billing.apiKeys.never', { defaultValue: 'Never' })}</td>
                  <td>
                    <button
                      className="apikey-revoke-btn"
                      onClick={() => { if (confirm(t('billing.apiKeys.revokeConfirm', { defaultValue: 'Revoke this key? Any integrations using it will stop working.' }))) revokeMutation.mutate(key.id); }}
                      disabled={revokeMutation.isPending}
                    >
                      <Trash2 size={14} />
                      {t('billing.apiKeys.revoke', { defaultValue: 'Revoke' })}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="empty-state" style={{ marginTop: '1rem' }}>
          <Key size={48} />
          <p>{t('billing.apiKeys.noKeys', { defaultValue: 'No API keys yet' })}</p>
          <p style={{ fontSize: '0.8rem', color: 'rgba(200,205,224,0.5)' }}>{t('billing.apiKeys.noKeysHint', { defaultValue: 'Generate a key to connect plugins and external integrations.' })}</p>
        </div>
      )}
    </div>
  );
}

export default function IntegrationsPage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [view, setView] = useState<View>('list');
  const [shopDomain, setShopDomain] = useState('');
  const [wcStoreUrl, setWcStoreUrl] = useState('');
  const [etsyShopId, setEtsyShopId] = useState('');
  const [connecting, setConnecting] = useState<string | false>(false);
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
  const [successMsg, setSuccessMsg] = useState<string | null>(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get('shopify') === 'connected') {
      // Clean up URL
      const url = new URL(window.location.href);
      url.searchParams.delete('shopify');
      window.history.replaceState({}, '', url.toString());
      return t('integrations.shopifyConnected', { defaultValue: 'Shopify store connected successfully!' });
    }
    return null;
  });

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

  const handleConnectShopify = async () => {
    if (!shopDomain) return;
    setConnecting('shopify');
    setError(null);
    try {
      const shop = shopDomain.includes('.myshopify.com')
        ? shopDomain
        : `${shopDomain}.myshopify.com`;
      const result = await api.connectShopify(shop);
      window.location.href = result.auth_url;
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : t('integrations.connectionFailed'));
      setConnecting(false);
    }
  };

  const handleConnectWooCommerce = async () => {
    if (!wcStoreUrl) return;
    setConnecting('woocommerce');
    setError(null);
    try {
      const result = await api.connectWooCommerce(wcStoreUrl);
      window.location.href = result.auth_url;
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : t('integrations.connectionFailed'));
      setConnecting(false);
    }
  };

  const handleConnectEtsy = async () => {
    if (!etsyShopId) return;
    setConnecting('etsy');
    setError(null);
    try {
      const result = await api.connectEtsy(etsyShopId);
      window.location.href = result.auth_url;
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : t('integrations.connectionFailed'));
      setConnecting(false);
    }
  };

  const handleDisconnect = async (integrationId: string) => {
    if (!confirm(t('integrations.disconnectConfirm'))) return;
    try {
      await api.disconnectIntegration(integrationId);
      queryClient.invalidateQueries({ queryKey: ['integrations'] });
      setActiveIntegration(null);
      setView('list');
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : t('integrations.disconnectFailed'));
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
      setError(err instanceof Error ? err.message : t('integrations.processingFailed'));
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
    if (view === 'results' || view === 'processing') {
      setView('products');
      setProcessingJobId(null);
      setProcessedItems([]);
      setPushBackResults([]);
      setSelectedProduct(null);
    } else if (view === 'products' || view === 'catalog') {
      setView('list');
      setActiveIntegration(null);
    }
  };

  return (
    <div className="integrations-page">
      {successMsg && (
        <div className="integration-success">
          <span>{successMsg}</span>
          <button onClick={() => setSuccessMsg(null)}>{t('common.dismiss')}</button>
        </div>
      )}
      {error && (
        <div className="integration-error">
          <X size={14} />
          <span>{error}</span>
          <button onClick={() => setError(null)}>{t('common.dismiss')}</button>
        </div>
      )}

      {view === 'list' && (
        <>
          <h2 className="section-title">{t('integrations.connectedStores')} <HelpTooltip text={t('help.connectedStores', 'Your linked webshops. Opal can pull product images, process them, and push them back automatically.')} /></h2>

          {isLoading ? (
            <div className="empty-state"><Loader2 size={24} className="spin" /> {t('common.loading')}</div>
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
                      {t('common.connected')} {new Date(integ.created_at).toLocaleDateString()}
                    </span>
                  </div>
                  <div className="integration-card-actions">
                    <button
                      className="btn btn-primary"
                      onClick={() => handleBrowseProducts(integ)}
                      disabled={integ.status !== 'active'}
                    >
                      <ImageIcon size={14} />
                      {t('integrations.browseProducts')}
                    </button>
                    <button
                      className="btn btn-secondary"
                      onClick={() => { setActiveIntegration(integ); setView('catalog'); }}
                      disabled={integ.status !== 'active'}
                    >
                      <Layers size={14} />
                      Bulk Process
                    </button>
                    <button
                      className="btn btn-danger"
                      onClick={() => handleDisconnect(integ.id)}
                    >
                      <Unlink size={14} />
                      {t('integrations.disconnect')}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-state">
              <Store size={48} />
              <p>{t('integrations.noStores')}</p>
            </div>
          )}

          <h2 className="section-title" style={{ marginTop: '2rem' }}>{t('integrations.connectStore')} <HelpTooltip text={t('help.connectStore', 'Connect your Shopify, Etsy, or WooCommerce store in a few clicks. Opal never accesses customer or payment data.')} /></h2>
          <div className="connect-providers">
            <div className="connect-form">
              <h4>Shopify</h4>
              <div className="connect-input-group">
                <input
                  type="text"
                  placeholder={t('integrations.shopifyPlaceholder')}
                  value={shopDomain}
                  onChange={e => setShopDomain(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && handleConnectShopify()}
                  className="connect-input"
                />
                <button
                  className="btn btn-primary"
                  onClick={handleConnectShopify}
                  disabled={!!connecting || !shopDomain}
                >
                  {connecting === 'shopify' ? (
                    <><Loader2 size={14} className="spin" /> {t('integrations.connecting')}</>
                  ) : (
                    <><Link size={14} /> {t('common.connect', { defaultValue: 'Connect' })}</>
                  )}
                </button>
              </div>
            </div>

            <div className="connect-form">
              <h4>WooCommerce</h4>
              <div className="connect-input-group">
                <input
                  type="text"
                  placeholder={t('integrations.woocommercePlaceholder', { defaultValue: 'https://your-store.com' })}
                  value={wcStoreUrl}
                  onChange={e => setWcStoreUrl(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && handleConnectWooCommerce()}
                  className="connect-input"
                />
                <button
                  className="btn btn-primary"
                  onClick={handleConnectWooCommerce}
                  disabled={!!connecting || !wcStoreUrl}
                >
                  {connecting === 'woocommerce' ? (
                    <><Loader2 size={14} className="spin" /> {t('integrations.connecting')}</>
                  ) : (
                    <><Link size={14} /> {t('common.connect', { defaultValue: 'Connect' })}</>
                  )}
                </button>
              </div>
            </div>

            <div className="connect-form">
              <h4>Etsy</h4>
              <div className="connect-input-group">
                <input
                  type="text"
                  placeholder={t('integrations.etsyPlaceholder', { defaultValue: 'Your Etsy Shop ID' })}
                  value={etsyShopId}
                  onChange={e => setEtsyShopId(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && handleConnectEtsy()}
                  className="connect-input"
                />
                <button
                  className="btn btn-primary"
                  onClick={handleConnectEtsy}
                  disabled={!!connecting || !etsyShopId}
                >
                  {connecting === 'etsy' ? (
                    <><Loader2 size={14} className="spin" /> {t('integrations.connecting')}</>
                  ) : (
                    <><Link size={14} /> {t('common.connect', { defaultValue: 'Connect' })}</>
                  )}
                </button>
              </div>
            </div>
          </div>

          {costs && (
            <p className="connect-cost-info">
              {t('integrations.costInfo', { process: costs.process_image })}
              {costs.push_back > 0 ? t('integrations.costPushBack', { push: costs.push_back }) : t('integrations.costPushBackFree')}
            </p>
          )}

          {/* Plugin Downloads */}
          <h2 className="section-title" style={{ marginTop: '2rem' }}>
            <Puzzle size={20} style={{ marginRight: '0.5rem', verticalAlign: 'middle' }} />
            {t('integrations.plugins.title', { defaultValue: 'Plugins' })}
          </h2>
          <div className="integrations-grid">
            <div className="integration-card plugin-card">
              <div className="integration-card-header">
                <Store size={20} />
                <div>
                  <div className="integration-store-name">WooCommerce Plugin</div>
                  <div className="integration-store-url">{t('integrations.plugins.wcDescription', { defaultValue: 'AI-powered product image enhancement for WooCommerce — background removal, studio scenes, upscaling, and A/B testing.' })}</div>
                </div>
              </div>
              <div className="integration-card-meta">
                <span className="integration-provider">WordPress / WooCommerce</span>
                <span className="integration-date">v1.0.0</span>
              </div>
              <div className="integration-card-actions">
                <a
                  href="https://github.com/code-418dotcom/opal/releases/latest/download/opal-ai-photography.zip"
                  className="btn btn-primary"
                  download
                >
                  <Download size={14} />
                  {t('integrations.plugins.download', { defaultValue: 'Download Plugin' })}
                </a>
                <a
                  href="https://github.com/code-418dotcom/opal/tree/main/plugins/woocommerce#readme"
                  className="btn btn-secondary"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  {t('integrations.plugins.docs', { defaultValue: 'Documentation' })}
                </a>
              </div>
              <div className="plugin-setup-hint">
                <p>{t('integrations.plugins.wcSetup', { defaultValue: 'Upload the ZIP file via WordPress → Plugins → Add New → Upload Plugin. You\'ll need an API key (below) to connect it.' })}</p>
              </div>
            </div>
          </div>

          {/* API Keys */}
          <ApiKeysSection />
        </>
      )}

      {view === 'products' && activeIntegration && (
        <>
          <div className="view-header">
            <button className="btn btn-secondary" onClick={goBack}>
              <ChevronLeft size={14} /> {t('common.back')}
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
                    {selectedImageIds.size === selectedProduct.images.length ? t('integrations.deselectAll') : t('integrations.selectAll')}
                  </button>
                  <button
                    className="btn btn-primary"
                    onClick={handleProcessImages}
                    disabled={selectedProduct.images.length === 0}
                  >
                    <ArrowUpRight size={14} />
                    {selectedImageIds.size > 0 ? t('integrations.processImages', { count: selectedImageIds.size }) : t('integrations.processAll')}
                  </button>
                  <button className="btn btn-secondary" onClick={() => setSelectedProduct(null)}>
                    <X size={14} /> {t('common.cancel')}
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
                <div className="empty-state"><Loader2 size={24} className="spin" /> {t('integrations.loadingProducts')}</div>
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
                            {t('integrations.imageCount', { count: product.images.length })} &middot; {product.status}
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
                      <ChevronLeft size={14} /> {t('common.previous')}
                    </button>
                    <button
                      className="btn btn-secondary"
                      onClick={handleNextPage}
                      disabled={!productsData?.next_page_info}
                    >
                      {t('common.next')} <ChevronRight size={14} />
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
            <h2 className="section-title">{t('integrations.processingImages')}</h2>
          </div>
          <div className="processing-status">
            <Loader2 size={48} className="spin" />
            <p>{t('integrations.processingCount', { count: processedItems.length })}</p>
            {jobData && (
              <div className="processing-progress">
                <span className={`status-badge status-${jobData.status}`}>{jobData.status}</span>
                <span>
                  {jobData.items.filter((i: { status: string }) => i.status === 'completed').length} / {jobData.items.length} {t('integrations.complete')}
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
              <ChevronLeft size={14} /> {t('integrations.backToProducts')}
            </button>
            <h2 className="section-title">{t('results.title')}</h2>
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
              <h3>{t('integrations.pushBackTitle')}</h3>
              <div className="push-back-options">
                <label className="push-back-option">
                  <input
                    type="radio"
                    name="pushBackMode"
                    value="add"
                    checked={pushBackMode === 'add'}
                    onChange={() => setPushBackMode('add')}
                  />
                  <span>{t('integrations.addAsNew')}</span>
                </label>
                <label className="push-back-option">
                  <input
                    type="radio"
                    name="pushBackMode"
                    value="replace"
                    checked={pushBackMode === 'replace'}
                    onChange={() => setPushBackMode('replace')}
                  />
                  <span>{t('integrations.replaceOriginal')}</span>
                </label>
              </div>
              <button
                className="btn btn-primary"
                onClick={handlePushBack}
                disabled={pushingBack || jobData.status === 'failed'}
              >
                {pushingBack ? (
                  <><Loader2 size={14} className="spin" /> {t('integrations.pushing')}</>
                ) : (
                  <><ArrowUpRight size={14} /> {t('integrations.pushImages', { count: jobData.items.filter((i: { status: string }) => i.status === 'completed').length })}</>
                )}
              </button>
            </div>
          ) : (
            <div className="push-back-results">
              <h3>{t('integrations.pushBackResults')}</h3>
              {pushBackResults.map((r, i) => (
                <div key={i} className={`push-back-result push-back-${r.status}`}>
                  {r.status === 'success' ? <Check size={14} /> : <X size={14} />}
                  <span>{r.item_id}: {r.status}</span>
                  {r.error && <span className="push-back-error">{r.error}</span>}
                </div>
              ))}
              <button className="btn btn-secondary" onClick={goBack} style={{ marginTop: '1rem' }}>
                {t('common.done')}
              </button>
            </div>
          )}
        </div>
      )}

      {view === 'catalog' && activeIntegration && (
        <CatalogProcessor
          integration={activeIntegration}
          onBack={goBack}
        />
      )}
    </div>
  );
}
