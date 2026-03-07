import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  ArrowLeft, Layers, Play, Square, Loader2,
  Check, X, AlertTriangle, ImageIcon, Package,
} from 'lucide-react';
import { api } from '../api';
import type { Integration } from '../types';

type CatalogView = 'estimate' | 'running' | 'history';

interface Props {
  integration: Integration;
  onBack: () => void;
}

export default function CatalogProcessor({ integration, onBack }: Props) {
  const queryClient = useQueryClient();
  const [catalogView, setCatalogView] = useState<CatalogView>('estimate');
  const [activeCatalogJobId, setActiveCatalogJobId] = useState<string | null>(null);
  const [selectedProducts, setSelectedProducts] = useState<Set<string>>(new Set());
  const [selectAll, setSelectAll] = useState(true);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { data: estimate, isLoading: estimating } = useQuery({
    queryKey: ['catalog-estimate', integration.id],
    queryFn: () => api.estimateCatalog(integration.id),
    enabled: catalogView === 'estimate',
  });

  const { data: catalogStatus } = useQuery({
    queryKey: ['catalog-status', integration.id, activeCatalogJobId],
    queryFn: () => api.getCatalogJobStatus(integration.id, activeCatalogJobId!),
    enabled: catalogView === 'running' && !!activeCatalogJobId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === 'processing' || status === 'created' ? 3000 : false;
    },
  });

  const { data: historyData } = useQuery({
    queryKey: ['catalog-history', integration.id],
    queryFn: () => api.listCatalogJobs(integration.id),
    enabled: catalogView === 'history',
  });

  const toggleProduct = (id: string) => {
    setSelectedProducts(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
    setSelectAll(false);
  };

  const handleSelectAll = () => {
    if (selectAll) {
      setSelectedProducts(new Set());
      setSelectAll(false);
    } else {
      setSelectedProducts(new Set(estimate?.products.map(p => p.id) || []));
      setSelectAll(true);
    }
  };

  const getSelectedCount = () => {
    if (selectAll && selectedProducts.size === 0) return estimate?.products.length || 0;
    return selectedProducts.size;
  };

  const getSelectedImageCount = () => {
    if (!estimate) return 0;
    if (selectAll && selectedProducts.size === 0) return estimate.total_images;
    return estimate.products
      .filter(p => selectedProducts.has(p.id))
      .reduce((sum, p) => sum + p.image_count, 0);
  };

  const handleStart = async () => {
    setStarting(true);
    setError(null);
    try {
      const productIds = selectAll && selectedProducts.size === 0
        ? undefined
        : Array.from(selectedProducts);

      const result = await api.startCatalogJob(integration.id, {
        product_ids: productIds,
      });
      setActiveCatalogJobId(result.catalog_job_id);
      setCatalogView('running');
      queryClient.invalidateQueries({ queryKey: ['balance'] });
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to start catalog processing');
    } finally {
      setStarting(false);
    }
  };

  const handleCancel = async () => {
    if (!activeCatalogJobId) return;
    try {
      await api.cancelCatalogJob(integration.id, activeCatalogJobId);
      queryClient.invalidateQueries({ queryKey: ['catalog-status'] });
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to cancel');
    }
  };

  const handleViewJob = (jobId: string) => {
    setActiveCatalogJobId(jobId);
    setCatalogView('running');
  };

  const progressPercent = catalogStatus
    ? Math.round(((catalogStatus.processed_count + catalogStatus.failed_count + catalogStatus.skipped_count) / Math.max(catalogStatus.total_products, 1)) * 100)
    : 0;

  return (
    <div className="catalog-processor">
      <div className="catalog-header">
        <button className="btn btn-ghost" onClick={onBack}>
          <ArrowLeft size={16} /> Back
        </button>
        <h2>
          <Layers size={20} />
          Bulk Process: {integration.provider_metadata?.shop_name || integration.store_url}
        </h2>
        <div className="catalog-tabs">
          <button
            className={`catalog-tab ${catalogView === 'estimate' ? 'active' : ''}`}
            onClick={() => setCatalogView('estimate')}
          >
            Estimate
          </button>
          <button
            className={`catalog-tab ${catalogView === 'history' ? 'active' : ''}`}
            onClick={() => setCatalogView('history')}
          >
            History
          </button>
        </div>
      </div>

      {error && (
        <div className="catalog-error">
          <AlertTriangle size={14} />
          <span>{error}</span>
          <button onClick={() => setError(null)}>
            <X size={14} />
          </button>
        </div>
      )}

      {catalogView === 'estimate' && (
        <div className="catalog-estimate">
          {estimating ? (
            <div className="catalog-loading">
              <Loader2 size={24} className="spin" />
              <p>Scanning your catalog...</p>
            </div>
          ) : estimate ? (
            <>
              <div className="catalog-summary">
                <div className="catalog-stat">
                  <Package size={20} />
                  <div>
                    <span className="catalog-stat-value">{estimate.products_with_images}</span>
                    <span className="catalog-stat-label">Products with images</span>
                  </div>
                </div>
                <div className="catalog-stat">
                  <ImageIcon size={20} />
                  <div>
                    <span className="catalog-stat-value">{estimate.total_images}</span>
                    <span className="catalog-stat-label">Total images</span>
                  </div>
                </div>
                <div className="catalog-stat">
                  <Layers size={20} />
                  <div>
                    <span className="catalog-stat-value">{estimate.tokens_required}</span>
                    <span className="catalog-stat-label">Tokens required</span>
                  </div>
                </div>
              </div>

              <div className="catalog-product-list">
                <div className="catalog-product-list-header">
                  <label className="catalog-select-all">
                    <input
                      type="checkbox"
                      checked={selectAll && selectedProducts.size === 0 || selectedProducts.size === estimate.products.length}
                      onChange={handleSelectAll}
                    />
                    Select all ({estimate.products.length} products)
                  </label>
                  <span className="catalog-selection-info">
                    {getSelectedCount()} selected, {getSelectedImageCount()} images
                  </span>
                </div>
                <div className="catalog-products-scroll">
                  {estimate.products.map(product => (
                    <label key={product.id} className="catalog-product-row">
                      <input
                        type="checkbox"
                        checked={selectAll && selectedProducts.size === 0 || selectedProducts.has(product.id)}
                        onChange={() => toggleProduct(product.id)}
                      />
                      <span className="catalog-product-title">{product.title}</span>
                      <span className="catalog-product-images">
                        {product.image_count} image{product.image_count !== 1 ? 's' : ''}
                      </span>
                    </label>
                  ))}
                </div>
              </div>

              <div className="catalog-actions">
                <button
                  className="btn btn-primary btn-lg"
                  onClick={handleStart}
                  disabled={starting || getSelectedCount() === 0}
                >
                  {starting ? (
                    <><Loader2 size={16} className="spin" /> Starting...</>
                  ) : (
                    <><Play size={16} /> Process {getSelectedCount()} products ({getSelectedImageCount()} images)</>
                  )}
                </button>
              </div>
            </>
          ) : (
            <div className="catalog-loading">
              <AlertTriangle size={24} />
              <p>Could not scan catalog. Check your store connection.</p>
            </div>
          )}
        </div>
      )}

      {catalogView === 'running' && catalogStatus && (
        <div className="catalog-running">
          <div className="catalog-progress-header">
            <h3>
              {catalogStatus.status === 'processing' && <Loader2 size={16} className="spin" />}
              {catalogStatus.status === 'completed' && <Check size={16} className="text-success" />}
              {catalogStatus.status === 'failed' && <X size={16} className="text-danger" />}
              {catalogStatus.status === 'canceled' && <Square size={16} />}
              {' '}Catalog Job — {catalogStatus.status}
            </h3>
          </div>

          <div className="catalog-progress-bar-container">
            <div className="catalog-progress-bar" style={{ width: `${progressPercent}%` }} />
          </div>

          <div className="catalog-progress-stats">
            <span className="stat-processed">{catalogStatus.processed_count} processed</span>
            <span className="stat-failed">{catalogStatus.failed_count} failed</span>
            <span className="stat-skipped">{catalogStatus.skipped_count} skipped</span>
            <span className="stat-total">of {catalogStatus.total_products} products</span>
            <span className="stat-tokens">{catalogStatus.tokens_spent} tokens used</span>
          </div>

          {catalogStatus.error_message && (
            <div className="catalog-error-message">
              <AlertTriangle size={14} /> {catalogStatus.error_message}
            </div>
          )}

          {catalogStatus.status === 'processing' && (
            <div className="catalog-actions">
              <button className="btn btn-danger" onClick={handleCancel}>
                <Square size={14} /> Cancel
              </button>
            </div>
          )}

          {catalogStatus.products && (
            <div className="catalog-product-status-list">
              <h4>Products</h4>
              {catalogStatus.products.map(p => (
                <div key={p.id} className={`catalog-product-status catalog-product-${p.status}`}>
                  <span className="catalog-product-status-icon">
                    {p.status === 'completed' && <Check size={12} />}
                    {p.status === 'failed' && <X size={12} />}
                    {p.status === 'processing' && <Loader2 size={12} className="spin" />}
                    {p.status === 'pending' && <span className="dot" />}
                    {p.status === 'skipped' && <span>—</span>}
                  </span>
                  <span className="catalog-product-status-title">{p.product_title || p.product_id}</span>
                  <span className="catalog-product-status-images">{p.image_count} imgs</span>
                  {p.error_message && <span className="catalog-product-status-error">{p.error_message}</span>}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {catalogView === 'history' && (
        <div className="catalog-history">
          {historyData?.catalog_jobs.length ? (
            historyData.catalog_jobs.map(job => (
              <div
                key={job.id}
                className={`catalog-history-card catalog-history-${job.status}`}
                onClick={() => handleViewJob(job.id)}
              >
                <div className="catalog-history-header">
                  <span className={`catalog-badge catalog-badge-${job.status}`}>{job.status}</span>
                  <span className="catalog-history-date">{new Date(job.created_at).toLocaleString()}</span>
                </div>
                <div className="catalog-history-stats">
                  <span>{job.total_products} products</span>
                  <span>{job.total_images} images</span>
                  <span>{job.processed_count} done</span>
                  {job.failed_count > 0 && <span className="text-danger">{job.failed_count} failed</span>}
                  <span>{job.tokens_spent} tokens</span>
                </div>
              </div>
            ))
          ) : (
            <div className="catalog-loading">
              <p>No catalog jobs yet.</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
