import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Coins, ArrowUpRight, ArrowDownRight, Gift, RotateCcw } from 'lucide-react';
import { api } from '../api';
import type { TokenPackage, TokenTransaction } from '../types';

export default function BillingPage() {
  const [purchaseLoading, setPurchaseLoading] = useState<string | null>(null);

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
      const result = await api.purchaseTokens(pkg.id, window.location.href);
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
