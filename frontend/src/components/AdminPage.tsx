import { useState } from 'react';
import { useTranslation } from 'react-i18next';
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
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState<AdminTab>('dashboard');

  const tabs: { id: AdminTab; label: string; icon: React.ComponentType<{ size?: number }> }[] = [
    { id: 'dashboard', label: t('admin.tabs.dashboard'), icon: BarChart3 },
    { id: 'users', label: t('admin.tabs.users'), icon: Users },
    { id: 'jobs', label: t('admin.tabs.jobs'), icon: Briefcase },
    { id: 'packages', label: t('admin.tabs.packages'), icon: Package },
    { id: 'activity', label: t('admin.tabs.activity'), icon: Activity },
    { id: 'integrations', label: t('admin.tabs.integrations'), icon: Link },
    { id: 'settings', label: t('admin.tabs.settings'), icon: Settings },
    { id: 'system', label: t('admin.tabs.system'), icon: Server },
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
  const { t } = useTranslation();
  const { data: stats, isLoading } = useQuery<PlatformStats>({
    queryKey: ['admin-stats'],
    queryFn: () => api.getPlatformStats(),
  });

  if (isLoading) {
    return <div className="empty-state"><Loader2 size={24} className="spin" /> {t('common.loading')}</div>;
  }

  if (!stats) return null;

  const cards = [
    { label: t('admin.dashboard.totalUsers'), value: stats.total_users, icon: Users, color: '#6366f1' },
    { label: t('admin.dashboard.totalJobs'), value: stats.total_jobs, icon: Briefcase, color: '#06b6d4' },
    { label: t('admin.dashboard.tokensInCirculation'), value: stats.total_tokens_in_circulation, icon: Coins, color: '#eab308' },
    { label: t('admin.dashboard.tokensSpent'), value: stats.total_tokens_spent, icon: Coins, color: '#f97316' },
    { label: t('admin.dashboard.revenue'), value: formatMoney(stats.total_revenue_cents), icon: CreditCard, color: '#22c55e' },
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
          <h3 className="settings-category-title">{t('admin.dashboard.jobsByStatus')}</h3>
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
  const { t } = useTranslation();
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
    if (!confirm(t('admin.settings.deleteConfirm', { key }))) return;
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
    shopify: t('admin.settings.categories.shopify'),
    payments: t('admin.settings.categories.payments'),
    ai: t('admin.settings.categories.ai'),
    security: t('admin.settings.categories.security'),
    general: t('admin.settings.categories.general'),
  };

  if (isLoading) {
    return <div className="empty-state"><Loader2 size={24} className="spin" /> {t('common.loading')}</div>;
  }

  return (
    <div className="admin-settings-panel">
      {error && (
        <div className="integration-error">
          <X size={14} />
          <span>{error}</span>
          <button onClick={() => setError(null)}>{t('common.dismiss')}</button>
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
                      placeholder={setting.is_secret ? t('admin.settings.enterNewValue') : 'Value'}
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
                            {revealedKeys.has(setting.key) ? setting.value : (setting.value ? '••••••••' : t('admin.settings.notSet'))}
                          </span>
                          {setting.value && (
                            <button className="btn-icon" onClick={() => toggleReveal(setting.key)}>
                              {revealedKeys.has(setting.key) ? <EyeOff size={14} /> : <Eye size={14} />}
                            </button>
                          )}
                        </>
                      ) : (
                        <span className={setting.value ? '' : 'setting-empty'}>
                          {setting.value || t('admin.settings.notSet')}
                        </span>
                      )}
                    </div>
                    <button className="btn btn-secondary btn-sm" onClick={() => handleEdit(setting)}>
                      {t('common.edit')}
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
          <h3>{t('admin.settings.addNewSetting')}</h3>
          <div className="setting-add-fields">
            <input
              type="text"
              placeholder={t('admin.settings.keyPlaceholder')}
              value={newKey}
              onChange={e => setNewKey(e.target.value.toUpperCase())}
              className="setting-input"
            />
            <select
              value={newCategory}
              onChange={e => setNewCategory(e.target.value)}
              className="setting-select"
            >
              <option value="general">{t('admin.settings.categories.general')}</option>
              <option value="shopify">{t('admin.settings.categories.shopify')}</option>
              <option value="payments">{t('admin.settings.categories.payments')}</option>
              <option value="ai">{t('admin.settings.categories.ai')}</option>
              <option value="security">{t('admin.settings.categories.security')}</option>
            </select>
            <label className="setting-checkbox">
              <input
                type="checkbox"
                checked={newIsSecret}
                onChange={e => setNewIsSecret(e.target.checked)}
              />
              {t('admin.settings.secretMasked')}
            </label>
            <input
              type="text"
              placeholder={t('admin.settings.descriptionPlaceholder')}
              value={newDescription}
              onChange={e => setNewDescription(e.target.value)}
              className="setting-input"
            />
          </div>
          <div className="setting-add-actions">
            <button className="btn btn-primary" onClick={handleAdd} disabled={!newKey}>
              <Plus size={14} /> {t('admin.settings.addSetting')}
            </button>
            <button className="btn btn-secondary" onClick={() => setShowAdd(false)}>
              {t('common.cancel')}
            </button>
          </div>
        </div>
      ) : (
        <button className="btn btn-secondary" onClick={() => setShowAdd(true)} style={{ marginTop: '1rem' }}>
          <Plus size={14} /> {t('admin.settings.addCustomSetting')}
        </button>
      )}
    </div>
  );
}

// ── Users Panel ─────────────────────────────────────────────────────

function UsersPanel() {
  const { t } = useTranslation();
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
    return <div className="empty-state"><Loader2 size={24} className="spin" /> {t('common.loading')}</div>;
  }

  return (
    <div className="admin-users-panel">
      <table className="admin-table">
        <thead>
          <tr>
            <th>{t('admin.users.email')}</th>
            <th>{t('admin.users.displayName')}</th>
            <th>{t('admin.users.tokens')}</th>
            <th>{t('admin.users.admin')}</th>
            <th>{t('admin.users.created')}</th>
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
                  <span className="admin-badge admin-yes"><Shield size={12} /> {t('admin.users.admin')}</span>
                ) : (
                  <span className="admin-badge admin-no">{t('admin.users.user')}</span>
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
                    <><ShieldOff size={12} /> {t('admin.users.revoke')}</>
                  ) : (
                    <><Shield size={12} /> {t('admin.users.grant')}</>
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
          <p>{t('admin.users.noUsers')}</p>
        </div>
      )}
    </div>
  );
}

// ── Jobs Panel ──────────────────────────────────────────────────────

function JobsPanel() {
  const { t } = useTranslation();
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [offset, setOffset] = useState(0);
  const limit = 25;

  const { data: jobs, isLoading } = useQuery<AdminJob[]>({
    queryKey: ['admin-jobs', statusFilter, offset],
    queryFn: () => api.listAdminJobs(limit, offset, statusFilter || undefined),
  });

  if (isLoading) {
    return <div className="empty-state"><Loader2 size={24} className="spin" /> {t('common.loading')}</div>;
  }

  return (
    <div className="admin-jobs-panel">
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
        <label style={{ color: '#94a3b8', fontSize: '0.85rem' }}>{t('admin.jobs.filterByStatus')}</label>
        <select
          value={statusFilter}
          onChange={e => { setStatusFilter(e.target.value); setOffset(0); }}
          className="setting-select"
          style={{ minWidth: '150px' }}
        >
          <option value="">{t('admin.jobs.all')}</option>
          <option value="pending">{t('admin.jobs.pending')}</option>
          <option value="processing">{t('admin.jobs.processing')}</option>
          <option value="completed">{t('admin.jobs.completed')}</option>
          <option value="failed">{t('admin.jobs.failed')}</option>
        </select>
      </div>

      <table className="admin-table">
        <thead>
          <tr>
            <th>{t('admin.jobs.jobId')}</th>
            <th>{t('admin.jobs.tenant')}</th>
            <th>{t('admin.jobs.status')}</th>
            <th>{t('admin.jobs.items')}</th>
            <th>{t('admin.jobs.created')}</th>
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
          <p>{t('admin.jobs.noJobs')}</p>
        </div>
      )}

      {jobs && jobs.length > 0 && (
        <div style={{ display: 'flex', gap: '0.5rem', marginTop: '1rem', justifyContent: 'center' }}>
          <button
            className="btn btn-secondary btn-sm"
            disabled={offset === 0}
            onClick={() => setOffset(Math.max(0, offset - limit))}
          >
            {t('common.previous')}
          </button>
          <span style={{ color: '#94a3b8', fontSize: '0.85rem', alignSelf: 'center' }}>
            {t('admin.jobs.showing', { from: offset + 1, to: offset + (jobs?.length || 0) })}
          </span>
          <button
            className="btn btn-secondary btn-sm"
            disabled={(jobs?.length || 0) < limit}
            onClick={() => setOffset(offset + limit)}
          >
            {t('common.next')}
          </button>
        </div>
      )}
    </div>
  );
}

// ── Packages Panel ──────────────────────────────────────────────────

function PackagesPanel() {
  const { t } = useTranslation();
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
    if (!confirm(t('admin.packages.deleteConfirm'))) return;
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
    return <div className="empty-state"><Loader2 size={24} className="spin" /> {t('common.loading')}</div>;
  }

  return (
    <div className="admin-packages-panel">
      {error && (
        <div className="integration-error">
          <X size={14} />
          <span>{error}</span>
          <button onClick={() => setError(null)}>{t('common.dismiss')}</button>
        </div>
      )}

      <table className="admin-table">
        <thead>
          <tr>
            <th>{t('admin.packages.name')}</th>
            <th>{t('admin.packages.tokens')}</th>
            <th>{t('admin.packages.price')}</th>
            <th>{t('admin.packages.currency')}</th>
            <th>{t('admin.packages.active')}</th>
            <th>{t('admin.packages.created')}</th>
            <th>{t('admin.packages.actions')}</th>
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
                        {pkg.active ? t('admin.packages.active') : t('admin.packages.inactive')}
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
          <p>{t('admin.packages.noPackages')}</p>
        </div>
      )}

      {showCreate ? (
        <div className="setting-add-form" style={{ marginTop: '1rem' }}>
          <h3>{t('admin.packages.createNew')}</h3>
          <div className="setting-add-fields">
            <input className="setting-input" placeholder={t('admin.packages.packageName')}
              value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} />
            <input className="setting-input" type="number" placeholder={t('admin.packages.tokens')}
              value={form.tokens} onChange={e => setForm({ ...form, tokens: e.target.value })} />
            <input className="setting-input" type="number" placeholder={t('admin.packages.priceCents')}
              value={form.price_cents} onChange={e => setForm({ ...form, price_cents: e.target.value })} />
            <input className="setting-input" placeholder={t('admin.packages.currencyPlaceholder')}
              value={form.currency} onChange={e => setForm({ ...form, currency: e.target.value })} />
            <label className="setting-checkbox">
              <input type="checkbox" checked={form.active}
                onChange={e => setForm({ ...form, active: e.target.checked })} />
              {t('admin.packages.active')}
            </label>
          </div>
          <div className="setting-add-actions">
            <button className="btn btn-primary" onClick={handleCreate}
              disabled={saving || !form.name || !form.tokens || !form.price_cents}>
              {saving ? <Loader2 size={14} className="spin" /> : <Plus size={14} />} {t('admin.packages.createPackage')}
            </button>
            <button className="btn btn-secondary" onClick={resetForm}>{t('common.cancel')}</button>
          </div>
        </div>
      ) : (
        <button className="btn btn-secondary" onClick={() => { resetForm(); setShowCreate(true); }}
          style={{ marginTop: '1rem' }}>
          <Plus size={14} /> {t('admin.packages.addPackage')}
        </button>
      )}
    </div>
  );
}

// ── Activity Panel ──────────────────────────────────────────────────

function ActivityPanel() {
  const { t } = useTranslation();
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
          <h3 className="settings-category-title">{t('admin.activity.recentTransactions')}</h3>
          {txLoading ? (
            <div className="empty-state"><Loader2 size={24} className="spin" /> {t('common.loading')}</div>
          ) : (
            <>
              <table className="admin-table">
                <thead>
                  <tr>
                    <th>{t('admin.activity.user')}</th>
                    <th>{t('admin.activity.amount')}</th>
                    <th>{t('admin.activity.type')}</th>
                    <th>{t('admin.activity.description')}</th>
                    <th>{t('admin.activity.date')}</th>
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
                <div className="empty-state"><p>{t('admin.activity.noTransactions')}</p></div>
              )}
              {transactions && transactions.length > 0 && (
                <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.75rem', justifyContent: 'center' }}>
                  <button className="btn btn-secondary btn-sm" disabled={txOffset === 0}
                    onClick={() => setTxOffset(Math.max(0, txOffset - limit))}>{t('common.previous')}</button>
                  <button className="btn btn-secondary btn-sm" disabled={(transactions?.length || 0) < limit}
                    onClick={() => setTxOffset(txOffset + limit)}>{t('common.next')}</button>
                </div>
              )}
            </>
          )}
        </div>

        {/* Payments */}
        <div>
          <h3 className="settings-category-title">{t('admin.activity.recentPayments')}</h3>
          {payLoading ? (
            <div className="empty-state"><Loader2 size={24} className="spin" /> {t('common.loading')}</div>
          ) : (
            <>
              <table className="admin-table">
                <thead>
                  <tr>
                    <th>{t('admin.activity.user')}</th>
                    <th>{t('admin.activity.amount')}</th>
                    <th>{t('admin.activity.status')}</th>
                    <th>{t('admin.activity.mollieId')}</th>
                    <th>{t('admin.activity.date')}</th>
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
                <div className="empty-state"><p>{t('admin.activity.noPayments')}</p></div>
              )}
              {payments && payments.length > 0 && (
                <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.75rem', justifyContent: 'center' }}>
                  <button className="btn btn-secondary btn-sm" disabled={payOffset === 0}
                    onClick={() => setPayOffset(Math.max(0, payOffset - limit))}>{t('common.previous')}</button>
                  <button className="btn btn-secondary btn-sm" disabled={(payments?.length || 0) < limit}
                    onClick={() => setPayOffset(payOffset + limit)}>{t('common.next')}</button>
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
  const { t } = useTranslation();
  const [offset, setOffset] = useState(0);
  const limit = 25;

  const { data: integrations, isLoading } = useQuery<AdminIntegration[]>({
    queryKey: ['admin-integrations', offset],
    queryFn: () => api.listAdminIntegrations(limit, offset),
  });

  if (isLoading) {
    return <div className="empty-state"><Loader2 size={24} className="spin" /> {t('common.loading')}</div>;
  }

  return (
    <div className="admin-integrations-panel">
      <table className="admin-table">
        <thead>
          <tr>
            <th>{t('admin.integrations.userId')}</th>
            <th>{t('admin.integrations.provider')}</th>
            <th>{t('admin.integrations.storeUrl')}</th>
            <th>{t('admin.integrations.status')}</th>
            <th>{t('admin.integrations.created')}</th>
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
          <p>{t('admin.integrations.noIntegrations')}</p>
        </div>
      )}

      {integrations && integrations.length > 0 && (
        <div style={{ display: 'flex', gap: '0.5rem', marginTop: '1rem', justifyContent: 'center' }}>
          <button className="btn btn-secondary btn-sm" disabled={offset === 0}
            onClick={() => setOffset(Math.max(0, offset - limit))}>{t('common.previous')}</button>
          <span style={{ color: '#94a3b8', fontSize: '0.85rem', alignSelf: 'center' }}>
            {t('admin.jobs.showing', { from: offset + 1, to: offset + (integrations?.length || 0) })}
          </span>
          <button className="btn btn-secondary btn-sm" disabled={(integrations?.length || 0) < limit}
            onClick={() => setOffset(offset + limit)}>{t('common.next')}</button>
        </div>
      )}
    </div>
  );
}

// ── System Panel ────────────────────────────────────────────────────

function SystemPanel() {
  const { t } = useTranslation();
  const { data: system, isLoading } = useQuery({
    queryKey: ['admin-system'],
    queryFn: () => api.getSystemInfo(),
  });

  if (isLoading) {
    return <div className="empty-state"><Loader2 size={24} className="spin" /> {t('common.loading')}</div>;
  }

  if (!system) return null;

  const configItems = [
    { label: t('admin.system.environment'), value: system.env_name },
    { label: t('admin.system.storageBackend'), value: system.storage_backend },
    { label: t('admin.system.queueBackend'), value: system.queue_backend },
    { label: t('admin.system.imageGenProvider'), value: system.image_gen_provider },
    { label: t('admin.system.upscaleProvider'), value: system.upscale_provider },
    { label: t('admin.system.upscaleEnabled'), value: system.upscale_enabled ? t('admin.system.yes') : t('admin.system.no') },
    { label: t('admin.system.bgRemovalProvider'), value: system.bg_removal_provider },
    { label: t('admin.system.publicBaseUrl'), value: system.public_base_url },
  ];

  const statusItems = [
    { label: t('admin.system.entraAuth'), configured: system.has_entra_config },
    { label: t('admin.system.molliePayments'), configured: system.has_mollie_config },
    { label: t('admin.system.shopify'), configured: system.has_shopify_config },
    { label: t('admin.system.falAi'), configured: system.has_fal_config },
    { label: t('admin.system.encryptionKey'), configured: system.has_encryption_key },
  ];

  return (
    <div className="admin-system-panel">
      <h3 className="settings-category-title">{t('admin.system.configuration')}</h3>
      <div className="system-grid">
        {configItems.map(item => (
          <div key={item.label} className="system-item">
            <span className="system-label">{item.label}</span>
            <span className="system-value">{item.value}</span>
          </div>
        ))}
      </div>

      <h3 className="settings-category-title" style={{ marginTop: '1.5rem' }}>{t('admin.system.serviceStatus')}</h3>
      <div className="system-grid">
        {statusItems.map(item => (
          <div key={item.label} className="system-item">
            <span className="system-label">{item.label}</span>
            <span className={`system-status ${item.configured ? 'status-ok' : 'status-missing'}`}>
              {item.configured ? <><Check size={14} /> {t('admin.system.configured')}</> : <><X size={14} /> {t('admin.system.notConfigured')}</>}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
