import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Settings, Users, Server, Eye, EyeOff, Save, Trash2, Plus, Shield, ShieldOff,
  X, Check, Loader2, Coins, BarChart3, Briefcase, CreditCard, Activity, Link,
  Package, Edit2,
} from 'lucide-react';
import { api } from '../api';
import type {
  AdminSetting, AdminUser, AdminJob, AdminTokenPackage, AdminTransaction,
  AdminPayment, AdminIntegration, PlatformStats,
} from '../types';

type AdminTab = 'dashboard' | 'users' | 'jobs' | 'packages' | 'activity' | 'integrations' | 'settings' | 'system';

const truncateId = (id: string) => id.length > 12 ? id.slice(0, 12) + '...' : id;
const formatMoney = (cents: number) => `\u20AC${(cents / 100).toFixed(2)}`;
const formatDate = (d: string) => new Date(d).toLocaleDateString();

const statusColor = (status: string): React.CSSProperties => {
  const s = status.toLowerCase();
  if (['completed', 'active', 'paid', 'connected', 'succeeded'].includes(s))
    return { background: '#16a34a22', color: '#22c55e', border: '1px solid #22c55e44' };
  if (['processing', 'pending', 'open'].includes(s))
    return { background: '#eab30822', color: '#eab308', border: '1px solid #eab30844' };
  if (['failed', 'error', 'disconnected', 'canceled', 'expired'].includes(s))
    return { background: '#ef444422', color: '#ef4444', border: '1px solid #ef444444' };
  return { background: '#64748b22', color: '#94a3b8', border: '1px solid #64748b44' };
};

const badgeStyle = (status: string): React.CSSProperties => ({
  ...statusColor(status),
  padding: '2px 8px',
  borderRadius: '9999px',
  fontSize: '0.75rem',
  fontWeight: 600,
  display: 'inline-block',
  textTransform: 'capitalize',
});

export default function AdminPage() {
  const [activeTab, setActiveTab] = useState<AdminTab>('dashboard');

  const tabs: { id: AdminTab; label: string; icon: React.ComponentType<{ size?: number }> }[] = [
    { id: 'dashboard', label: 'Dashboard', icon: BarChart3 },
    { id: 'users', label: 'Users', icon: Users },
    { id: 'jobs', label: 'Jobs', icon: Briefcase },
    { id: 'packages', label: 'Packages', icon: Package },
    { id: 'activity', label: 'Activity', icon: Activity },
    { id: 'integrations', label: 'Integrations', icon: Link },
    { id: 'settings', label: 'Settings', icon: Settings },
    { id: 'system', label: 'System', icon: Server },
  ];

  return (
    <div className="admin-page">
      <div className="admin-tabs">
        {tabs.map(tab => (
          <button
            key={tab.id}
            className={`admin-tab ${activeTab === tab.id ? 'active' : ''}`}
            onClick={() => setActiveTab(tab.id)}
          >
            <tab.icon size={16} />
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === 'dashboard' && <DashboardPanel />}
      {activeTab === 'users' && <UsersPanel />}
      {activeTab === 'jobs' && <JobsPanel />}
      {activeTab === 'packages' && <PackagesPanel />}
      {activeTab === 'activity' && <ActivityPanel />}
      {activeTab === 'integrations' && <IntegrationsPanel />}
      {activeTab === 'settings' && <SettingsPanel />}
      {activeTab === 'system' && <SystemPanel />}
    </div>
  );
}

// ── Dashboard Panel ──────────────────────────────────────────────

function DashboardPanel() {
  const { data: stats, isLoading } = useQuery<PlatformStats>({
    queryKey: ['admin-stats'],
    queryFn: () => api.getPlatformStats(),
  });

  if (isLoading) {
    return <div className="empty-state"><Loader2 size={24} className="spin" /> Loading stats...</div>;
  }

  if (!stats) return null;

  const cards = [
    { label: 'Total Users', value: stats.total_users, icon: Users, color: '#6366f1' },
    { label: 'Total Jobs', value: stats.total_jobs, icon: Briefcase, color: '#06b6d4' },
    { label: 'Tokens in Circulation', value: stats.total_tokens_in_circulation, icon: Coins, color: '#eab308' },
    { label: 'Tokens Spent', value: stats.total_tokens_spent, icon: Coins, color: '#f97316' },
    { label: 'Revenue', value: formatMoney(stats.total_revenue_cents), icon: CreditCard, color: '#22c55e' },
  ];

  return (
    <div className="admin-dashboard-panel">
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
        gap: '1rem',
        marginBottom: '1.5rem',
      }}>
        {cards.map(card => (
          <div key={card.label} style={{
            background: 'rgba(255,255,255,0.03)',
            border: '1px solid rgba(255,255,255,0.08)',
            borderRadius: '12px',
            padding: '1.25rem',
            display: 'flex',
            flexDirection: 'column',
            gap: '0.5rem',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#94a3b8', fontSize: '0.8rem' }}>
              <card.icon size={16} style={{ color: card.color }} />
              {card.label}
            </div>
            <div style={{ fontSize: '1.75rem', fontWeight: 700, color: '#f1f5f9' }}>
              {card.value}
            </div>
          </div>
        ))}
      </div>

      {stats.jobs_by_status && Object.keys(stats.jobs_by_status).length > 0 && (
        <div>
          <h3 className="settings-category-title">Jobs by Status</h3>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginTop: '0.75rem' }}>
            {Object.entries(stats.jobs_by_status).map(([status, count]) => (
              <span key={status} style={{
                ...badgeStyle(status),
                fontSize: '0.85rem',
                padding: '4px 12px',
              }}>
                {status}: {count}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Settings Panel ──────────────────────────────────────────────────

function SettingsPanel() {
  const queryClient = useQueryClient();
  const [editingKey, setEditingKey] = useState<string | null>(null);
  const [editValue, setEditValue] = useState('');
  const [revealedKeys, setRevealedKeys] = useState<Set<string>>(new Set());
  const [saving, setSaving] = useState(false);
  const [showAdd, setShowAdd] = useState(false);
  const [newKey, setNewKey] = useState('');
  const [newCategory, setNewCategory] = useState('general');
  const [newIsSecret, setNewIsSecret] = useState(false);
  const [newDescription, setNewDescription] = useState('');
  const [error, setError] = useState<string | null>(null);

  const { data: settings, isLoading } = useQuery({
    queryKey: ['admin-settings'],
    queryFn: () => api.listAdminSettings(),
  });

  const grouped = (settings || []).reduce<Record<string, AdminSetting[]>>((acc, s) => {
    (acc[s.category] = acc[s.category] || []).push(s);
    return acc;
  }, {});

  const handleEdit = (setting: AdminSetting) => {
    setEditingKey(setting.key);
    setEditValue(setting.is_secret ? '' : setting.value);
    setError(null);
  };

  const handleSave = async (key: string) => {
    setSaving(true);
    setError(null);
    try {
      await api.updateAdminSetting(key, editValue);
      setEditingKey(null);
      setEditValue('');
      queryClient.invalidateQueries({ queryKey: ['admin-settings'] });
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Save failed');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (key: string) => {
    if (!confirm(`Delete setting "${key}"? This cannot be undone.`)) return;
    try {
      await api.deleteAdminSetting(key);
      queryClient.invalidateQueries({ queryKey: ['admin-settings'] });
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Delete failed');
    }
  };

  const handleAdd = async () => {
    if (!newKey) return;
    setError(null);
    try {
      await api.createAdminSetting({
        key: newKey,
        category: newCategory,
        is_secret: newIsSecret,
        description: newDescription || undefined,
      });
      setShowAdd(false);
      setNewKey('');
      setNewCategory('general');
      setNewIsSecret(false);
      setNewDescription('');
      queryClient.invalidateQueries({ queryKey: ['admin-settings'] });
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Create failed');
    }
  };

  const toggleReveal = (key: string) => {
    setRevealedKeys(prev => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const categoryLabels: Record<string, string> = {
    shopify: 'Shopify Integration',
    payments: 'Payment Provider (Mollie)',
    ai: 'AI Providers',
    security: 'Security',
    general: 'General',
  };

  if (isLoading) {
    return <div className="empty-state"><Loader2 size={24} className="spin" /> Loading settings...</div>;
  }

  return (
    <div className="admin-settings-panel">
      {error && (
        <div className="integration-error">
          <X size={14} />
          <span>{error}</span>
          <button onClick={() => setError(null)}>Dismiss</button>
        </div>
      )}

      {Object.entries(grouped).map(([category, categorySettings]) => (
        <div key={category} className="settings-category">
          <h3 className="settings-category-title">
            {categoryLabels[category] || category}
          </h3>
          <div className="settings-list">
            {categorySettings.map(setting => (
              <div key={setting.key} className="setting-row">
                <div className="setting-info">
                  <div className="setting-key">{setting.key}</div>
                  {setting.description && (
                    <div className="setting-description">{setting.description}</div>
                  )}
                </div>

                {editingKey === setting.key ? (
                  <div className="setting-edit">
                    <input
                      type={setting.is_secret ? 'password' : 'text'}
                      value={editValue}
                      onChange={e => setEditValue(e.target.value)}
                      placeholder={setting.is_secret ? 'Enter new value...' : 'Value'}
                      className="setting-input"
                      autoFocus
                      onKeyDown={e => {
                        if (e.key === 'Enter') handleSave(setting.key);
                        if (e.key === 'Escape') setEditingKey(null);
                      }}
                    />
                    <button
                      className="btn btn-primary btn-sm"
                      onClick={() => handleSave(setting.key)}
                      disabled={saving}
                    >
                      {saving ? <Loader2 size={14} className="spin" /> : <Save size={14} />}
                    </button>
                    <button
                      className="btn btn-secondary btn-sm"
                      onClick={() => setEditingKey(null)}
                    >
                      <X size={14} />
                    </button>
                  </div>
                ) : (
                  <div className="setting-value-row">
                    <div className="setting-value">
                      {setting.is_secret ? (
                        <>
                          <span className="setting-masked">
                            {revealedKeys.has(setting.key) ? setting.value : (setting.value ? '••••••••' : '(not set)')}
                          </span>
                          {setting.value && (
                            <button className="btn-icon" onClick={() => toggleReveal(setting.key)}>
                              {revealedKeys.has(setting.key) ? <EyeOff size={14} /> : <Eye size={14} />}
                            </button>
                          )}
                        </>
                      ) : (
                        <span className={setting.value ? '' : 'setting-empty'}>
                          {setting.value || '(not set)'}
                        </span>
                      )}
                    </div>
                    <button className="btn btn-secondary btn-sm" onClick={() => handleEdit(setting)}>
                      Edit
                    </button>
                    <button className="btn-icon btn-danger-icon" onClick={() => handleDelete(setting.key)}>
                      <Trash2 size={14} />
                    </button>
                  </div>
                )}

                {setting.updated_at && (
                  <div className="setting-meta">
                    Updated {new Date(setting.updated_at).toLocaleString()}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      ))}

      {showAdd ? (
        <div className="setting-add-form">
          <h3>Add New Setting</h3>
          <div className="setting-add-fields">
            <input
              type="text"
              placeholder="KEY_NAME (UPPER_SNAKE_CASE)"
              value={newKey}
              onChange={e => setNewKey(e.target.value.toUpperCase())}
              className="setting-input"
            />
            <select
              value={newCategory}
              onChange={e => setNewCategory(e.target.value)}
              className="setting-select"
            >
              <option value="general">General</option>
              <option value="shopify">Shopify</option>
              <option value="payments">Payments</option>
              <option value="ai">AI Providers</option>
              <option value="security">Security</option>
            </select>
            <label className="setting-checkbox">
              <input
                type="checkbox"
                checked={newIsSecret}
                onChange={e => setNewIsSecret(e.target.checked)}
              />
              Secret (masked)
            </label>
            <input
              type="text"
              placeholder="Description (optional)"
              value={newDescription}
              onChange={e => setNewDescription(e.target.value)}
              className="setting-input"
            />
          </div>
          <div className="setting-add-actions">
            <button className="btn btn-primary" onClick={handleAdd} disabled={!newKey}>
              <Plus size={14} /> Add Setting
            </button>
            <button className="btn btn-secondary" onClick={() => setShowAdd(false)}>
              Cancel
            </button>
          </div>
        </div>
      ) : (
        <button className="btn btn-secondary" onClick={() => setShowAdd(true)} style={{ marginTop: '1rem' }}>
          <Plus size={14} /> Add Custom Setting
        </button>
      )}
    </div>
  );
}

// ── Users Panel ─────────────────────────────────────────────────────

function UsersPanel() {
  const queryClient = useQueryClient();
  const [toggling, setToggling] = useState<string | null>(null);
  const [editingTokens, setEditingTokens] = useState<string | null>(null);
  const [tokenValue, setTokenValue] = useState('');
  const [savingTokens, setSavingTokens] = useState(false);

  const { data: users, isLoading } = useQuery({
    queryKey: ['admin-users'],
    queryFn: () => api.listAdminUsers(),
  });

  const handleToggleAdmin = async (user: AdminUser) => {
    setToggling(user.id);
    try {
      await api.setUserAdmin(user.id, !user.is_admin);
      queryClient.invalidateQueries({ queryKey: ['admin-users'] });
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed');
    } finally {
      setToggling(null);
    }
  };

  const handleEditTokens = (user: AdminUser) => {
    setEditingTokens(user.id);
    setTokenValue(String(user.token_balance));
  };

  const handleSaveTokens = async (userId: string) => {
    const val = parseInt(tokenValue, 10);
    if (isNaN(val) || val < 0) return;
    setSavingTokens(true);
    try {
      await api.setUserTokens(userId, val);
      setEditingTokens(null);
      queryClient.invalidateQueries({ queryKey: ['admin-users'] });
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed');
    } finally {
      setSavingTokens(false);
    }
  };

  if (isLoading) {
    return <div className="empty-state"><Loader2 size={24} className="spin" /> Loading users...</div>;
  }

  return (
    <div className="admin-users-panel">
      <table className="admin-table">
        <thead>
          <tr>
            <th>Email</th>
            <th>Display Name</th>
            <th>Tokens</th>
            <th>Admin</th>
            <th>Created</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {users?.map((user: AdminUser) => (
            <tr key={user.id}>
              <td className="user-email">{user.email}</td>
              <td>{user.display_name || '—'}</td>
              <td>
                {editingTokens === user.id ? (
                  <div className="token-edit-inline">
                    <input
                      type="number"
                      min="0"
                      value={tokenValue}
                      onChange={e => setTokenValue(e.target.value)}
                      className="token-edit-input"
                      autoFocus
                      onKeyDown={e => {
                        if (e.key === 'Enter') handleSaveTokens(user.id);
                        if (e.key === 'Escape') setEditingTokens(null);
                      }}
                    />
                    <button
                      className="btn btn-primary btn-sm"
                      onClick={() => handleSaveTokens(user.id)}
                      disabled={savingTokens}
                    >
                      {savingTokens ? <Loader2 size={12} className="spin" /> : <Check size={12} />}
                    </button>
                    <button className="btn btn-secondary btn-sm" onClick={() => setEditingTokens(null)}>
                      <X size={12} />
                    </button>
                  </div>
                ) : (
                  <span className="token-display" onClick={() => handleEditTokens(user)} title="Click to edit">
                    {user.token_balance}
                    <Coins size={12} className="token-edit-icon" />
                  </span>
                )}
              </td>
              <td>
                {user.is_admin ? (
                  <span className="admin-badge admin-yes"><Shield size={12} /> Admin</span>
                ) : (
                  <span className="admin-badge admin-no">User</span>
                )}
              </td>
              <td>{new Date(user.created_at).toLocaleDateString()}</td>
              <td>
                <button
                  className={`btn btn-sm ${user.is_admin ? 'btn-danger' : 'btn-primary'}`}
                  onClick={() => handleToggleAdmin(user)}
                  disabled={toggling === user.id}
                >
                  {toggling === user.id ? (
                    <Loader2 size={12} className="spin" />
                  ) : user.is_admin ? (
                    <><ShieldOff size={12} /> Revoke</>
                  ) : (
                    <><Shield size={12} /> Grant</>
                  )}
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {(!users || users.length === 0) && (
        <div className="empty-state">
          <Users size={48} />
          <p>No users yet</p>
        </div>
      )}
    </div>
  );
}

// ── Jobs Panel ──────────────────────────────────────────────────────

function JobsPanel() {
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [offset, setOffset] = useState(0);
  const limit = 25;

  const { data: jobs, isLoading } = useQuery<AdminJob[]>({
    queryKey: ['admin-jobs', statusFilter, offset],
    queryFn: () => api.listAdminJobs(limit, offset, statusFilter || undefined),
  });

  if (isLoading) {
    return <div className="empty-state"><Loader2 size={24} className="spin" /> Loading jobs...</div>;
  }

  return (
    <div className="admin-jobs-panel">
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
        <label style={{ color: '#94a3b8', fontSize: '0.85rem' }}>Filter by status:</label>
        <select
          value={statusFilter}
          onChange={e => { setStatusFilter(e.target.value); setOffset(0); }}
          className="setting-select"
          style={{ minWidth: '150px' }}
        >
          <option value="">All</option>
          <option value="pending">Pending</option>
          <option value="processing">Processing</option>
          <option value="completed">Completed</option>
          <option value="failed">Failed</option>
        </select>
      </div>

      <table className="admin-table">
        <thead>
          <tr>
            <th>Job ID</th>
            <th>Tenant</th>
            <th>Status</th>
            <th>Items</th>
            <th>Created</th>
          </tr>
        </thead>
        <tbody>
          {jobs?.map((job: AdminJob) => (
            <tr key={job.id}>
              <td style={{ fontFamily: 'monospace', fontSize: '0.8rem' }}>{truncateId(job.job_id)}</td>
              <td style={{ fontFamily: 'monospace', fontSize: '0.8rem' }}>{truncateId(job.tenant_id)}</td>
              <td><span style={badgeStyle(job.status)}>{job.status}</span></td>
              <td>{job.item_count}</td>
              <td>{formatDate(job.created_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>

      {(!jobs || jobs.length === 0) && (
        <div className="empty-state">
          <Briefcase size={48} />
          <p>No jobs found</p>
        </div>
      )}

      {jobs && jobs.length > 0 && (
        <div style={{ display: 'flex', gap: '0.5rem', marginTop: '1rem', justifyContent: 'center' }}>
          <button
            className="btn btn-secondary btn-sm"
            disabled={offset === 0}
            onClick={() => setOffset(Math.max(0, offset - limit))}
          >
            Previous
          </button>
          <span style={{ color: '#94a3b8', fontSize: '0.85rem', alignSelf: 'center' }}>
            Showing {offset + 1}–{offset + (jobs?.length || 0)}
          </span>
          <button
            className="btn btn-secondary btn-sm"
            disabled={(jobs?.length || 0) < limit}
            onClick={() => setOffset(offset + limit)}
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}

// ── Packages Panel ──────────────────────────────────────────────────

function PackagesPanel() {
  const queryClient = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState({ name: '', tokens: '', price_cents: '', currency: 'EUR', active: true });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { data: packages, isLoading } = useQuery<AdminTokenPackage[]>({
    queryKey: ['admin-packages'],
    queryFn: () => api.listAdminPackages(),
  });

  const resetForm = () => {
    setForm({ name: '', tokens: '', price_cents: '', currency: 'EUR', active: true });
    setShowCreate(false);
    setEditingId(null);
    setError(null);
  };

  const handleCreate = async () => {
    if (!form.name || !form.tokens || !form.price_cents) return;
    setSaving(true);
    setError(null);
    try {
      await api.createAdminPackage({
        name: form.name,
        tokens: parseInt(form.tokens, 10),
        price_cents: parseInt(form.price_cents, 10),
        currency: form.currency,
        active: form.active,
      });
      resetForm();
      queryClient.invalidateQueries({ queryKey: ['admin-packages'] });
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Create failed');
    } finally {
      setSaving(false);
    }
  };

  const handleStartEdit = (pkg: AdminTokenPackage) => {
    setEditingId(pkg.id);
    setForm({
      name: pkg.name,
      tokens: String(pkg.tokens),
      price_cents: String(pkg.price_cents),
      currency: pkg.currency,
      active: pkg.active,
    });
    setShowCreate(false);
    setError(null);
  };

  const handleUpdate = async () => {
    if (editingId === null) return;
    setSaving(true);
    setError(null);
    try {
      await api.updateAdminPackage(editingId, {
        name: form.name,
        tokens: parseInt(form.tokens, 10),
        price_cents: parseInt(form.price_cents, 10),
        currency: form.currency,
        active: form.active,
      });
      resetForm();
      queryClient.invalidateQueries({ queryKey: ['admin-packages'] });
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Update failed');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this package? This cannot be undone.')) return;
    try {
      await api.deleteAdminPackage(id);
      queryClient.invalidateQueries({ queryKey: ['admin-packages'] });
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Delete failed');
    }
  };

  const handleToggleActive = async (pkg: AdminTokenPackage) => {
    try {
      await api.updateAdminPackage(pkg.id, { active: !pkg.active });
      queryClient.invalidateQueries({ queryKey: ['admin-packages'] });
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Toggle failed');
    }
  };

  if (isLoading) {
    return <div className="empty-state"><Loader2 size={24} className="spin" /> Loading packages...</div>;
  }

  return (
    <div className="admin-packages-panel">
      {error && (
        <div className="integration-error">
          <X size={14} />
          <span>{error}</span>
          <button onClick={() => setError(null)}>Dismiss</button>
        </div>
      )}

      <table className="admin-table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Tokens</th>
            <th>Price</th>
            <th>Currency</th>
            <th>Active</th>
            <th>Created</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {packages?.map((pkg: AdminTokenPackage) => (
            <tr key={pkg.id}>
              {editingId === pkg.id ? (
                <>
                  <td>
                    <input className="setting-input" value={form.name}
                      onChange={e => setForm({ ...form, name: e.target.value })}
                      style={{ width: '100%' }} />
                  </td>
                  <td>
                    <input className="setting-input" type="number" value={form.tokens}
                      onChange={e => setForm({ ...form, tokens: e.target.value })}
                      style={{ width: '80px' }} />
                  </td>
                  <td>
                    <input className="setting-input" type="number" value={form.price_cents}
                      onChange={e => setForm({ ...form, price_cents: e.target.value })}
                      style={{ width: '80px' }} />
                  </td>
                  <td>
                    <input className="setting-input" value={form.currency}
                      onChange={e => setForm({ ...form, currency: e.target.value })}
                      style={{ width: '60px' }} />
                  </td>
                  <td>
                    <input type="checkbox" checked={form.active}
                      onChange={e => setForm({ ...form, active: e.target.checked })} />
                  </td>
                  <td>{formatDate(pkg.created_at)}</td>
                  <td>
                    <div style={{ display: 'flex', gap: '0.25rem' }}>
                      <button className="btn btn-primary btn-sm" onClick={handleUpdate} disabled={saving}>
                        {saving ? <Loader2 size={12} className="spin" /> : <Check size={12} />}
                      </button>
                      <button className="btn btn-secondary btn-sm" onClick={resetForm}>
                        <X size={12} />
                      </button>
                    </div>
                  </td>
                </>
              ) : (
                <>
                  <td style={{ fontWeight: 500 }}>{pkg.name}</td>
                  <td>{pkg.tokens}</td>
                  <td>{formatMoney(pkg.price_cents)}</td>
                  <td>{pkg.currency}</td>
                  <td>
                    <button
                      className="btn-icon"
                      onClick={() => handleToggleActive(pkg)}
                      title={pkg.active ? 'Click to deactivate' : 'Click to activate'}
                    >
                      <span style={badgeStyle(pkg.active ? 'active' : 'disconnected')}>
                        {pkg.active ? 'Active' : 'Inactive'}
                      </span>
                    </button>
                  </td>
                  <td>{formatDate(pkg.created_at)}</td>
                  <td>
                    <div style={{ display: 'flex', gap: '0.25rem' }}>
                      <button className="btn btn-secondary btn-sm" onClick={() => handleStartEdit(pkg)}>
                        <Edit2 size={12} />
                      </button>
                      <button className="btn-icon btn-danger-icon" onClick={() => handleDelete(pkg.id)}>
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </td>
                </>
              )}
            </tr>
          ))}
        </tbody>
      </table>

      {(!packages || packages.length === 0) && (
        <div className="empty-state">
          <Package size={48} />
          <p>No packages yet</p>
        </div>
      )}

      {showCreate ? (
        <div className="setting-add-form" style={{ marginTop: '1rem' }}>
          <h3>Create New Package</h3>
          <div className="setting-add-fields">
            <input className="setting-input" placeholder="Package name"
              value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} />
            <input className="setting-input" type="number" placeholder="Tokens"
              value={form.tokens} onChange={e => setForm({ ...form, tokens: e.target.value })} />
            <input className="setting-input" type="number" placeholder="Price (cents)"
              value={form.price_cents} onChange={e => setForm({ ...form, price_cents: e.target.value })} />
            <input className="setting-input" placeholder="Currency (EUR)"
              value={form.currency} onChange={e => setForm({ ...form, currency: e.target.value })} />
            <label className="setting-checkbox">
              <input type="checkbox" checked={form.active}
                onChange={e => setForm({ ...form, active: e.target.checked })} />
              Active
            </label>
          </div>
          <div className="setting-add-actions">
            <button className="btn btn-primary" onClick={handleCreate}
              disabled={saving || !form.name || !form.tokens || !form.price_cents}>
              {saving ? <Loader2 size={14} className="spin" /> : <Plus size={14} />} Create Package
            </button>
            <button className="btn btn-secondary" onClick={resetForm}>Cancel</button>
          </div>
        </div>
      ) : (
        <button className="btn btn-secondary" onClick={() => { resetForm(); setShowCreate(true); }}
          style={{ marginTop: '1rem' }}>
          <Plus size={14} /> Add Package
        </button>
      )}
    </div>
  );
}

// ── Activity Panel ──────────────────────────────────────────────────

function ActivityPanel() {
  const [txOffset, setTxOffset] = useState(0);
  const [payOffset, setPayOffset] = useState(0);
  const limit = 20;

  const { data: transactions, isLoading: txLoading } = useQuery<AdminTransaction[]>({
    queryKey: ['admin-transactions', txOffset],
    queryFn: () => api.listAdminTransactions(limit, txOffset),
  });

  const { data: payments, isLoading: payLoading } = useQuery<AdminPayment[]>({
    queryKey: ['admin-payments', payOffset],
    queryFn: () => api.listAdminPayments(limit, payOffset),
  });

  return (
    <div className="admin-activity-panel">
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: '1.5rem' }}>
        {/* Transactions */}
        <div>
          <h3 className="settings-category-title">Recent Transactions</h3>
          {txLoading ? (
            <div className="empty-state"><Loader2 size={24} className="spin" /> Loading...</div>
          ) : (
            <>
              <table className="admin-table">
                <thead>
                  <tr>
                    <th>User</th>
                    <th>Amount</th>
                    <th>Type</th>
                    <th>Description</th>
                    <th>Date</th>
                  </tr>
                </thead>
                <tbody>
                  {transactions?.map((tx: AdminTransaction) => (
                    <tr key={tx.id}>
                      <td style={{ fontFamily: 'monospace', fontSize: '0.8rem' }}>{truncateId(tx.user_id)}</td>
                      <td style={{ color: tx.amount >= 0 ? '#22c55e' : '#ef4444', fontWeight: 600 }}>
                        {tx.amount >= 0 ? '+' : ''}{tx.amount}
                      </td>
                      <td><span style={badgeStyle(tx.type)}>{tx.type}</span></td>
                      <td style={{ fontSize: '0.8rem', color: '#94a3b8', maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {tx.description || '—'}
                      </td>
                      <td>{formatDate(tx.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {(!transactions || transactions.length === 0) && (
                <div className="empty-state"><p>No transactions yet</p></div>
              )}
              {transactions && transactions.length > 0 && (
                <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.75rem', justifyContent: 'center' }}>
                  <button className="btn btn-secondary btn-sm" disabled={txOffset === 0}
                    onClick={() => setTxOffset(Math.max(0, txOffset - limit))}>Prev</button>
                  <button className="btn btn-secondary btn-sm" disabled={(transactions?.length || 0) < limit}
                    onClick={() => setTxOffset(txOffset + limit)}>Next</button>
                </div>
              )}
            </>
          )}
        </div>

        {/* Payments */}
        <div>
          <h3 className="settings-category-title">Recent Payments</h3>
          {payLoading ? (
            <div className="empty-state"><Loader2 size={24} className="spin" /> Loading...</div>
          ) : (
            <>
              <table className="admin-table">
                <thead>
                  <tr>
                    <th>User</th>
                    <th>Amount</th>
                    <th>Status</th>
                    <th>Mollie ID</th>
                    <th>Date</th>
                  </tr>
                </thead>
                <tbody>
                  {payments?.map((pay: AdminPayment) => (
                    <tr key={pay.id}>
                      <td style={{ fontFamily: 'monospace', fontSize: '0.8rem' }}>{truncateId(pay.user_id)}</td>
                      <td>{formatMoney(pay.amount_cents)} {pay.currency}</td>
                      <td><span style={badgeStyle(pay.status)}>{pay.status}</span></td>
                      <td style={{ fontFamily: 'monospace', fontSize: '0.8rem' }}>
                        {pay.mollie_payment_id ? truncateId(pay.mollie_payment_id) : '—'}
                      </td>
                      <td>{formatDate(pay.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {(!payments || payments.length === 0) && (
                <div className="empty-state"><p>No payments yet</p></div>
              )}
              {payments && payments.length > 0 && (
                <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.75rem', justifyContent: 'center' }}>
                  <button className="btn btn-secondary btn-sm" disabled={payOffset === 0}
                    onClick={() => setPayOffset(Math.max(0, payOffset - limit))}>Prev</button>
                  <button className="btn btn-secondary btn-sm" disabled={(payments?.length || 0) < limit}
                    onClick={() => setPayOffset(payOffset + limit)}>Next</button>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Integrations Panel ──────────────────────────────────────────────

function IntegrationsPanel() {
  const [offset, setOffset] = useState(0);
  const limit = 25;

  const { data: integrations, isLoading } = useQuery<AdminIntegration[]>({
    queryKey: ['admin-integrations', offset],
    queryFn: () => api.listAdminIntegrations(limit, offset),
  });

  if (isLoading) {
    return <div className="empty-state"><Loader2 size={24} className="spin" /> Loading integrations...</div>;
  }

  return (
    <div className="admin-integrations-panel">
      <table className="admin-table">
        <thead>
          <tr>
            <th>User ID</th>
            <th>Provider</th>
            <th>Store URL</th>
            <th>Status</th>
            <th>Created</th>
          </tr>
        </thead>
        <tbody>
          {integrations?.map((intg: AdminIntegration) => (
            <tr key={intg.id}>
              <td style={{ fontFamily: 'monospace', fontSize: '0.8rem' }}>{truncateId(intg.user_id)}</td>
              <td style={{ textTransform: 'capitalize', fontWeight: 500 }}>{intg.provider}</td>
              <td style={{ fontSize: '0.8rem' }}>
                <a href={intg.store_url} target="_blank" rel="noopener noreferrer"
                  style={{ color: '#6366f1', textDecoration: 'none' }}>
                  {intg.store_url}
                </a>
              </td>
              <td><span style={badgeStyle(intg.status)}>{intg.status}</span></td>
              <td>{formatDate(intg.created_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>

      {(!integrations || integrations.length === 0) && (
        <div className="empty-state">
          <Link size={48} />
          <p>No integrations yet</p>
        </div>
      )}

      {integrations && integrations.length > 0 && (
        <div style={{ display: 'flex', gap: '0.5rem', marginTop: '1rem', justifyContent: 'center' }}>
          <button className="btn btn-secondary btn-sm" disabled={offset === 0}
            onClick={() => setOffset(Math.max(0, offset - limit))}>Previous</button>
          <span style={{ color: '#94a3b8', fontSize: '0.85rem', alignSelf: 'center' }}>
            Showing {offset + 1}–{offset + (integrations?.length || 0)}
          </span>
          <button className="btn btn-secondary btn-sm" disabled={(integrations?.length || 0) < limit}
            onClick={() => setOffset(offset + limit)}>Next</button>
        </div>
      )}
    </div>
  );
}

// ── System Panel ────────────────────────────────────────────────────

function SystemPanel() {
  const { data: system, isLoading } = useQuery({
    queryKey: ['admin-system'],
    queryFn: () => api.getSystemInfo(),
  });

  if (isLoading) {
    return <div className="empty-state"><Loader2 size={24} className="spin" /> Loading...</div>;
  }

  if (!system) return null;

  const configItems = [
    { label: 'Environment', value: system.env_name },
    { label: 'Storage Backend', value: system.storage_backend },
    { label: 'Queue Backend', value: system.queue_backend },
    { label: 'Image Gen Provider', value: system.image_gen_provider },
    { label: 'Upscale Provider', value: system.upscale_provider },
    { label: 'Upscale Enabled', value: system.upscale_enabled ? 'Yes' : 'No' },
    { label: 'BG Removal Provider', value: system.bg_removal_provider },
    { label: 'Public Base URL', value: system.public_base_url },
  ];

  const statusItems = [
    { label: 'Entra Auth', configured: system.has_entra_config },
    { label: 'Mollie Payments', configured: system.has_mollie_config },
    { label: 'Shopify', configured: system.has_shopify_config },
    { label: 'fal.ai (Image Gen)', configured: system.has_fal_config },
    { label: 'Encryption Key', configured: system.has_encryption_key },
  ];

  return (
    <div className="admin-system-panel">
      <h3 className="settings-category-title">Configuration</h3>
      <div className="system-grid">
        {configItems.map(item => (
          <div key={item.label} className="system-item">
            <span className="system-label">{item.label}</span>
            <span className="system-value">{item.value}</span>
          </div>
        ))}
      </div>

      <h3 className="settings-category-title" style={{ marginTop: '1.5rem' }}>Service Status</h3>
      <div className="system-grid">
        {statusItems.map(item => (
          <div key={item.label} className="system-item">
            <span className="system-label">{item.label}</span>
            <span className={`system-status ${item.configured ? 'status-ok' : 'status-missing'}`}>
              {item.configured ? <><Check size={14} /> Configured</> : <><X size={14} /> Not configured</>}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
