import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Settings, Users, Server, Eye, EyeOff, Save, Trash2, Plus, Shield, ShieldOff, X, Check, Loader2 } from 'lucide-react';
import { api } from '../api';
import type { AdminSetting, AdminUser } from '../types';

type AdminTab = 'settings' | 'users' | 'system';

export default function AdminPage() {
  const [activeTab, setActiveTab] = useState<AdminTab>('settings');

  const tabs = [
    { id: 'settings' as AdminTab, label: 'Settings', icon: Settings },
    { id: 'users' as AdminTab, label: 'Users', icon: Users },
    { id: 'system' as AdminTab, label: 'System', icon: Server },
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

      {activeTab === 'settings' && <SettingsPanel />}
      {activeTab === 'users' && <UsersPanel />}
      {activeTab === 'system' && <SystemPanel />}
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
              <td>{user.token_balance}</td>
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
