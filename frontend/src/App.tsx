import { useState, useEffect, useRef, useCallback } from 'react';
import { QueryClient, QueryClientProvider, useQuery } from '@tanstack/react-query';
import { Upload, Activity, Image as ImageIcon, Palette, BookImage, CreditCard, LogOut, Coins, Store, Settings } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import UploadSection from './components/UploadSection';
import JobMonitor from './components/JobMonitor';
import ResultsGallery from './components/ResultsGallery';
import BrandProfiles from './components/BrandProfiles';
import SceneLibrary from './components/SceneLibrary';
import BillingPage from './components/BillingPage';
import IntegrationsPage from './components/IntegrationsPage';
import AdminPage from './components/AdminPage';
import LandingPage from './components/LandingPage';
import LanguageSelector from './components/LanguageSelector';
import { api } from './api';
import { initializeMsal, isAuthConfigured, getAccount, getAccessToken, login, logout } from './auth';
import './App.css';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

type Tab = 'upload' | 'monitor' | 'results' | 'brands' | 'library' | 'integrations' | 'billing' | 'admin';

function AppContent({ isAdmin }: { isAdmin: boolean }) {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState<Tab>(() => {
    // Auto-switch to billing tab when returning from payment
    const params = new URLSearchParams(window.location.search);
    if (params.has('payment_id')) return 'billing';
    // Auto-switch to integrations tab when returning from Shopify OAuth
    if (params.get('tab') === 'integrations') return 'integrations';
    return 'upload';
  });
  const [currentJobId, setCurrentJobId] = useState<string | null>(() => {
    return localStorage.getItem('currentJobId');
  });
  const prevJobStatusRef = useRef<string | null>(null);

  const handleJobCreated = (jobId: string) => {
    setCurrentJobId(jobId);
    localStorage.setItem('currentJobId', jobId);
    setActiveTab('monitor');
  };

  const allTabs = [
    { id: 'upload' as Tab, label: t('app.tabs.upload'), icon: Upload },
    { id: 'monitor' as Tab, label: t('app.tabs.monitor'), icon: Activity },
    { id: 'results' as Tab, label: t('app.tabs.results'), icon: ImageIcon },
    { id: 'brands' as Tab, label: t('app.tabs.brands'), icon: Palette },
    { id: 'library' as Tab, label: t('app.tabs.library'), icon: BookImage },
    { id: 'integrations' as Tab, label: t('app.tabs.integrations'), icon: Store },
    { id: 'billing' as Tab, label: t('app.tabs.billing'), icon: CreditCard },
    { id: 'admin' as Tab, label: t('app.tabs.admin'), icon: Settings, adminOnly: true },
  ];

  const tabs = allTabs.filter(t => !('adminOnly' in t) || isAdmin);

  const { data: health } = useQuery({
    queryKey: ['health'],
    queryFn: () => api.checkHealth(),
    refetchInterval: 30000,
  });

  const { data: currentJob } = useQuery({
    queryKey: ['job-nav', currentJobId],
    queryFn: () => api.getJob(currentJobId!),
    enabled: !!currentJobId && activeTab === 'monitor',
    refetchInterval: 3000,
  });

  useEffect(() => {
    if (!currentJob) return;
    const prevStatus = prevJobStatusRef.current;
    const newStatus = currentJob.status;
    prevJobStatusRef.current = newStatus;

    if (
      prevStatus === 'processing' &&
      (newStatus === 'completed' || newStatus === 'failed' || newStatus === 'partial') &&
      activeTab === 'monitor'
    ) {
      setActiveTab('results');
    }
  }, [currentJob, activeTab]);

  const isHealthy = health?.status === 'ok';

  return (
    <div className="app">
      <header className="header">
        <div className="container">
          <div className="header-content">
            <h1 className="logo">
              <span className="logo-icon">&#9670;</span>
              OPAL
              <span className="logo-subtitle">{t('app.subtitle')}</span>
            </h1>
            <div className="header-info">
              <span className="api-status">
                <span className={`status-dot ${isHealthy ? '' : 'status-dot-error'}`}></span>
                {isHealthy ? t('common.connected') : t('common.disconnected')}
              </span>
            </div>
          </div>
        </div>
      </header>

      <nav className="tabs">
        <div className="container">
          <div className="tabs-list">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                className={`tab ${activeTab === tab.id ? 'active' : ''}`}
                onClick={() => setActiveTab(tab.id)}
              >
                <tab.icon size={18} />
                {tab.label}
              </button>
            ))}
          </div>
        </div>
      </nav>

      <main className="main">
        <div className="container">
          {activeTab === 'upload' && (
            <UploadSection onJobCreated={handleJobCreated} />
          )}
          {activeTab === 'monitor' && (
            <JobMonitor jobId={currentJobId} />
          )}
          {activeTab === 'results' && (
            <ResultsGallery jobId={currentJobId} />
          )}
          {activeTab === 'brands' && <BrandProfiles />}
          {activeTab === 'library' && <SceneLibrary />}
          {activeTab === 'integrations' && <IntegrationsPage />}
          {activeTab === 'billing' && <BillingPage />}
          {activeTab === 'admin' && <AdminPage />}
        </div>
      </main>

      <footer className="footer">
        <div className="container">
          <p>{t('app.footer')}</p>
        </div>
      </footer>
    </div>
  );
}

function AuthenticatedApp({ userEmail, onLogout }: { userEmail: string; onLogout: () => void }) {
  const { t } = useTranslation();
  const { data: balance } = useQuery({
    queryKey: ['balance'],
    queryFn: () => api.getBalance(),
    refetchInterval: 30000,
  });

  const isAdmin = balance?.is_admin ?? false;

  return (
    <>
      <div className="auth-bar">
        <div className="container">
          <div className="auth-bar-content">
            <span className="auth-user-email">{userEmail}</span>
            {balance && (
              <span className="auth-token-balance">
                <Coins size={14} />
                {balance.token_balance} {t('common.tokens')}
              </span>
            )}
            <LanguageSelector />
            <button className="auth-logout-btn" onClick={onLogout}>
              <LogOut size={14} />
              {t('common.signOut')}
            </button>
          </div>
        </div>
      </div>
      <AppContent isAdmin={isAdmin} />
    </>
  );
}

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [userEmail, setUserEmail] = useState('');
  const [msalReady, setMsalReady] = useState(false);
  const authEnabled = isAuthConfigured();

  useEffect(() => {
    if (!authEnabled) {
      setMsalReady(true);
      setIsAuthenticated(true);
      return;
    }

    initializeMsal().then(async () => {
      setMsalReady(true);
      const account = getAccount();
      if (account) {
        const token = await getAccessToken();
        if (token) {
          api.setAccessToken(token);
          setUserEmail(account.username || account.name || '');
          setIsAuthenticated(true);
        }
      }
    });
  }, [authEnabled]);

  // Refresh token periodically (every 5 min)
  useEffect(() => {
    if (!authEnabled || !isAuthenticated) return;
    const interval = setInterval(async () => {
      const token = await getAccessToken();
      if (token) api.setAccessToken(token);
    }, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, [authEnabled, isAuthenticated]);

  const handleLoginSuccess = useCallback(async () => {
    const account = getAccount();
    if (account) {
      const token = await getAccessToken();
      if (token) {
        api.setAccessToken(token);
        setUserEmail(account.username || account.name || '');
        setIsAuthenticated(true);
      }
    }
  }, []);

  const handleLogout = useCallback(async () => {
    await logout();
    api.setAccessToken(null);
    setIsAuthenticated(false);
    setUserEmail('');
  }, []);

  const handleGetStarted = useCallback(async () => {
    if (!authEnabled) {
      // No auth configured — go straight to app
      setIsAuthenticated(true);
      return;
    }
    try {
      await login();
      await handleLoginSuccess();
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '';
      if (!msg.includes('user_cancelled')) {
        console.error('Login failed:', msg);
      }
    }
  }, [authEnabled, handleLoginSuccess]);

  if (!msalReady) {
    return (
      <div className="app">
        <div className="login-page">
          <div className="login-card">
            <p>Loading...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <QueryClientProvider client={queryClient}>
      {isAuthenticated ? (
        <AuthenticatedApp userEmail={userEmail} onLogout={handleLogout} />
      ) : (
        <LandingPage onGetStarted={handleGetStarted} />
      )}
    </QueryClientProvider>
  );
}

export default App;
