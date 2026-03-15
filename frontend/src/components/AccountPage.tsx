import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import {
  User, Building2, MapPin, Phone, FileCheck,
  Save, Loader2, CheckCircle, XCircle,
} from 'lucide-react';
import { api } from '../api';
import type { UserProfile } from '../types';

const COUNTRIES = [
  { code: 'AT', name: 'Austria' }, { code: 'BE', name: 'Belgium' },
  { code: 'BG', name: 'Bulgaria' }, { code: 'HR', name: 'Croatia' },
  { code: 'CY', name: 'Cyprus' }, { code: 'CZ', name: 'Czechia' },
  { code: 'DK', name: 'Denmark' }, { code: 'EE', name: 'Estonia' },
  { code: 'FI', name: 'Finland' }, { code: 'FR', name: 'France' },
  { code: 'DE', name: 'Germany' }, { code: 'GR', name: 'Greece' },
  { code: 'HU', name: 'Hungary' }, { code: 'IE', name: 'Ireland' },
  { code: 'IT', name: 'Italy' }, { code: 'LV', name: 'Latvia' },
  { code: 'LT', name: 'Lithuania' }, { code: 'LU', name: 'Luxembourg' },
  { code: 'MT', name: 'Malta' }, { code: 'NL', name: 'Netherlands' },
  { code: 'PL', name: 'Poland' }, { code: 'PT', name: 'Portugal' },
  { code: 'RO', name: 'Romania' }, { code: 'SK', name: 'Slovakia' },
  { code: 'SI', name: 'Slovenia' }, { code: 'ES', name: 'Spain' },
  { code: 'SE', name: 'Sweden' },
  { code: 'GB', name: 'United Kingdom' }, { code: 'CH', name: 'Switzerland' },
  { code: 'NO', name: 'Norway' }, { code: 'TR', name: 'Turkey' },
  { code: 'US', name: 'United States' }, { code: 'CA', name: 'Canada' },
];

export default function AccountPage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  const { data: profile, isLoading } = useQuery({
    queryKey: ['profile'],
    queryFn: () => api.getProfile(),
  });

  const [form, setForm] = useState<Partial<UserProfile> | null>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState('');
  const [vatStatus, setVatStatus] = useState<'idle' | 'checking' | 'valid' | 'invalid'>('idle');
  const [vatError, setVatError] = useState('');

  // Initialize form from profile on first load
  const formData = form ?? profile ?? {} as Partial<UserProfile>;

  const set = (field: keyof UserProfile) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    setForm(prev => ({ ...(prev ?? profile ?? {}), [field]: e.target.value }));
    setSaved(false);
    if (field === 'vat_number') { setVatStatus('idle'); setVatError(''); }
  };

  const handleValidateVat = async () => {
    const vat = (formData.vat_number || '').trim();
    if (!vat || vat.length < 4) return;
    setVatStatus('checking');
    setVatError('');
    try {
      const result = await api.validateVat(vat);
      if (result.valid) {
        setVatStatus('valid');
      } else {
        setVatStatus('invalid');
        setVatError(result.error || 'Invalid VAT number');
      }
    } catch {
      setVatStatus('invalid');
      setVatError('Could not validate');
    }
  };

  const handleSave = async () => {
    if (!form) return;
    setSaving(true);
    setError('');
    try {
      await api.updateProfile(form);
      queryClient.invalidateQueries({ queryKey: ['profile'] });
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to save');
    } finally {
      setSaving(false);
    }
  };

  if (isLoading) {
    return (
      <div className="settings-page">
        <p style={{ color: 'rgba(200,205,224,0.6)', padding: '2rem' }}>Loading...</p>
      </div>
    );
  }

  return (
    <div className="settings-page">
      <div className="section-header">
        <h2>{t('account.title', 'Account')}</h2>
        <p>{t('account.subtitle', 'Manage your business details and billing information')}</p>
      </div>

      {/* Account Type */}
      <div className="settings-section">
        <h3 className="settings-section-title">
          {t('account.accountType', 'Account Type')}
        </h3>
        <div style={{ display: 'flex', gap: '0.75rem' }}>
          {(['consumer', 'business'] as const).map(type => (
            <button
              key={type}
              className={`onboarding-type-card ${formData.account_type === type ? 'selected' : ''}`}
              style={{ flex: 1, padding: '1rem' }}
              onClick={() => { setForm(prev => ({ ...(prev ?? profile ?? {}), account_type: type } as typeof prev)); setSaved(false); }}
            >
              {type === 'consumer' ? <User size={20} /> : <Building2 size={20} />}
              <strong>{type === 'consumer' ? 'Personal' : 'Business'}</strong>
            </button>
          ))}
        </div>
      </div>

      {/* Personal Info */}
      <div className="settings-section">
        <h3 className="settings-section-title">
          <User size={18} style={{ marginRight: '0.5rem', opacity: 0.7 }} />
          {t('account.personalInfo', 'Personal Information')}
        </h3>

        <div className="account-form">
          <label className="account-label">
            {t('account.email', 'Email')}
            <input className="account-input" value={profile?.email || ''} disabled
              style={{ opacity: 0.5, cursor: 'not-allowed' }} />
          </label>

          <label className="account-label">
            {t('account.displayName', 'Display name')}
            <input className="account-input" value={formData.display_name || ''}
              onChange={set('display_name')} placeholder="John Doe" />
          </label>

          <label className="account-label">
            <span style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <Phone size={14} style={{ opacity: 0.5 }} />
              {t('account.phone', 'Phone')}
            </span>
            <input className="account-input" value={formData.phone || ''}
              onChange={set('phone')} placeholder="+31 6 12345678" />
          </label>
        </div>
      </div>

      {/* Business Info */}
      <div className="settings-section">
        <h3 className="settings-section-title">
          <Building2 size={18} style={{ marginRight: '0.5rem', opacity: 0.7 }} />
          {t('account.businessInfo', 'Business Information')}
        </h3>

        <div className="account-form">
          <label className="account-label">
            {t('account.companyName', 'Company name')}
            <input className="account-input" value={formData.company_name || ''}
              onChange={set('company_name')} placeholder="Acme B.V." />
          </label>

          <label className="account-label">
            <span style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <FileCheck size={14} style={{ opacity: 0.5 }} />
              {t('account.vatNumber', 'VAT number')}
            </span>
            <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
              <input className="account-input" style={{ flex: 1, marginBottom: 0 }}
                value={formData.vat_number || ''} onChange={set('vat_number')}
                placeholder="NL123456789B01" />
              {(formData.vat_number || '').trim().length >= 4 && (
                <button
                  type="button"
                  className="btn btn-sm"
                  style={{ whiteSpace: 'nowrap', padding: '0.4rem 0.8rem', fontSize: '0.8rem' }}
                  onClick={handleValidateVat}
                  disabled={vatStatus === 'checking'}
                >
                  {vatStatus === 'checking' ? <Loader2 size={14} className="spin" /> : 'Verify'}
                </button>
              )}
              {vatStatus === 'valid' && <CheckCircle size={18} style={{ color: '#4ade80', flexShrink: 0 }} />}
              {vatStatus === 'invalid' && <XCircle size={18} style={{ color: '#f87171', flexShrink: 0 }} />}
            </div>
            {vatError && <span style={{ color: '#f87171', fontSize: '0.75rem', marginTop: '0.25rem' }}>{vatError}</span>}
          </label>
        </div>
      </div>

      {/* Address */}
      <div className="settings-section">
        <h3 className="settings-section-title">
          <MapPin size={18} style={{ marginRight: '0.5rem', opacity: 0.7 }} />
          {t('account.billingAddress', 'Billing Address')}
        </h3>

        <div className="account-form">
          <label className="account-label">
            {t('account.addressLine1', 'Address')}
            <input className="account-input" value={formData.address_line1 || ''}
              onChange={set('address_line1')} placeholder="123 Main Street" />
          </label>

          <label className="account-label">
            {t('account.addressLine2', 'Address line 2')}
            <input className="account-input" value={formData.address_line2 || ''}
              onChange={set('address_line2')} placeholder="Suite 4B" />
          </label>

          <div style={{ display: 'flex', gap: '1rem' }}>
            <label className="account-label" style={{ flex: 2 }}>
              {t('account.city', 'City')}
              <input className="account-input" value={formData.city || ''}
                onChange={set('city')} placeholder="Amsterdam" />
            </label>
            <label className="account-label" style={{ flex: 1 }}>
              {t('account.postalCode', 'Postal code')}
              <input className="account-input" value={formData.postal_code || ''}
                onChange={set('postal_code')} placeholder="1012 AB" />
            </label>
          </div>

          <label className="account-label">
            {t('account.country', 'Country')}
            <select className="account-input" value={formData.country || ''}
              onChange={set('country')}>
              <option value="">Select country...</option>
              {COUNTRIES.map(c => (
                <option key={c.code} value={c.code}>{c.name}</option>
              ))}
            </select>
          </label>
        </div>
      </div>

      {/* Save */}
      {error && <p style={{ color: '#f87171', fontSize: '0.85rem', marginTop: '0.5rem' }}>{error}</p>}
      <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', marginTop: '1.5rem' }}>
        <button
          className="btn btn-primary"
          onClick={handleSave}
          disabled={saving || !form}
          style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}
        >
          {saving ? <Loader2 size={16} className="spin" /> : <Save size={16} />}
          {t('account.save', 'Save changes')}
        </button>
        {saved && (
          <span style={{ color: '#4ade80', fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
            <CheckCircle size={14} /> Saved
          </span>
        )}
      </div>
    </div>
  );
}
