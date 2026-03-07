import { useState, useEffect } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { Coins, ArrowUpRight, ArrowDownRight, Gift, RotateCcw, CheckCircle, XCircle, Clock, Crown } from 'lucide-react';
import { api } from '../api';
import type { TokenPackage, TokenTransaction } from '../types';

export default function BillingPage() {
  const { t } = useTranslation();
  const [purchaseLoading, setPurchaseLoading] = useState<string | null>(null);
  const [paymentBanner, setPaymentBanner] = useState<{ status: string; message: string } | null>(null);
  const queryClient = useQueryClient();

  // Check for payment return (payment_id in URL)
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const paymentId = params.get('payment_id');
    if (!paymentId) return;

    // Clean URL immediately
    const url = new URL(window.location.href);
    url.searchParams.delete('payment_id');
    window.history.replaceState({}, '', url.pathname + url.search);

    // Poll payment status (Mollie webhook may not have arrived yet)
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
        // Still pending — retry up to 10 times (30s total)
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
      // Backend appends payment_id to redirect_url automatically
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
      {subData?.subscription && subData.subscription.status === 'active' && (
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

      {/* Subscription Plans */}
      {(!subData?.subscription || subData.subscription.status !== 'active') && subPlans && subPlans.length > 0 && (
        <>
          <h2 className="billing-section-title">{t('billing.monthlyPlans', { defaultValue: 'Monthly Plans' })}</h2>
          <div className="billing-packages-grid">
            {subPlans.map((plan) => (
              <div key={plan.id} className="billing-package-card billing-sub-card">
                <div className="billing-sub-badge"><Crown size={12} /> Monthly</div>
                <div className="billing-package-name">{plan.name}</div>
                <div className="billing-package-tokens">{plan.tokens_per_month} tokens/month</div>
                <div className="billing-package-price">{formatPrice(plan.price_cents, plan.currency)}/mo</div>
                <div className="billing-package-per-token">
                  {formatPrice(Math.round(plan.price_cents / plan.tokens_per_month), plan.currency)}{t('billing.perToken')}
                </div>
                <button
                  className="btn btn-primary billing-buy-btn"
                  onClick={() => handleSubscribe(plan.id)}
                  disabled={subLoading === plan.id}
                >
                  {subLoading === plan.id ? t('billing.redirecting') : t('billing.subscribe', { defaultValue: 'Subscribe' })}
                </button>
              </div>
            ))}
          </div>
        </>
      )}

      {/* One-time Packages */}
      <h2 className="billing-section-title">{t('billing.topUp')}</h2>
      <div className="billing-packages-grid">
        {packages?.map((pkg) => (
          <div key={pkg.id} className="billing-package-card">
            <div className="billing-package-name">{pkg.name}</div>
            <div className="billing-package-tokens">{pkg.tokens} tokens</div>
            <div className="billing-package-price">{formatPrice(pkg.price_cents, pkg.currency)}</div>
            <div className="billing-package-per-token">
              {formatPrice(Math.round(pkg.price_cents / pkg.tokens), pkg.currency)}{t('billing.perToken')}
            </div>
            <button
              className="btn btn-primary billing-buy-btn"
              onClick={() => handlePurchase(pkg)}
              disabled={purchaseLoading === pkg.id}
            >
              {purchaseLoading === pkg.id ? t('billing.redirecting') : t('billing.buyNow')}
            </button>
          </div>
        ))}
      </div>

      {/* Transaction History */}
      <h2 className="billing-section-title">{t('billing.transactionHistory')}</h2>
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
    </div>
  );
}
