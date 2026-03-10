import { useState, useRef } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Target, Upload, Loader2, AlertTriangle, CheckCircle2,
  ArrowRight, ChevronDown, BarChart3, Zap,
} from 'lucide-react';
import { api } from '../api';
import type { ImageBenchmark, ImageBenchmarkScores, BenchmarkSuggestion, CategoryBenchmark } from '../types';
import HelpTooltip from './HelpTooltip';

type BenchView = 'analyze' | 'result' | 'history';

const CATEGORIES = [
  'general', 'fashion', 'electronics', 'jewelry',
  'home & garden', 'beauty', 'food & beverage', 'toys & games', 'sports & outdoors',
];

const METRIC_LABELS: Record<string, string> = {
  resolution: 'Resolution',
  background: 'Background',
  lighting: 'Lighting',
  composition: 'Composition',
  text_penalty: 'No Text/Watermarks',
  image_count: 'Image Count',
};

const PRIORITY_COLORS: Record<string, string> = {
  high: '#ef4444',
  medium: '#f59e0b',
  low: '#6b7280',
};

function ScoreBar({ label, score, avg }: { label: string; score: number; avg?: number }) {
  const color = score >= 80 ? '#22c55e' : score >= 60 ? '#f59e0b' : '#ef4444';
  return (
    <div className="bench-score-row">
      <div className="bench-score-label">{label}</div>
      <div className="bench-score-bar-container">
        <div className="bench-score-bar" style={{ width: `${score}%`, backgroundColor: color }} />
        {avg !== undefined && (
          <div className="bench-score-avg-marker" style={{ left: `${avg}%` }} title={`Category avg: ${avg}`} />
        )}
      </div>
      <div className="bench-score-value">{score}</div>
    </div>
  );
}

function OverallGauge({ score }: { score: number }) {
  const color = score >= 80 ? '#22c55e' : score >= 60 ? '#f59e0b' : '#ef4444';
  const label = score >= 80 ? 'Great' : score >= 60 ? 'Fair' : 'Needs Work';
  return (
    <div className="bench-gauge">
      <div className="bench-gauge-ring" style={{ borderColor: color }}>
        <span className="bench-gauge-score">{score}</span>
      </div>
      <span className="bench-gauge-label" style={{ color }}>{label}</span>
    </div>
  );
}

export default function BenchmarkPage() {
  const queryClient = useQueryClient();
  const fileRef = useRef<HTMLInputElement>(null);
  const [view, setView] = useState<BenchView>('analyze');
  const [error, setError] = useState<string | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [category, setCategory] = useState('general');
  const [imageCount, setImageCount] = useState(1);
  const [currentResult, setCurrentResult] = useState<ImageBenchmark | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  const { data: historyData, isLoading: historyLoading } = useQuery({
    queryKey: ['benchmarks'],
    queryFn: () => api.listBenchmarks(),
    enabled: view === 'history',
  });

  const { data: categoriesData } = useQuery({
    queryKey: ['benchmark-categories'],
    queryFn: () => api.listBenchmarkCategories(),
  });

  const handleFileAnalyze = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setPreviewUrl(URL.createObjectURL(file));
    setAnalyzing(true);
    setError(null);

    try {
      const result = await api.analyzeBenchmarkFile(file, category, imageCount);
      setCurrentResult(result);
      setView('result');
      queryClient.invalidateQueries({ queryKey: ['benchmarks'] });
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Analysis failed');
    } finally {
      setAnalyzing(false);
      if (fileRef.current) fileRef.current.value = '';
    }
  };

  const handleViewResult = (bm: ImageBenchmark) => {
    setCurrentResult(bm);
    setPreviewUrl(null);
    setView('result');
  };

  return (
    <div className="bench-page">
      <div className="bench-header">
        <h2><Target size={20} /> Image Quality Score <HelpTooltip text="Upload any product image to get an instant quality score. See how it compares to your category and get improvement suggestions." /></h2>
        <div className="bench-header-actions">
          {view !== 'analyze' && (
            <button className="btn btn-ghost" onClick={() => { setView('analyze'); setCurrentResult(null); setPreviewUrl(null); }}>
              New Analysis
            </button>
          )}
          <button
            className={`btn ${view === 'history' ? 'btn-primary' : 'btn-ghost'}`}
            onClick={() => setView(view === 'history' ? 'analyze' : 'history')}
          >
            <BarChart3 size={14} /> History
          </button>
        </div>
      </div>

      {error && (
        <div className="bench-error">
          <AlertTriangle size={14} /> {error}
        </div>
      )}

      {/* ── Analyze View ─────────────────────────────── */}
      {view === 'analyze' && (
        <div className="bench-analyze">
          <div className="bench-upload-card">
            <Target size={48} className="bench-upload-icon" />
            <h3>Score Your Product Image</h3>
            <p>Upload a product photo to get a quality score with improvement suggestions.</p>

            <div className="bench-options">
              <div className="bench-option">
                <label>Category</label>
                <select value={category} onChange={(e) => setCategory(e.target.value)}>
                  {CATEGORIES.map(c => (
                    <option key={c} value={c}>{c.charAt(0).toUpperCase() + c.slice(1)}</option>
                  ))}
                </select>
                <ChevronDown size={14} className="bench-select-icon" />
              </div>
              <div className="bench-option">
                <label>Images in listing</label>
                <input
                  type="number"
                  min={1}
                  max={20}
                  value={imageCount}
                  onChange={(e) => setImageCount(parseInt(e.target.value) || 1)}
                />
              </div>
            </div>

            <input
              ref={fileRef}
              type="file"
              accept="image/*"
              onChange={handleFileAnalyze}
              style={{ display: 'none' }}
            />
            <button
              className="btn btn-primary btn-lg"
              onClick={() => fileRef.current?.click()}
              disabled={analyzing}
            >
              {analyzing ? <><Loader2 size={16} className="spin" /> Analyzing...</> : <><Upload size={16} /> Upload & Analyze</>}
            </button>
          </div>

          {/* Category benchmarks reference */}
          {categoriesData?.categories && (
            <div className="bench-categories-ref">
              <h4>Category Averages</h4>
              <div className="bench-cat-grid">
                {categoriesData.categories.map((cat: CategoryBenchmark) => (
                  <div key={cat.id} className="bench-cat-card">
                    <div className="bench-cat-name">{cat.category}</div>
                    <div className="bench-cat-scores">
                      {Object.entries(cat.avg_scores).map(([k, v]) => (
                        <div key={k} className="bench-cat-score">
                          <span>{METRIC_LABELS[k] || k}</span>
                          <span>{v as number}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── Result View ─────────────────────────────── */}
      {view === 'result' && currentResult && (
        <div className="bench-result">
          <div className="bench-result-top">
            {previewUrl && (
              <div className="bench-result-preview">
                <img src={previewUrl} alt="Analyzed product" />
              </div>
            )}
            <div className="bench-result-overview">
              <OverallGauge score={currentResult.overall_score} />
              {currentResult.product_title && (
                <div className="bench-result-title">{currentResult.product_title}</div>
              )}
              <div className="bench-result-category">{currentResult.category}</div>
            </div>
          </div>

          <div className="bench-result-scores">
            <h4>Score Breakdown</h4>
            {Object.entries(currentResult.scores).map(([key, val]) => (
              <ScoreBar
                key={key}
                label={METRIC_LABELS[key] || key}
                score={val}
                avg={currentResult.category_avg?.[key as keyof ImageBenchmarkScores]}
              />
            ))}
            <div className="bench-legend">
              <span className="bench-legend-item"><span className="bench-legend-dot" style={{ background: '#888' }} /> Category Average</span>
            </div>
          </div>

          {currentResult.suggestions.length > 0 && (
            <div className="bench-suggestions">
              <h4><Zap size={16} /> Improvement Suggestions</h4>
              {currentResult.suggestions.map((s: BenchmarkSuggestion, i: number) => (
                <div key={i} className="bench-suggestion" style={{ borderLeftColor: PRIORITY_COLORS[s.priority] }}>
                  <div className="bench-suggestion-header">
                    <span className="bench-suggestion-metric">{METRIC_LABELS[s.metric] || s.metric}</span>
                    <span className="bench-suggestion-priority" style={{ color: PRIORITY_COLORS[s.priority] }}>
                      {s.priority}
                    </span>
                  </div>
                  <p>{s.message}</p>
                  <button className="btn btn-ghost btn-sm">
                    Fix it <ArrowRight size={12} />
                  </button>
                </div>
              ))}
            </div>
          )}

          {currentResult.suggestions.length === 0 && (
            <div className="bench-all-good">
              <CheckCircle2 size={32} />
              <p>Looking good! No major improvements needed.</p>
            </div>
          )}
        </div>
      )}

      {/* ── History View ─────────────────────────────── */}
      {view === 'history' && (
        <div className="bench-history">
          {historyLoading ? (
            <div className="bench-loading"><Loader2 size={24} className="spin" /> Loading history...</div>
          ) : historyData?.benchmarks?.length ? (
            <div className="bench-history-list">
              {historyData.benchmarks.map((bm: ImageBenchmark) => {
                const scoreColor = bm.overall_score >= 80 ? '#22c55e' : bm.overall_score >= 60 ? '#f59e0b' : '#ef4444';
                return (
                  <div key={bm.id} className="bench-history-item" onClick={() => handleViewResult(bm)}>
                    <div className="bench-history-score" style={{ borderColor: scoreColor, color: scoreColor }}>
                      {bm.overall_score}
                    </div>
                    <div className="bench-history-info">
                      <div className="bench-history-title">{bm.product_title || 'Untitled image'}</div>
                      <div className="bench-history-meta">
                        {bm.category} &middot; {new Date(bm.created_at).toLocaleDateString()}
                        {bm.suggestions?.length > 0 && ` \u00b7 ${bm.suggestions.length} suggestion${bm.suggestions.length > 1 ? 's' : ''}`}
                      </div>
                    </div>
                    <ArrowRight size={16} className="bench-history-arrow" />
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="bench-empty">
              <Target size={48} />
              <p>No benchmarks yet. Analyze an image to get started.</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
