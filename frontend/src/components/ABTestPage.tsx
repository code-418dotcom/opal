import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  FlaskConical, Play, ArrowLeftRight, Trophy, Square, Loader2,
  Check, X, AlertTriangle, TrendingUp, BarChart3, Plus,
} from 'lucide-react';
import { api } from '../api';
import HelpTooltip from './HelpTooltip';


type ABView = 'list' | 'detail' | 'create' | 'metrics';

export default function ABTestPage() {
  const queryClient = useQueryClient();
  const [view, setView] = useState<ABView>('list');
  const [activeTestId, setActiveTestId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // ── Create form state ──
  const [createForm, setCreateForm] = useState({
    integration_id: '',
    product_id: '',
    product_title: '',
    variant_a_job_item_id: '',
    variant_b_job_item_id: '',
    variant_a_label: 'Variant A',
    variant_b_label: 'Variant B',
    original_image_id: '',
  });
  const [creating, setCreating] = useState(false);

  // ── Metrics form state ──
  const [metricForm, setMetricForm] = useState({
    variant: 'a',
    date: new Date().toISOString().split('T')[0],
    views: 0,
    clicks: 0,
    conversions: 0,
    revenue_cents: 0,
  });

  const { data: testsData, isLoading } = useQuery({
    queryKey: ['ab-tests'],
    queryFn: () => api.listABTests(),
    enabled: view === 'list',
  });

  const { data: testDetail } = useQuery({
    queryKey: ['ab-test-detail', activeTestId],
    queryFn: () => api.getABTest(activeTestId!),
    enabled: (view === 'detail' || view === 'metrics') && !!activeTestId,
    refetchInterval: (query) => {
      return query.state.data?.status === 'running' ? 10000 : false;
    },
  });

  const { data: integrations } = useQuery({
    queryKey: ['integrations'],
    queryFn: () => api.listIntegrations(),
    enabled: view === 'create',
  });

  const handleCreate = async () => {
    setCreating(true);
    setError(null);
    try {
      const test = await api.createABTest({
        ...createForm,
        original_image_id: createForm.original_image_id || undefined,
      });
      setActiveTestId(test.id);
      setView('detail');
      queryClient.invalidateQueries({ queryKey: ['ab-tests'] });
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to create test');
    } finally {
      setCreating(false);
    }
  };

  const handleStart = async () => {
    if (!activeTestId) return;
    try {
      await api.startABTest(activeTestId);
      queryClient.invalidateQueries({ queryKey: ['ab-test-detail', activeTestId] });
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to start test');
    }
  };

  const handleSwap = async () => {
    if (!activeTestId) return;
    try {
      await api.swapABTestVariant(activeTestId);
      queryClient.invalidateQueries({ queryKey: ['ab-test-detail', activeTestId] });
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to swap variant');
    }
  };

  const handleConclude = async (winner: string) => {
    if (!activeTestId) return;
    try {
      await api.concludeABTest(activeTestId, winner);
      queryClient.invalidateQueries({ queryKey: ['ab-test-detail', activeTestId] });
      queryClient.invalidateQueries({ queryKey: ['ab-tests'] });
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to conclude test');
    }
  };

  const handleCancel = async () => {
    if (!activeTestId) return;
    try {
      await api.cancelABTest(activeTestId);
      queryClient.invalidateQueries({ queryKey: ['ab-test-detail', activeTestId] });
      queryClient.invalidateQueries({ queryKey: ['ab-tests'] });
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to cancel test');
    }
  };

  const handleRecordMetric = async () => {
    if (!activeTestId) return;
    try {
      await api.recordABTestMetric(activeTestId, metricForm);
      queryClient.invalidateQueries({ queryKey: ['ab-test-detail', activeTestId] });
      setError(null);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to record metric');
    }
  };

  const openTest = (testId: string) => {
    setActiveTestId(testId);
    setView('detail');
  };

  const statusIcon = (status: string) => {
    switch (status) {
      case 'running': return <Loader2 size={14} className="spin" />;
      case 'concluded': return <Trophy size={14} className="text-success" />;
      case 'canceled': return <X size={14} />;
      default: return <FlaskConical size={14} />;
    }
  };

  return (
    <div className="ab-test-page">
      <div className="ab-header">
        <h2><FlaskConical size={20} /> A/B Image Tests <HelpTooltip text="Test two different product images on your live store to see which one gets more clicks and sales." /></h2>
        {view !== 'list' && (
          <button className="btn btn-ghost" onClick={() => { setView('list'); setActiveTestId(null); }}>
            Back to list
          </button>
        )}
        {view === 'list' && (
          <button className="btn btn-primary" onClick={() => setView('create')}>
            <Plus size={14} /> New Test
          </button>
        )}
      </div>

      {error && (
        <div className="ab-error">
          <AlertTriangle size={14} />
          <span>{error}</span>
          <button onClick={() => setError(null)}><X size={14} /></button>
        </div>
      )}

      {/* ── List View ── */}
      {view === 'list' && (
        <div className="ab-list">
          {isLoading ? (
            <div className="ab-loading"><Loader2 size={24} className="spin" /> Loading tests...</div>
          ) : testsData?.tests.length ? (
            testsData.tests.map(test => (
              <div key={test.id} className={`ab-card ab-card-${test.status}`} onClick={() => openTest(test.id)}>
                <div className="ab-card-header">
                  {statusIcon(test.status)}
                  <span className="ab-card-title">{test.product_title || `Product ${test.product_id}`}</span>
                  <span className={`ab-badge ab-badge-${test.status}`}>{test.status}</span>
                </div>
                <div className="ab-card-meta">
                  <span>{test.variant_a_label} vs {test.variant_b_label}</span>
                  {test.winner && <span className="ab-winner">Winner: Variant {test.winner.toUpperCase()}</span>}
                  <span className="ab-card-date">{new Date(test.created_at).toLocaleDateString()}</span>
                </div>
              </div>
            ))
          ) : (
            <div className="ab-empty">
              <FlaskConical size={48} />
              <p>No A/B tests yet. Create one to compare image variants.</p>
            </div>
          )}
        </div>
      )}

      {/* ── Create View ── */}
      {view === 'create' && (
        <div className="ab-create">
          <h3>Create A/B Test</h3>
          <p className="ab-hint">Compare two processed image variants for a product. Enter the job item IDs from your processed jobs.</p>
          <div className="ab-form">
            <label>
              Integration
              <select
                value={createForm.integration_id}
                onChange={e => setCreateForm(f => ({ ...f, integration_id: e.target.value }))}
              >
                <option value="">Select store...</option>
                {integrations?.map(i => (
                  <option key={i.id} value={i.id}>
                    {i.provider_metadata?.shop_name || i.store_url} ({i.provider})
                  </option>
                ))}
              </select>
            </label>
            <label>
              Product ID (from store)
              <input
                type="text"
                value={createForm.product_id}
                onChange={e => setCreateForm(f => ({ ...f, product_id: e.target.value }))}
                placeholder="e.g. 1234567890"
              />
            </label>
            <label>
              Product Title
              <input
                type="text"
                value={createForm.product_title}
                onChange={e => setCreateForm(f => ({ ...f, product_title: e.target.value }))}
                placeholder="e.g. Blue T-Shirt"
              />
            </label>
            <div className="ab-form-row">
              <label>
                Variant A — Job Item ID
                <input
                  type="text"
                  value={createForm.variant_a_job_item_id}
                  onChange={e => setCreateForm(f => ({ ...f, variant_a_job_item_id: e.target.value }))}
                  placeholder="item_..."
                />
              </label>
              <label>
                Variant A Label
                <input
                  type="text"
                  value={createForm.variant_a_label}
                  onChange={e => setCreateForm(f => ({ ...f, variant_a_label: e.target.value }))}
                />
              </label>
            </div>
            <div className="ab-form-row">
              <label>
                Variant B — Job Item ID
                <input
                  type="text"
                  value={createForm.variant_b_job_item_id}
                  onChange={e => setCreateForm(f => ({ ...f, variant_b_job_item_id: e.target.value }))}
                  placeholder="item_..."
                />
              </label>
              <label>
                Variant B Label
                <input
                  type="text"
                  value={createForm.variant_b_label}
                  onChange={e => setCreateForm(f => ({ ...f, variant_b_label: e.target.value }))}
                />
              </label>
            </div>
            <label>
              Original Image ID (optional, for replacement)
              <input
                type="text"
                value={createForm.original_image_id}
                onChange={e => setCreateForm(f => ({ ...f, original_image_id: e.target.value }))}
                placeholder="Store image ID to replace"
              />
            </label>
            <button
              className="btn btn-primary"
              onClick={handleCreate}
              disabled={creating || !createForm.integration_id || !createForm.product_id || !createForm.variant_a_job_item_id || !createForm.variant_b_job_item_id}
            >
              {creating ? <><Loader2 size={14} className="spin" /> Creating...</> : <><Plus size={14} /> Create Test</>}
            </button>
          </div>
        </div>
      )}

      {/* ── Detail View ── */}
      {view === 'detail' && testDetail && (
        <div className="ab-detail">
          <div className="ab-detail-header">
            <h3>{testDetail.product_title || `Product ${testDetail.product_id}`}</h3>
            <span className={`ab-badge ab-badge-${testDetail.status}`}>{testDetail.status}</span>
          </div>

          <div className="ab-variants">
            <div className={`ab-variant ${testDetail.active_variant === 'a' ? 'ab-variant-active' : ''}`}>
              <div className="ab-variant-header">
                <span className="ab-variant-label">{testDetail.variant_a_label}</span>
                {testDetail.active_variant === 'a' && <span className="ab-live-badge">LIVE</span>}
                {testDetail.winner === 'a' && <Trophy size={14} className="text-success" />}
              </div>
              <div className="ab-variant-stats">
                {testDetail.metrics?.a ? (
                  <>
                    <div><span className="ab-stat-value">{testDetail.metrics.a.views}</span> views</div>
                    <div><span className="ab-stat-value">{testDetail.metrics.a.clicks}</span> clicks</div>
                    <div><span className="ab-stat-value">{testDetail.metrics.a.conversions}</span> conversions</div>
                    {testDetail.significance?.conversion_rate_a !== undefined && (
                      <div><span className="ab-stat-value">{testDetail.significance.conversion_rate_a}%</span> conv. rate</div>
                    )}
                  </>
                ) : (
                  <div className="ab-no-data">No data yet</div>
                )}
              </div>
            </div>

            <div className="ab-vs">VS</div>

            <div className={`ab-variant ${testDetail.active_variant === 'b' ? 'ab-variant-active' : ''}`}>
              <div className="ab-variant-header">
                <span className="ab-variant-label">{testDetail.variant_b_label}</span>
                {testDetail.active_variant === 'b' && <span className="ab-live-badge">LIVE</span>}
                {testDetail.winner === 'b' && <Trophy size={14} className="text-success" />}
              </div>
              <div className="ab-variant-stats">
                {testDetail.metrics?.b ? (
                  <>
                    <div><span className="ab-stat-value">{testDetail.metrics.b.views}</span> views</div>
                    <div><span className="ab-stat-value">{testDetail.metrics.b.clicks}</span> clicks</div>
                    <div><span className="ab-stat-value">{testDetail.metrics.b.conversions}</span> conversions</div>
                    {testDetail.significance?.conversion_rate_b !== undefined && (
                      <div><span className="ab-stat-value">{testDetail.significance.conversion_rate_b}%</span> conv. rate</div>
                    )}
                  </>
                ) : (
                  <div className="ab-no-data">No data yet</div>
                )}
              </div>
            </div>
          </div>

          {/* Significance indicator */}
          {testDetail.significance && (
            <div className={`ab-significance ${testDetail.significance.confident ? 'ab-significant' : ''}`}>
              <BarChart3 size={16} />
              <span>{testDetail.significance.message}</span>
              {testDetail.significance.lift_percent !== null && (
                <span className="ab-lift">
                  <TrendingUp size={14} />
                  {testDetail.significance.lift_percent > 0 ? '+' : ''}{testDetail.significance.lift_percent}% lift
                </span>
              )}
            </div>
          )}

          {/* Actions */}
          <div className="ab-actions">
            {testDetail.status === 'created' && (
              <button className="btn btn-primary" onClick={handleStart}>
                <Play size={14} /> Start Test
              </button>
            )}
            {testDetail.status === 'running' && (
              <>
                <button className="btn btn-secondary" onClick={handleSwap}>
                  <ArrowLeftRight size={14} /> Swap Variant
                </button>
                <button className="btn btn-primary" onClick={() => handleConclude('a')}>
                  <Trophy size={14} /> Pick A as Winner
                </button>
                <button className="btn btn-primary" onClick={() => handleConclude('b')}>
                  <Trophy size={14} /> Pick B as Winner
                </button>
                <button className="btn btn-danger" onClick={handleCancel}>
                  <Square size={14} /> Cancel
                </button>
              </>
            )}
            {testDetail.status === 'running' && (
              <button className="btn btn-ghost" onClick={() => setView('metrics')}>
                <BarChart3 size={14} /> Record Metrics
              </button>
            )}
          </div>
        </div>
      )}

      {/* ── Metrics Entry View ── */}
      {view === 'metrics' && testDetail && (
        <div className="ab-metrics-entry">
          <h3>Record Metrics — {testDetail.product_title || testDetail.product_id}</h3>
          <p className="ab-hint">Enter daily performance data from your store analytics.</p>
          <div className="ab-form">
            <div className="ab-form-row">
              <label>
                Variant
                <select
                  value={metricForm.variant}
                  onChange={e => setMetricForm(f => ({ ...f, variant: e.target.value }))}
                >
                  <option value="a">{testDetail.variant_a_label}</option>
                  <option value="b">{testDetail.variant_b_label}</option>
                </select>
              </label>
              <label>
                Date
                <input
                  type="date"
                  value={metricForm.date}
                  onChange={e => setMetricForm(f => ({ ...f, date: e.target.value }))}
                />
              </label>
            </div>
            <div className="ab-form-row">
              <label>
                Views
                <input type="number" min="0" value={metricForm.views}
                  onChange={e => setMetricForm(f => ({ ...f, views: parseInt(e.target.value) || 0 }))} />
              </label>
              <label>
                Clicks
                <input type="number" min="0" value={metricForm.clicks}
                  onChange={e => setMetricForm(f => ({ ...f, clicks: parseInt(e.target.value) || 0 }))} />
              </label>
              <label>
                Conversions
                <input type="number" min="0" value={metricForm.conversions}
                  onChange={e => setMetricForm(f => ({ ...f, conversions: parseInt(e.target.value) || 0 }))} />
              </label>
              <label>
                Revenue (cents)
                <input type="number" min="0" value={metricForm.revenue_cents}
                  onChange={e => setMetricForm(f => ({ ...f, revenue_cents: parseInt(e.target.value) || 0 }))} />
              </label>
            </div>
            <div className="ab-form-actions">
              <button className="btn btn-primary" onClick={handleRecordMetric}>
                <Check size={14} /> Save Metric
              </button>
              <button className="btn btn-ghost" onClick={() => setView('detail')}>
                Back to Test
              </button>
            </div>
          </div>

          {testDetail.daily_metrics?.length > 0 && (
            <div className="ab-metrics-table">
              <h4>Recorded Metrics</h4>
              <table>
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Variant</th>
                    <th>Views</th>
                    <th>Clicks</th>
                    <th>Conv.</th>
                    <th>Revenue</th>
                  </tr>
                </thead>
                <tbody>
                  {testDetail.daily_metrics.map(m => (
                    <tr key={m.id}>
                      <td>{m.date}</td>
                      <td>{m.variant === 'a' ? testDetail.variant_a_label : testDetail.variant_b_label}</td>
                      <td>{m.views}</td>
                      <td>{m.clicks}</td>
                      <td>{m.conversions}</td>
                      <td>{(m.revenue_cents / 100).toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
