import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import {
  Upload,
  Store,
  Palette,
  Coins,
  ArrowRight,
  Image as ImageIcon,
  CheckCircle,
  Crown,
  Zap,
  TrendingUp,
} from 'lucide-react';
import { api } from '../api';
import type { Page } from './Sidebar';

interface Props {
  onNavigate: (page: Page) => void;
  tokenBalance: number | null;
  hasSubscription: boolean;
}

export default function Dashboard({ onNavigate, tokenBalance, hasSubscription }: Props) {
  const { t } = useTranslation();

  const { data: brands = [] } = useQuery({
    queryKey: ['brand-profiles'],
    queryFn: () => api.listBrandProfiles(),
  });

  const { data: integrations = [] } = useQuery({
    queryKey: ['integrations'],
    queryFn: () => api.listIntegrations(),
  });

  const { data: health } = useQuery({
    queryKey: ['health'],
    queryFn: () => api.checkHealth(),
    refetchInterval: 30000,
  });

  const activeIntegrations = integrations.filter(i => i.status === 'active');
  const isHealthy = health?.status === 'ok';

  return (
    <div className="dashboard">
      <div className="dashboard-welcome">
        <div className="dashboard-welcome-text">
          <h1>{t('dashboard.welcome', { defaultValue: 'Welcome to Opal' })}</h1>
          <p>{t('dashboard.subtitle', { defaultValue: 'AI-powered product image enhancement for e-commerce' })}</p>
        </div>
        <div className="dashboard-status">
          <span className={`dashboard-health ${isHealthy ? '' : 'offline'}`}>
            <span className="status-dot" />
            {isHealthy ? t('common.connected', { defaultValue: 'Connected' }) : t('common.disconnected', { defaultValue: 'Disconnected' })}
          </span>
        </div>
      </div>

      {/* Token Balance Card */}
      <div className="dashboard-balance-card">
        <div className="dashboard-balance-left">
          <div className="dashboard-balance-icon">
            <Coins size={24} />
          </div>
          <div>
            <div className="dashboard-balance-label">{t('dashboard.tokenBalance', { defaultValue: 'Token Balance' })}</div>
            <div className="dashboard-balance-value">{tokenBalance ?? '—'}</div>
          </div>
        </div>
        <div className="dashboard-balance-right">
          {hasSubscription ? (
            <span className="dashboard-sub-badge">
              <Crown size={14} /> {t('dashboard.subscribed', { defaultValue: 'Subscribed' })}
            </span>
          ) : (
            <button className="dashboard-buy-btn" onClick={() => onNavigate('billing')}>
              <Zap size={14} /> {t('dashboard.getTokens', { defaultValue: 'Get Tokens' })}
            </button>
          )}
        </div>
      </div>

      {/* Quick Actions */}
      <div className="dashboard-section">
        <h2 className="dashboard-section-title">
          <TrendingUp size={18} />
          {t('dashboard.quickActions', { defaultValue: 'Quick Actions' })}
        </h2>
        <div className="dashboard-actions-grid">
          <button className="dashboard-action-card" onClick={() => onNavigate('upload')}>
            <div className="dashboard-action-icon action-upload">
              <Upload size={24} />
            </div>
            <div className="dashboard-action-info">
              <h3>{t('dashboard.uploadImages', { defaultValue: 'Upload & Process' })}</h3>
              <p>{t('dashboard.uploadDesc', { defaultValue: 'Remove backgrounds, generate scenes, upscale' })}</p>
            </div>
            <ArrowRight size={16} className="dashboard-action-arrow" />
          </button>

          <button className="dashboard-action-card" onClick={() => onNavigate('integrations')}>
            <div className="dashboard-action-icon action-store">
              <Store size={24} />
            </div>
            <div className="dashboard-action-info">
              <h3>{t('dashboard.processFromStore', { defaultValue: 'Process from Store' })}</h3>
              <p>{t('dashboard.storeDesc', { defaultValue: 'Shopify, WooCommerce, Etsy integrations' })}</p>
            </div>
            <ArrowRight size={16} className="dashboard-action-arrow" />
          </button>

          <button className="dashboard-action-card" onClick={() => onNavigate('brands')}>
            <div className="dashboard-action-icon action-brand">
              <Palette size={24} />
            </div>
            <div className="dashboard-action-info">
              <h3>{t('dashboard.manageBrands', { defaultValue: 'Brand Profiles' })}</h3>
              <p>{t('dashboard.brandDesc', { defaultValue: 'Colors, moods, scene templates' })}</p>
            </div>
            <ArrowRight size={16} className="dashboard-action-arrow" />
          </button>

          <button className="dashboard-action-card" onClick={() => onNavigate('results')}>
            <div className="dashboard-action-icon action-results">
              <ImageIcon size={24} />
            </div>
            <div className="dashboard-action-info">
              <h3>{t('dashboard.viewResults', { defaultValue: 'View Results' })}</h3>
              <p>{t('dashboard.resultsDesc', { defaultValue: 'Download, export, push to stores' })}</p>
            </div>
            <ArrowRight size={16} className="dashboard-action-arrow" />
          </button>
        </div>
      </div>

      {/* Stats Row */}
      <div className="dashboard-stats-row">
        <div className="dashboard-stat-card">
          <Palette size={18} />
          <div className="dashboard-stat-info">
            <span className="dashboard-stat-value">{brands.length}</span>
            <span className="dashboard-stat-label">{t('dashboard.brandProfiles', { defaultValue: 'Brand Profiles' })}</span>
          </div>
          {brands.length === 0 && (
            <button className="dashboard-stat-action" onClick={() => onNavigate('brands')}>
              {t('dashboard.create', { defaultValue: 'Create' })}
            </button>
          )}
        </div>

        <div className="dashboard-stat-card">
          <Store size={18} />
          <div className="dashboard-stat-info">
            <span className="dashboard-stat-value">{activeIntegrations.length}</span>
            <span className="dashboard-stat-label">{t('dashboard.connectedStores', { defaultValue: 'Connected Stores' })}</span>
          </div>
          {activeIntegrations.length === 0 && (
            <button className="dashboard-stat-action" onClick={() => onNavigate('integrations')}>
              {t('dashboard.connect', { defaultValue: 'Connect' })}
            </button>
          )}
        </div>

        <div className="dashboard-stat-card">
          <Coins size={18} />
          <div className="dashboard-stat-info">
            <span className="dashboard-stat-value">{tokenBalance ?? 0}</span>
            <span className="dashboard-stat-label">{t('dashboard.tokensAvailable', { defaultValue: 'Tokens Available' })}</span>
          </div>
          {(tokenBalance ?? 0) === 0 && (
            <button className="dashboard-stat-action" onClick={() => onNavigate('billing')}>
              {t('dashboard.topUp', { defaultValue: 'Top Up' })}
            </button>
          )}
        </div>
      </div>

      {/* Connected Integrations Preview */}
      {activeIntegrations.length > 0 && (
        <div className="dashboard-section">
          <h2 className="dashboard-section-title">
            <Store size={18} />
            {t('dashboard.yourStores', { defaultValue: 'Your Stores' })}
          </h2>
          <div className="dashboard-integrations-list">
            {activeIntegrations.map(integ => (
              <div key={integ.id} className="dashboard-integration-item">
                <div className="dashboard-integration-provider">{integ.provider}</div>
                <div className="dashboard-integration-name">
                  {integ.provider_metadata?.shop_name || integ.store_url}
                </div>
                <span className="dashboard-integration-status">
                  <CheckCircle size={12} /> {t('common.connected', { defaultValue: 'Active' })}
                </span>
              </div>
            ))}
            <button className="dashboard-integration-add" onClick={() => onNavigate('integrations')}>
              + {t('dashboard.addStore', { defaultValue: 'Add another store' })}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
