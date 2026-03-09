import { useState, useEffect } from 'react';
import { useQuery, useQueryClient, useMutation } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import {
  Coins, ArrowUpRight, ArrowDownRight, Gift, RotateCcw,
  CheckCircle, XCircle, Clock, Crown, Check, Zap, Repeat,
  ShoppingBag, Key, Plus, Copy, Trash2, AlertTriangle,
} from 'lucide-react';
import { api } from '../api';
import type { TokenPackage, TokenTransaction, ApiKeyCreateResponse } from '../types';

type PricingTab = 'subscriptions' | 'packs';

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
      alert(err.message || t('billing.apiKeys.generateFailed'));
    },
  });

  const revokeMutation = useMutation({
    mutationFn: (keyId: string) => api.revokeApiKey(keyId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['api-keys'] });
    },
    onError: (err: Error) => {
      alert(err.message || t('billing.apiKeys.revokeFailed'));
    },
  });

  const handleGenerate = () => {
    createMutation.mutate(newKeyName || undefined);
  };

  const handleRevoke = (keyId: string) => {
    if (!confirm(t('billing.apiKeys.revokeConfirm'))) return;
    revokeMutation.mutate(keyId);
  };

  const handleCopy = async () => {
    if (!newlyCreatedKey) return;
    try {
      await navigator.clipboard.writeText(newlyCreatedKey.key);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback: select the text
      const input = document.querySelector('.apikey-reveal-input') as HTMLInputElement;
      if (input) { input.select(); document.execCommand('copy'); setCopied(true); setTimeout(() => setCopied(false), 2000); }
    }
  };

  return (
    <div className="apikeys-section">
      <h2 className="billing-section-title" style={{ marginTop: '2rem' }}>
        <Key size={20} />
        {t('billing.apiKeys.title')}
      </h2>
      <p className="apikeys-description">{t('billing.apiKeys.description')}</p>

      {/* Newly created key reveal */}
      {newlyCreatedKey && (
        <div className="apikey-reveal">
          <div className="apikey-reveal-header">
            <AlertTriangle size={18} />
            <strong>{t('billing.apiKeys.newKeyTitle')}</strong>
          </div>
          <p className="apikey-reveal-warning">{t('billing.apiKeys.newKeyWarning')}</p>
          <div className="apikey-reveal-box">
            <input
              type="text"
              readOnly
              value={newlyCreatedKey.key}
              className="apikey-reveal-input"
              onClick={(e) => (e.target as HTMLInputElement).select()}
            />
            <button className="btn btn-sm apikey-copy-btn" onClick={handleCopy}>
              <Copy size={14} />
              {copied ? t('billing.apiKeys.copied') : t('billing.apiKeys.copyKey')}
            </button>
          </div>
          <button
            className="btn btn-sm apikey-done-btn"
            onClick={() => setNewlyCreatedKey(null)}
          >
            {t('billing.apiKeys.done')}
          </button>
        </div>
      )}

      {/* Generate form */}
      {showGenerateForm && !newlyCreatedKey && (
        <div className="apikey-generate-form">
          <input
            type="text"
            value={newKeyName}
            onChange={(e) => setNewKeyName(e.target.value)}
            placeholder={t('billing.apiKeys.namePlaceholder')}
            className="apikey-name-input"
          />
          <div className="apikey-generate-actions">
            <button
              className="billing-pricing-btn billing-pricing-btn-primary"
              onClick={handleGenerate}
              disabled={createMutation.isPending}
            >
              {createMutation.isPending ? t('billing.apiKeys.generating') : t('billing.apiKeys.generateNew')}
            </button>
            <button
              className="btn btn-ghost"
              onClick={() => { setShowGenerateForm(false); setNewKeyName(''); }}
            >
              {t('common.cancel')}
            </button>
          </div>
        </div>
      )}

      {/* Generate button */}
      {!showGenerateForm && !newlyCreatedKey && (
        <button
          className="apikey-generate-btn"
          onClick={() => setShowGenerateForm(true)}
        >
          <Plus size={16} />
          {t('billing.apiKeys.generateNew')}
        </button>
      )}

      {/* Keys list */}
      {isLoading ? (
        <p style={{ color: 'rgba(200,205,224,0.6)', padding: '1rem 0' }}>{t('common.loading')}</p>
      ) : apiKeys && apiKeys.length > 0 ? (
        <div className="billing-transactions">
          <table className="billing-tx-table apikeys-table">
            <thead>
              <tr>
                <th>{t('billing.apiKeys.name')}</th>
                <th>{t('billing.apiKeys.prefix')}</th>
                <th>{t('billing.apiKeys.created')}</th>
                <th>{t('billing.apiKeys.lastUsed')}</th>
                <th>{t('billing.apiKeys.actions')}</th>
              </tr>
            </thead>
            <tbody>
              {apiKeys.map((key) => (
                <tr key={key.id}>
                  <td>{key.name || '—'}</td>
                  <td><code className="apikey-prefix">{key.prefix}...</code></td>
                  <td>{new Date(key.created_at).toLocaleDateString()}</td>
                  <td>{key.last_used_at ? new Date(key.last_used_at).toLocaleDateString() : t('billing.apiKeys.never')}</td>
                  <td>
                    <button
                      className="apikey-revoke-btn"
                      onClick={() => handleRevoke(key.id)}
                      disabled={revokeMutation.isPending}
                      title={t('billing.apiKeys.revoke')}
                    >
                      <Trash2 size={14} />
                      {t('billing.apiKeys.revoke')}
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
          <p>{t('billing.apiKeys.noKeys')}</p>
          <p style={{ fontSize: '0.8rem', color: 'rgba(200,205,224,0.5)' }}>{t('billing.apiKeys.noKeysHint')}</p>
        </div>
      )}
    </div>
  );
}

export default function BillingPage() {
  const { t } = useTranslation();
  const [purchaseLoading, setPurchaseLoading] = useState<string | null>(null);
  const [paymentBanner, setPaymentBanner] = useState<{ status: string; message: string } | null>(null);
  const [pricingTab, setPricingTab] = useState<PricingTab>('subscriptions');
  const queryClient = useQueryClient();

  // Check for payment return (payment_id in URL)
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const paymentId = params.get('payment_id');
    if (!paymentId) return;

    const url = new URL(window.location.href);
    url.searchParams.delete('payment_id');
    window.history.replaceState({}, '', url.pathname + url.search);

    let attempts = 0;
    const poll = async () => {
      try {
        const payment = await api.getPaymentStatus(paymentId);
        if (payment.status === 'paid') {
          setPaymentBanner({ status: 'paid', message: t('billing.paymentSuccess') });
          queryClient.invalidateQueries({ queryKey: ['balance'] });
          queryClient.invalidateQueries({ queryKey: ['transactions'] });
          return;
        }
        if (payment.status === 'failed' || payment.status === 'expired') {
          setPaymentBanner({ status: 'failed', message: t('billing.paymentFailed', { status: payment.status }) });
          return;
        }
        attempts++;
        if (attempts < 10) {
          setTimeout(poll, 3000);
        } else {
          setPaymentBanner({ status: 'pending', message: t('billing.paymentPending') });
        }
      } catch {
        setPaymentBanner({ status: 'pending', message: t('billing.paymentPending') });
      }
    };
    poll();
  }, [queryClient, t]);

  const { data: balance } = useQuery({
    queryKey: ['balance'],
    queryFn: () => api.getBalance(),
    refetchInterval: 30000,
  });

  const { data: packages } = useQuery({
    queryKey: ['packages'],
    queryFn: () => api.listPackages(),
  });

  const { data: subPlans } = useQuery({
    queryKey: ['subscription-plans'],
    queryFn: () => api.listSubscriptionPlans(),
  });

  const { data: subData } = useQuery({
    queryKey: ['subscription'],
    queryFn: () => api.getSubscription(),
  });

  const [subLoading, setSubLoading] = useState<string | null>(null);
  const [cancelLoading, setCancelLoading] = useState(false);

  const handleSubscribe = async (planId: string) => {
    setSubLoading(planId);
    try {
      const redirectUrl = window.location.origin + window.location.pathname;
      const result = await api.subscribe(planId, redirectUrl);
      window.location.href = result.payment_url;
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : t('billing.subscribeFailed', { defaultValue: 'Failed to start subscription' });
      alert(msg);
      setSubLoading(null);
    }
  };

  const handleCancel = async () => {
    if (!confirm(t('billing.cancelConfirm', { defaultValue: 'Are you sure you want to cancel your subscription?' }))) return;
    setCancelLoading(true);
    try {
      await api.cancelSubscription();
      queryClient.invalidateQueries({ queryKey: ['subscription'] });
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed');
    } finally {
      setCancelLoading(false);
    }
  };

  const { data: transactions } = useQuery({
    queryKey: ['transactions'],
    queryFn: () => api.listTransactions(),
  });

  const handlePurchase = async (pkg: TokenPackage) => {
    setPurchaseLoading(pkg.id);
    try {
      const redirectUrl = window.location.origin + window.location.pathname;
      const result = await api.purchaseTokens(pkg.id, redirectUrl);
      window.location.href = result.payment_url;
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : t('billing.purchaseFailed');
      alert(msg);
      setPurchaseLoading(null);
    }
  };

  const formatPrice = (cents: number, currency: string) => {
    return new Intl.NumberFormat('en-EU', {
      style: 'currency',
      currency,
    }).format(cents / 100);
  };

  const txIcon = (type: string) => {
    switch (type) {
      case 'purchase': return <ArrowUpRight size={14} className="tx-icon tx-credit" />;
      case 'bonus': return <Gift size={14} className="tx-icon tx-credit" />;
      case 'refund': return <RotateCcw size={14} className="tx-icon tx-credit" />;
      case 'usage': return <ArrowDownRight size={14} className="tx-icon tx-debit" />;
      default: return null;
    }
  };

  const hasActiveSub = subData?.subscription?.status === 'active';

  // Find recommended plan/pack (second item)
  const recommendedPlanId = subPlans && subPlans.length > 1 ? subPlans[1].id : null;
  const recommendedPkgId = packages && packages.length > 1 ? packages[1].id : null;

  return (
    <div className="billing-page">
      {/* Payment Status Banner */}
      {paymentBanner && (
        <div className={`billing-payment-banner billing-banner-${paymentBanner.status}`}>
          {paymentBanner.status === 'paid' && <CheckCircle size={20} />}
          {paymentBanner.status === 'failed' && <XCircle size={20} />}
          {paymentBanner.status === 'pending' && <Clock size={20} />}
          <span>{paymentBanner.message}</span>
          <button className="billing-banner-dismiss" onClick={() => setPaymentBanner(null)}>&times;</button>
        </div>
      )}

      {/* Balance Card */}
      <div className="billing-balance-card">
        <div className="billing-balance-label">{t('billing.tokenBalance')}</div>
        <div className="billing-balance-value">
          <Coins size={28} />
          <span>{balance?.token_balance ?? '—'}</span>
        </div>
      </div>

      {/* Active Subscription */}
      {hasActiveSub && subData?.subscription && (
        <div className="billing-sub-active">
          <div className="billing-sub-active-info">
            <Crown size={20} />
            <div>
              <strong>{subData.subscription.plan?.name || 'Subscription'}</strong>
              <span className="billing-sub-detail">
                {subData.subscription.plan?.tokens_per_month} tokens/month
                {subData.subscription.current_period_end && (
                  <> · {t('billing.renews', { defaultValue: 'Renews' })} {new Date(subData.subscription.current_period_end).toLocaleDateString()}</>
                )}
              </span>
            </div>
          </div>
          <button
            className="button-secondary button-sm"
            onClick={handleCancel}
            disabled={cancelLoading}
          >
            {cancelLoading ? t('common.processing', { defaultValue: 'Processing...' }) : t('billing.cancelSubscription', { defaultValue: 'Cancel' })}
          </button>
        </div>
      )}

      {/* Pricing Tab Toggle */}
      <div className="billing-tab-toggle">
        <button
          className={`billing-tab-btn ${pricingTab === 'subscriptions' ? 'active' : ''}`}
          onClick={() => setPricingTab('subscriptions')}
        >
          <Repeat size={15} />
          {t('billing.monthlyPlans', { defaultValue: 'Monthly Plans' })}
          <span className="billing-tab-save">{t('billing.saveBadge', { defaultValue: 'Save more' })}</span>
        </button>
        <button
          className={`billing-tab-btn ${pricingTab === 'packs' ? 'active' : ''}`}
          onClick={() => setPricingTab('packs')}
        >
          <ShoppingBag size={15} />
          {t('billing.tokenPacks', { defaultValue: 'Token Packs' })}
        </button>
      </div>

      {/* Subscription Plans */}
      {pricingTab === 'subscriptions' && subPlans && subPlans.length > 0 && (
        <div className="billing-pricing-grid">
          {subPlans.map((plan) => {
            const isRecommended = plan.id === recommendedPlanId;
            const perToken = plan.price_cents / plan.tokens_per_month / 100;
            return (
              <div
                key={plan.id}
                className={`billing-pricing-card ${isRecommended ? 'billing-pricing-recommended' : ''}`}
              >
                {isRecommended && (
                  <div className="billing-pricing-badge">
                    <Zap size={10} />
                    {t('billing.recommended', { defaultValue: 'Best value' })}
                  </div>
                )}
                <div className="billing-pricing-name">{plan.name}</div>
                <div className="billing-pricing-price">
                  {formatPrice(plan.price_cents, plan.currency)}
                  <span className="billing-pricing-interval">/mo</span>
                </div>
                <div className="billing-pricing-tokens">
                  {plan.tokens_per_month} {t('common.tokens')}
                </div>
                <div className="billing-pricing-per">
                  {formatPrice(Math.round(perToken * 100), plan.currency)}{t('billing.perToken')}
                </div>
                <ul className="billing-pricing-features">
                  <li><Check size={14} /> {t('billing.featureAllIncluded', { defaultValue: 'All features included' })}</li>
                  <li><Check size={14} /> {t('billing.featureRollover', { defaultValue: 'Unused tokens roll over' })}</li>
                  {plan.tokens_per_month >= 100 && (
                    <li><Check size={14} /> {t('billing.featureBulk', { defaultValue: 'Bulk catalog processing' })}</li>
                  )}
                  {plan.tokens_per_month >= 500 && (
                    <li><Check size={14} /> {t('billing.featurePriority', { defaultValue: 'Priority processing' })}</li>
                  )}
                  {plan.tokens_per_month >= 2000 && (
                    <li><Check size={14} /> {t('billing.featureDedicated', { defaultValue: 'Dedicated support' })}</li>
                  )}
                </ul>
                <button
                  className={`billing-pricing-btn ${isRecommended ? 'billing-pricing-btn-primary' : ''}`}
                  onClick={() => handleSubscribe(plan.id)}
                  disabled={subLoading === plan.id || hasActiveSub}
                >
                  {subLoading === plan.id
                    ? t('billing.redirecting')
                    : hasActiveSub
                      ? t('billing.currentPlan', { defaultValue: 'Active plan' })
                      : t('billing.subscribe', { defaultValue: 'Subscribe' })}
                </button>
              </div>
            );
          })}
        </div>
      )}

      {/* One-time Token Packs */}
      {pricingTab === 'packs' && packages && packages.length > 0 && (
        <div className="billing-pricing-grid">
          {packages.map((pkg) => {
            const isRecommended = pkg.id === recommendedPkgId;
            const perToken = pkg.price_cents / pkg.tokens / 100;
            return (
              <div
                key={pkg.id}
                className={`billing-pricing-card ${isRecommended ? 'billing-pricing-recommended' : ''}`}
              >
                {isRecommended && (
                  <div className="billing-pricing-badge">
                    <Zap size={10} />
                    {t('billing.recommended', { defaultValue: 'Best value' })}
                  </div>
                )}
                <div className="billing-pricing-name">{pkg.name}</div>
                <div className="billing-pricing-price">
                  {formatPrice(pkg.price_cents, pkg.currency)}
                </div>
                <div className="billing-pricing-tokens">
                  {pkg.tokens} {t('common.tokens')}
                </div>
                <div className="billing-pricing-per">
                  {formatPrice(Math.round(perToken * 100), pkg.currency)}{t('billing.perToken')}
                </div>
                <ul className="billing-pricing-features">
                  <li><Check size={14} /> {t('billing.featureAllIncluded', { defaultValue: 'All features included' })}</li>
                  <li><Check size={14} /> {t('billing.featureNeverExpire', { defaultValue: 'Tokens never expire' })}</li>
                  <li><Check size={14} /> {t('billing.featureIntegrations', { defaultValue: 'Shopify, Etsy & WooCommerce' })}</li>
                  {pkg.tokens >= 100 && (
                    <li><Check size={14} /> {t('billing.featureBulk', { defaultValue: 'Bulk catalog processing' })}</li>
                  )}
                  {pkg.tokens >= 2000 && (
                    <li><Check size={14} /> {t('billing.featurePriority', { defaultValue: 'Priority processing' })}</li>
                  )}
                </ul>
                <button
                  className={`billing-pricing-btn ${isRecommended ? 'billing-pricing-btn-primary' : ''}`}
                  onClick={() => handlePurchase(pkg)}
                  disabled={purchaseLoading === pkg.id}
                >
                  {purchaseLoading === pkg.id ? t('billing.redirecting') : t('billing.buyNow')}
                </button>
              </div>
            );
          })}
        </div>
      )}

      {/* Transaction History */}
      <h2 className="billing-section-title" style={{ marginTop: '2rem' }}>{t('billing.transactionHistory')}</h2>
      {transactions && transactions.length > 0 ? (
        <div className="billing-transactions">
          <table className="billing-tx-table">
            <thead>
              <tr>
                <th>{t('billing.type')}</th>
                <th>{t('billing.amount')}</th>
                <th>{t('billing.description')}</th>
                <th>{t('billing.date')}</th>
              </tr>
            </thead>
            <tbody>
              {transactions.map((tx: TokenTransaction) => (
                <tr key={tx.id}>
                  <td className="tx-type-cell">
                    {txIcon(tx.type)}
                    <span>{tx.type}</span>
                  </td>
                  <td className={tx.amount > 0 ? 'tx-amount-positive' : 'tx-amount-negative'}>
                    {tx.amount > 0 ? '+' : ''}{tx.amount}
                  </td>
                  <td>{tx.description || '—'}</td>
                  <td>{new Date(tx.created_at).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="empty-state">
          <Coins size={48} />
          <p>{t('billing.noTransactions')}</p>
        </div>
      )}

      {/* API Keys Section */}
      <ApiKeysSection />
    </div>
  );
}
