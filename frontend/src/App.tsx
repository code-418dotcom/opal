import { useState, useEffect, useRef } from 'react';
import { QueryClient, QueryClientProvider, useQuery } from '@tanstack/react-query';
import { Upload, Activity, Image as ImageIcon } from 'lucide-react';
import UploadSection from './components/UploadSection';
import JobMonitor from './components/JobMonitor';
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

type Tab = 'upload' | 'monitor' | 'results';

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
  ];

  const { data: health } = useQuery({
    queryKey: ['health'],
    queryFn: () => api.checkHealth(),
    refetchInterval: 30000,
  });

  // Poll current job for auto-navigation
  const { data: currentJob } = useQuery({
    queryKey: ['job-nav', currentJobId],
    queryFn: () => api.getJob(currentJobId!),
    enabled: !!currentJobId && activeTab === 'monitor',
    refetchInterval: 3000,
  });

  // Auto-navigate to Results when job reaches terminal status
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
        </div>
      </main>

      <footer className="footer">
        <div className="container">
          <p>OPAL Platform v0.3 | AI-Powered Image Processing</p>
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
