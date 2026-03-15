import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Loader2, Building2, MapPin, ArrowRight, CheckCircle, XCircle, User, Briefcase } from 'lucide-react';
import { api } from '../api';
import type { UserProfile } from '../types';

const EU_COUNTRIES = [
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
  // Common non-EU
  { code: 'GB', name: 'United Kingdom' }, { code: 'CH', name: 'Switzerland' },
  { code: 'NO', name: 'Norway' }, { code: 'TR', name: 'Turkey' },
  { code: 'US', name: 'United States' }, { code: 'CA', name: 'Canada' },
];

interface Props {
  profile: UserProfile;
  onComplete: () => void;
}

type AccountType = 'consumer' | 'business';

export default function OnboardingModal({ profile, onComplete }: Props) {
  const { t } = useTranslation();
  const [step, setStep] = useState<0 | 1 | 2>(0);
  const [accountType, setAccountType] = useState<AccountType | null>(profile.account_type || null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [vatStatus, setVatStatus] = useState<'idle' | 'checking' | 'valid' | 'invalid'>('idle');
  const [vatError, setVatError] = useState('');

  const [form, setForm] = useState({
    display_name: profile.display_name || '',
    company_name: profile.company_name || '',
    vat_number: profile.vat_number || '',
    phone: profile.phone || '',
    address_line1: profile.address_line1 || '',
    address_line2: profile.address_line2 || '',
    city: profile.city || '',
    postal_code: profile.postal_code || '',
    country: profile.country || '',
  });

  const set = (field: string) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    setForm(prev => ({ ...prev, [field]: e.target.value }));
    if (field === 'vat_number') { setVatStatus('idle'); setVatError(''); }
  };

  const handleValidateVat = async () => {
    const vat = form.vat_number.trim();
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

  const isBusiness = accountType === 'business';
  const step1Valid = isBusiness
    ? form.display_name.trim() && form.company_name.trim()
    : form.display_name.trim();
  const step2Valid = form.address_line1.trim() && form.city.trim() && form.postal_code.trim() && form.country;

  const handleFinish = async () => {
    setSaving(true);
    setError('');
    try {
      await api.updateProfile({
        ...form,
        account_type: accountType!,
        onboarding_completed: true,
      });
      onComplete();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to save profile');
    } finally {
      setSaving(false);
    }
  };

  // Consumer can finish after step 1 (name only)
  const handleConsumerFinish = async () => {
    setSaving(true);
    setError('');
    try {
      await api.updateProfile({
        display_name: form.display_name,
        account_type: 'consumer',
        onboarding_completed: true,
      });
      onComplete();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to save profile');
    } finally {
      setSaving(false);
    }
  };

  const totalSteps = isBusiness ? 3 : 2;

  return (
    <div className="onboarding-overlay">
      <div className="onboarding-modal">
        <div className="onboarding-header">
          <h2>{t('onboarding.title', { defaultValue: 'Welcome to Opal' })}</h2>
          <p className="onboarding-subtitle">
            {step === 0
              ? t('onboarding.subtitleType', { defaultValue: 'How will you be using Opal?' })
              : t('onboarding.subtitle', { defaultValue: 'Tell us a bit about yourself so we can set up your account.' })}
          </p>
          {step > 0 && (
            <div className="onboarding-steps">
              {Array.from({ length: totalSteps }, (_, i) => (
                <span key={i}>
                  {i > 0 && <span className="onboarding-step-line" />}
                  <span className={`onboarding-step ${step >= i + 1 ? 'active' : ''}`}>{i + 1}</span>
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Step 0: Account type selection */}
        {step === 0 && (
          <div className="onboarding-body">
            <div className="onboarding-type-grid">
              <button
                className={`onboarding-type-card ${accountType === 'consumer' ? 'selected' : ''}`}
                onClick={() => setAccountType('consumer')}
              >
                <User size={28} />
                <strong>{t('onboarding.consumer', { defaultValue: 'Personal' })}</strong>
                <span>{t('onboarding.consumerDesc', { defaultValue: 'Individual use, no business details needed' })}</span>
              </button>
              <button
                className={`onboarding-type-card ${accountType === 'business' ? 'selected' : ''}`}
                onClick={() => setAccountType('business')}
              >
                <Briefcase size={28} />
                <strong>{t('onboarding.business', { defaultValue: 'Business' })}</strong>
                <span>{t('onboarding.businessDesc', { defaultValue: 'Company details, VAT, and invoicing' })}</span>
              </button>
            </div>
            <div className="onboarding-actions">
              <button className="btn btn-primary" onClick={() => setStep(1)} disabled={!accountType}>
                {t('onboarding.next', { defaultValue: 'Next' })} <ArrowRight size={16} />
              </button>
            </div>
          </div>
        )}

        {/* Step 1: Personal / Business info */}
        {step === 1 && (
          <div className="onboarding-body">
            <div className="onboarding-section-icon">
              {isBusiness ? <Building2 size={20} /> : <User size={20} />}
            </div>
            <h3>{isBusiness
              ? t('onboarding.businessInfo', { defaultValue: 'Business Information' })
              : t('onboarding.personalInfo', { defaultValue: 'Your Information' })
            }</h3>

            <label className="onboarding-label">
              {t('onboarding.yourName', { defaultValue: 'Your name' })} *
              <input className="onboarding-input" value={form.display_name} onChange={set('display_name')}
                placeholder="John Doe" autoFocus />
            </label>

            {isBusiness && (
              <>
                <label className="onboarding-label">
                  {t('onboarding.companyName', { defaultValue: 'Company name' })} *
                  <input className="onboarding-input" value={form.company_name} onChange={set('company_name')}
                    placeholder="Acme B.V." />
                </label>

                <label className="onboarding-label">
                  {t('onboarding.vatNumber', { defaultValue: 'VAT number' })}
                  <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                    <input className="onboarding-input" style={{ flex: 1, marginBottom: 0 }} value={form.vat_number} onChange={set('vat_number')}
                      placeholder="NL123456789B01" />
                    {form.vat_number.trim().length >= 4 && (
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

                <label className="onboarding-label">
                  {t('onboarding.phone', { defaultValue: 'Phone' })}
                  <input className="onboarding-input" value={form.phone} onChange={set('phone')}
                    placeholder="+31 6 12345678" />
                </label>
              </>
            )}

            {error && !isBusiness && <p className="onboarding-error">{error}</p>}

            <div className="onboarding-actions">
              <button className="btn btn-secondary" onClick={() => setStep(0)}>
                {t('onboarding.back', { defaultValue: 'Back' })}
              </button>
              {isBusiness ? (
                <button className="btn btn-primary" onClick={() => setStep(2)} disabled={!step1Valid}>
                  {t('onboarding.next', { defaultValue: 'Next' })} <ArrowRight size={16} />
                </button>
              ) : (
                <button className="btn btn-primary" onClick={handleConsumerFinish} disabled={!step1Valid || saving}>
                  {saving ? <Loader2 size={16} className="spin" /> : null}
                  {t('onboarding.finish', { defaultValue: 'Get Started' })}
                </button>
              )}
            </div>
          </div>
        )}

        {/* Step 2: Billing address (business only) */}
        {step === 2 && isBusiness && (
          <div className="onboarding-body">
            <div className="onboarding-section-icon"><MapPin size={20} /></div>
            <h3>{t('onboarding.billingAddress', { defaultValue: 'Billing Address' })}</h3>

            <label className="onboarding-label">
              {t('onboarding.addressLine1', { defaultValue: 'Address' })} *
              <input className="onboarding-input" value={form.address_line1} onChange={set('address_line1')}
                placeholder="123 Main Street" autoFocus />
            </label>

            <label className="onboarding-label">
              {t('onboarding.addressLine2', { defaultValue: 'Address line 2' })}
              <input className="onboarding-input" value={form.address_line2} onChange={set('address_line2')}
                placeholder="Suite 4B" />
            </label>

            <div className="onboarding-row">
              <label className="onboarding-label" style={{ flex: 2 }}>
                {t('onboarding.city', { defaultValue: 'City' })} *
                <input className="onboarding-input" value={form.city} onChange={set('city')} placeholder="Amsterdam" />
              </label>
              <label className="onboarding-label" style={{ flex: 1 }}>
                {t('onboarding.postalCode', { defaultValue: 'Postal code' })} *
                <input className="onboarding-input" value={form.postal_code} onChange={set('postal_code')} placeholder="1012 AB" />
              </label>
            </div>

            <label className="onboarding-label">
              {t('onboarding.country', { defaultValue: 'Country' })} *
              <select className="onboarding-input" value={form.country} onChange={set('country')}>
                <option value="">{t('onboarding.selectCountry', { defaultValue: 'Select country...' })}</option>
                {EU_COUNTRIES.map(c => (
                  <option key={c.code} value={c.code}>{c.name}</option>
                ))}
              </select>
            </label>

            {error && <p className="onboarding-error">{error}</p>}

            <div className="onboarding-actions">
              <button className="btn btn-secondary" onClick={() => setStep(1)}>
                {t('onboarding.back', { defaultValue: 'Back' })}
              </button>
              <button className="btn btn-primary" onClick={handleFinish} disabled={!step2Valid || saving}>
                {saving ? <Loader2 size={16} className="spin" /> : null}
                {t('onboarding.finish', { defaultValue: 'Get Started' })}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
