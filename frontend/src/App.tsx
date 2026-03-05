import { useState, useEffect, useRef, useCallback } from 'react';
import { QueryClient, QueryClientProvider, useQuery } from '@tanstack/react-query';
import { Upload, Activity, Image as ImageIcon, Palette, BookImage, CreditCard, LogOut, Coins } from 'lucide-react';
import UploadSection from './components/UploadSection';
import JobMonitor from './components/JobMonitor';
import ResultsGallery from './components/ResultsGallery';
import BrandProfiles from './components/BrandProfiles';
import SceneLibrary from './components/SceneLibrary';
import BillingPage from './components/BillingPage';
import LoginPage from './components/LoginPage';
import { api } from './api';
import { initializeMsal, isAuthConfigured, getAccount, getAccessToken, logout } from './auth';
import './App.css';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

type Tab = 'upload' | 'monitor' | 'results' | 'brands' | 'library' | 'billing';

function AppContent() {
  const [activeTab, setActiveTab] = useState<Tab>('upload');
  const [currentJobId, setCurrentJobId] = useState<string | null>(() => {
    return localStorage.getItem('currentJobId');
  });
  const prevJobStatusRef = useRef<string | null>(null);

  const handleJobCreated = (jobId: string) => {
    setCurrentJobId(jobId);
    localStorage.setItem('currentJobId', jobId);
    setActiveTab('monitor');
  };

  const tabs = [
    { id: 'upload' as Tab, label: 'Upload', icon: Upload },
    { id: 'monitor' as Tab, label: 'Monitor', icon: Activity },
    { id: 'results' as Tab, label: 'Results', icon: ImageIcon },
    { id: 'brands' as Tab, label: 'Brands', icon: Palette },
    { id: 'library' as Tab, label: 'Library', icon: BookImage },
    { id: 'billing' as Tab, label: 'Billing', icon: CreditCard },
  ];

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
              <span className="logo-subtitle">AI Image Processing</span>
            </h1>
            <div className="header-info">
              <span className="api-status">
                <span className={`status-dot ${isHealthy ? '' : 'status-dot-error'}`}></span>
                {isHealthy ? 'Connected' : 'Disconnected'}
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
          {activeTab === 'billing' && <BillingPage />}
        </div>
      </main>

      <footer className="footer">
        <div className="container">
          <p>OPAL Platform v0.5 | AI-Powered Image Processing</p>
        </div>
      </footer>
    </div>
  );
}

function AuthenticatedApp({ userEmail, onLogout }: { userEmail: string; onLogout: () => void }) {
  const { data: balance } = useQuery({
    queryKey: ['balance'],
    queryFn: () => api.getBalance(),
    refetchInterval: 30000,
  });

  return (
    <>
      <div className="auth-bar">
        <div className="container">
          <div className="auth-bar-content">
            <span className="auth-user-email">{userEmail}</span>
            {balance && (
              <span className="auth-token-balance">
                <Coins size={14} />
                {balance.token_balance} tokens
              </span>
            )}
            <button className="auth-logout-btn" onClick={onLogout}>
              <LogOut size={14} />
              Sign out
            </button>
          </div>
        </div>
      </div>
      <AppContent />
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
        <LoginPage onLoginSuccess={handleLoginSuccess} />
      )}
    </QueryClientProvider>
  );
}

export default App;
