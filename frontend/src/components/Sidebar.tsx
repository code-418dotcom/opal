import { useTranslation } from 'react-i18next';
import {
  LayoutDashboard,
  Upload,
  Activity,
  Image as ImageIcon,
  Palette,
  Store,
  ShoppingBag,
  Target,
  CreditCard,
  Settings,
  SlidersHorizontal,
  ChevronLeft,
  ChevronRight,
  Coins,
  LogOut,
} from 'lucide-react';
import LanguageSelector from './LanguageSelector';
import OpalLogo from './OpalLogo';

export type Page =
  | 'dashboard'
  | 'upload'
  | 'monitor'
  | 'results'
  | 'brands'
  | 'integrations'
  | 'products'
  | 'benchmarks'
  | 'billing'
  | 'settings'
  | 'admin';

interface Props {
  activePage: Page;
  onNavigate: (page: Page) => void;
  collapsed: boolean;
  onToggleCollapse: () => void;
  isAdmin: boolean;
  hasConnectedStores: boolean;
  tokenBalance: number | null;
  userEmail: string;
  onLogout: () => void;
}

export default function Sidebar({
  activePage,
  onNavigate,
  collapsed,
  onToggleCollapse,
  isAdmin,
  hasConnectedStores,
  tokenBalance,
  userEmail,
  onLogout,
}: Props) {
  const { t } = useTranslation();

  const navItems = [
    { id: 'dashboard' as Page, icon: LayoutDashboard, label: t('nav.dashboard', { defaultValue: 'Dashboard' }) },
    { id: 'upload' as Page, icon: Upload, label: t('nav.process', { defaultValue: 'Process Images' }) },
    { id: 'monitor' as Page, icon: Activity, label: t('nav.monitor', { defaultValue: 'Job Monitor' }) },
    { id: 'results' as Page, icon: ImageIcon, label: t('nav.results', { defaultValue: 'Results' }) },
    { id: 'brands' as Page, icon: Palette, label: t('nav.brands', { defaultValue: 'Brands & Scenes' }) },
    { id: 'integrations' as Page, icon: Store, label: t('nav.integrations', { defaultValue: 'Integrations' }) },
    ...(hasConnectedStores ? [{ id: 'products' as Page, icon: ShoppingBag, label: t('nav.products', { defaultValue: 'Products' }) }] : []),
    { id: 'benchmarks' as Page, icon: Target, label: t('nav.benchmarks', { defaultValue: 'Image Score' }) },
    { id: 'billing' as Page, icon: CreditCard, label: t('nav.billing', { defaultValue: 'Billing' }) },
    { id: 'settings' as Page, icon: SlidersHorizontal, label: t('nav.settings', { defaultValue: 'Settings' }) },
    ...(isAdmin ? [{ id: 'admin' as Page, icon: Settings, label: t('nav.admin', { defaultValue: 'Admin' }) }] : []),
  ];

  return (
    <aside className={`sidebar ${collapsed ? 'sidebar-collapsed' : ''}`}>
      <div className="sidebar-header">
        <div className="sidebar-logo" onClick={() => onNavigate('dashboard')}>
          <span className="sidebar-logo-icon"><OpalLogo size={22} /></span>
          {!collapsed && <span className="sidebar-logo-text">OPAL</span>}
        </div>
        <button className="sidebar-toggle" onClick={onToggleCollapse}>
          {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
        </button>
      </div>

      <nav className="sidebar-nav">
        {navItems.map((item) => (
          <button
            key={item.id}
            className={`sidebar-nav-item ${activePage === item.id ? 'active' : ''}`}
            onClick={() => onNavigate(item.id)}
            title={collapsed ? item.label : undefined}
          >
            <item.icon size={20} />
            {!collapsed && <span>{item.label}</span>}
          </button>
        ))}
      </nav>

      <div className="sidebar-footer">
        {!collapsed && (
          <div className="sidebar-balance">
            <Coins size={16} />
            <span>{tokenBalance ?? '—'} {t('common.tokens', { defaultValue: 'tokens' })}</span>
          </div>
        )}
        {collapsed && (
          <div className="sidebar-balance-mini" title={`${tokenBalance ?? '—'} tokens`}>
            <Coins size={16} />
          </div>
        )}

        {!collapsed && (
          <div className="sidebar-user">
            <div className="sidebar-user-email" title={userEmail}>
              {userEmail}
            </div>
            <div className="sidebar-user-actions">
              <LanguageSelector />
              <button className="sidebar-logout" onClick={onLogout} title={t('common.signOut', { defaultValue: 'Sign out' })}>
                <LogOut size={14} />
              </button>
            </div>
          </div>
        )}
        {collapsed && (
          <button className="sidebar-logout sidebar-logout-mini" onClick={onLogout} title={t('common.signOut', { defaultValue: 'Sign out' })}>
            <LogOut size={16} />
          </button>
        )}
      </div>
    </aside>
  );
}
