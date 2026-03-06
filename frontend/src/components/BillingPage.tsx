import { useState, useEffect } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Coins, ArrowUpRight, ArrowDownRight, Gift, RotateCcw, CheckCircle, XCircle, Clock } from 'lucide-react';
import { api } from '../api';
import type { TokenPackage, TokenTransaction } from '../types';

export default function BillingPage() {
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
          setPaymentBanner({ status: 'paid', message: 'Payment successful! Tokens have been added to your balance.' });
          queryClient.invalidateQueries({ queryKey: ['balance'] });
          queryClient.invalidateQueries({ queryKey: ['transactions'] });
          return;
        }
        if (payment.status === 'failed' || payment.status === 'expired') {
          setPaymentBanner({ status: 'failed', message: `Payment ${payment.status}. No tokens were charged.` });
          return;
        }
        // Still pending — retry up to 10 times (30s total)
        attempts++;
        if (attempts < 10) {
          setTimeout(poll, 3000);
        } else {
          setPaymentBanner({ status: 'pending', message: 'Payment is being processed. Your tokens will appear shortly.' });
        }
      } catch {
        setPaymentBanner({ status: 'pending', message: 'Payment is being processed. Your tokens will appear shortly.' });
      }
    };
    poll();
  }, [queryClient]);

  const { data: balance } = useQuery({
    queryKey: ['balance'],
    queryFn: () => api.getBalance(),
    refetchInterval: 30000,
  });

  const { data: packages } = useQuery({
    queryKey: ['packages'],
    queryFn: () => api.listPackages(),
  });

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
      const msg = err instanceof Error ? err.message : 'Purchase failed';
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
        <div className="billing-balance-label">Token Balance</div>
        <div className="billing-balance-value">
          <Coins size={28} />
          <span>{balance?.token_balance ?? '—'}</span>
        </div>
      </div>

      {/* Packages */}
      <h2 className="billing-section-title">Top Up Tokens</h2>
      <div className="billing-packages-grid">
        {packages?.map((pkg) => (
          <div key={pkg.id} className="billing-package-card">
            <div className="billing-package-name">{pkg.name}</div>
            <div className="billing-package-tokens">{pkg.tokens} tokens</div>
            <div className="billing-package-price">{formatPrice(pkg.price_cents, pkg.currency)}</div>
            <div className="billing-package-per-token">
              {formatPrice(Math.round(pkg.price_cents / pkg.tokens), pkg.currency)}/token
            </div>
            <button
              className="btn btn-primary billing-buy-btn"
              onClick={() => handlePurchase(pkg)}
              disabled={purchaseLoading === pkg.id}
            >
              {purchaseLoading === pkg.id ? 'Redirecting...' : 'Buy Now'}
            </button>
          </div>
        ))}
      </div>

      {/* Transaction History */}
      <h2 className="billing-section-title">Transaction History</h2>
      {transactions && transactions.length > 0 ? (
        <div className="billing-transactions">
          <table className="billing-tx-table">
            <thead>
              <tr>
                <th>Type</th>
                <th>Amount</th>
                <th>Description</th>
                <th>Date</th>
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
          <p>No transactions yet</p>
        </div>
      )}
    </div>
  );
}
