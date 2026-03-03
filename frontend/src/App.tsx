import { useState } from 'react';
import { QueryClient, QueryClientProvider, useQuery } from '@tanstack/react-query';
import { Upload, Activity, Bug, Image as ImageIcon } from 'lucide-react';
import UploadSection from './components/UploadSection';
import JobMonitor from './components/JobMonitor';
import DebugConsole from './components/DebugConsole';
import ResultsGallery from './components/ResultsGallery';
import { api } from './api';
import './App.css';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

type Tab = 'upload' | 'monitor' | 'debug' | 'results';

function AppContent() {
  const [activeTab, setActiveTab] = useState<Tab>('upload');
  const [currentJobId, setCurrentJobId] = useState<string | null>(() => {
    // Restore job ID from localStorage
    return localStorage.getItem('currentJobId');
  });

  const handleJobCreated = (jobId: string) => {
    setCurrentJobId(jobId);
    // Persist to localStorage
    localStorage.setItem('currentJobId', jobId);
  };

  const tabs = [
    { id: 'upload' as Tab, label: 'Upload', icon: Upload },
    { id: 'monitor' as Tab, label: 'Monitor', icon: Activity },
    { id: 'debug' as Tab, label: 'Debug', icon: Bug },
    { id: 'results' as Tab, label: 'Results', icon: ImageIcon },
  ];

  const { data: health } = useQuery({
    queryKey: ['health'],
    queryFn: () => api.checkHealth(),
    refetchInterval: 30000,
  });

  const isHealthy = health?.status === 'ok';

  return (
      <div className="app">
        <header className="header">
          <div className="container">
            <div className="header-content">
              <h1 className="logo">
                <span className="logo-icon">⚡</span>
                OPAL
                <span className="logo-subtitle">AI Image Processing</span>
              </h1>
              <div className="header-info">
                <span className="api-status">
                  <span className={`status-dot ${isHealthy ? '' : 'status-dot-error'}`}></span>
                  API: {import.meta.env.VITE_API_URL || 'http://localhost:8080'}
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
            {activeTab === 'debug' && <DebugConsole />}
            {activeTab === 'results' && (
              <ResultsGallery jobId={currentJobId} />
            )}
          </div>
        </main>

        <footer className="footer">
          <div className="container">
            <p>OPAL Platform v0.2 | AI-Powered Image Processing</p>
          </div>
        </footer>
      </div>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AppContent />
    </QueryClientProvider>
  );
}

export default App;
