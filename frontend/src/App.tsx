import { useState, useEffect, useRef, useCallback } from 'react';
import { QueryClient, QueryClientProvider, useQuery } from '@tanstack/react-query';
import Sidebar, { type Page } from './components/Sidebar';
import Dashboard from './components/Dashboard';
import OnboardingWizard from './components/OnboardingWizard';
import UploadSection from './components/UploadSection';
import JobMonitor from './components/JobMonitor';
import ResultsGallery from './components/ResultsGallery';
import type { Job } from './types';
import BrandProfiles from './components/BrandProfiles';
import SceneLibrary from './components/SceneLibrary';
import BillingPage from './components/BillingPage';
import IntegrationsPage from './components/IntegrationsPage';
import ProductsPage from './components/ProductsPage';
import ABTestPage from './components/ABTestPage';
import BenchmarkPage from './components/BenchmarkPage';
import AdminPage from './components/AdminPage';
import SettingsPage from './components/SettingsPage';
import LandingPage from './components/LandingPage';
import TipsBar from './components/TipsBar';
import { PreferencesProvider } from './components/PreferencesContext';
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

function AppContent({
  isAdmin,
  tokenBalance,
  userEmail,
  onLogout,
}: {
  isAdmin: boolean;
  tokenBalance: number | null;
  userEmail: string;
  onLogout: () => void;
}) {
  const [activePage, setActivePage] = useState<Page>(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.has('payment_id')) return 'billing';
    if (params.get('tab') === 'integrations') return 'integrations';
    return 'dashboard';
  });
  const [isMobile, setIsMobile] = useState(() => window.innerWidth < 768);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => window.innerWidth < 768);

  useEffect(() => {
    const handleResize = () => {
      const mobile = window.innerWidth < 768;
      setIsMobile(mobile);
      if (mobile) setSidebarCollapsed(true);
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);
  const [currentJobId, setCurrentJobId] = useState<string | null>(() => {
    return localStorage.getItem('currentJobId');
  });
  const [onboardingDismissed, setOnboardingDismissed] = useState(() => {
    return localStorage.getItem('opal_onboarding_dismissed') === '1';
  });
  const prevJobStatusRef = useRef<string | null>(null);

  // Check if user needs onboarding (no brand profiles)
  const { data: brands } = useQuery({
    queryKey: ['brand-profiles'],
    queryFn: () => api.listBrandProfiles(),
  });

  const { data: subData } = useQuery({
    queryKey: ['subscription'],
    queryFn: () => api.getSubscription(),
  });

  const { data: integrationsData } = useQuery({
    queryKey: ['integrations'],
    queryFn: () => api.listIntegrations(),
  });
  const hasConnectedStores = (integrationsData ?? []).some(i => i.status === 'active');

  const hasSubscription = subData?.subscription?.status === 'active';
  const showOnboarding = brands !== undefined && brands.length === 0 && !onboardingDismissed;

  const handleOnboardingComplete = () => {
    setOnboardingDismissed(true);
    localStorage.setItem('opal_onboarding_dismissed', '1');
  };

  const handleJobCreated = (jobId: string) => {
    setCurrentJobId(jobId);
    localStorage.setItem('currentJobId', jobId);
    setActivePage('monitor');
  };

  // Auto-navigate to results when the active job finishes
  useQuery<Job>({
    queryKey: ['job-nav', currentJobId],
    queryFn: async () => {
      const job = await api.getJob(currentJobId!);
      const prevStatus = prevJobStatusRef.current;
      prevJobStatusRef.current = job.status;
      if (
        prevStatus === 'processing' &&
        (job.status === 'completed' || job.status === 'failed' || job.status === 'partial')
      ) {
        setTimeout(() => setActivePage('results'), 0);
      }
      return job;
    },
    enabled: !!currentJobId && activePage === 'monitor',
    refetchInterval: 3000,
  });

  const handleNavigate = (page: Page) => {
    setActivePage(page);
    if (isMobile) {
      setSidebarCollapsed(true);
    }
  };

  return (
    <div className="app-layout">
      <Sidebar
        activePage={activePage}
        onNavigate={handleNavigate}
        collapsed={sidebarCollapsed}
        onToggleCollapse={() => setSidebarCollapsed(c => !c)}
        isAdmin={isAdmin}
        hasConnectedStores={hasConnectedStores}
        tokenBalance={tokenBalance}
        userEmail={userEmail}
        onLogout={onLogout}
      />

      <main className="app-main">
        {isMobile && (
          <div className="mobile-header">
            <button className="mobile-menu-btn" onClick={() => setSidebarCollapsed(false)}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                <line x1="3" y1="6" x2="21" y2="6" />
                <line x1="3" y1="12" x2="21" y2="12" />
                <line x1="3" y1="18" x2="21" y2="18" />
              </svg>
            </button>
            <span className="mobile-logo">
              <span className="mobile-logo-icon">&#9670;</span> OPAL
            </span>
            <span className="mobile-balance">{tokenBalance ?? '—'}</span>
          </div>
        )}
        <div className="app-content">
          <TipsBar activePage={activePage} />

          {showOnboarding && (
            <OnboardingWizard onComplete={handleOnboardingComplete} />
          )}

          {activePage === 'dashboard' && (
            <Dashboard
              onNavigate={handleNavigate}
              tokenBalance={tokenBalance}
              hasSubscription={hasSubscription}
            />
          )}

          {activePage === 'upload' && (
            <UploadSection onJobCreated={handleJobCreated} />
          )}

          {activePage === 'monitor' && (
            <JobMonitor jobId={currentJobId} onSelectJob={(id) => {
              setCurrentJobId(id);
              localStorage.setItem('currentJobId', id);
            }} />
          )}

          {activePage === 'results' && (
            <ResultsGallery jobId={currentJobId} tokenBalance={tokenBalance} />
          )}

          {activePage === 'brands' && (
            <div className="page-split">
              <BrandProfiles />
              <SceneLibrary />
            </div>
          )}

          {activePage === 'integrations' && <IntegrationsPage />}
          {activePage === 'products' && <ProductsPage onJobCreated={handleJobCreated} />}
          {activePage === 'ab-tests' && <ABTestPage />}
          {activePage === 'benchmarks' && <BenchmarkPage />}
          {activePage === 'billing' && <BillingPage />}
          {activePage === 'settings' && <SettingsPage />}
          {activePage === 'admin' && <AdminPage />}
        </div>
      </main>

      {/* Mobile sidebar overlay */}
      {!sidebarCollapsed && isMobile && (
        <div className="sidebar-overlay" onClick={() => setSidebarCollapsed(true)} />
      )}
    </div>
  );
}

function AuthenticatedApp({ userEmail, onLogout }: { userEmail: string; onLogout: () => void }) {
  const { data: balance } = useQuery({
    queryKey: ['balance'],
    queryFn: () => api.getBalance(),
    refetchInterval: 30000,
  });

  const isAdmin = balance?.is_admin ?? false;
  const tokenBalance = balance?.token_balance ?? null;

  return (
    <PreferencesProvider>
      <AppContent
        isAdmin={isAdmin}
        tokenBalance={tokenBalance}
        userEmail={userEmail}
        onLogout={onLogout}
      />
    </PreferencesProvider>
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
      <div className="app-loading">
        <div className="app-loading-content">
          <span className="app-loading-logo">&#9670;</span>
          <p>Loading...</p>
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
