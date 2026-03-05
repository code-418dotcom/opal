import { useState, useEffect } from 'react';
import { Sparkles, Layers, ZoomIn, ShoppingBag, ArrowRight, Check } from 'lucide-react';

interface TokenPackage {
  id: string;
  name: string;
  tokens: number;
  price_cents: number;
  currency: string;
}

interface LandingPageProps {
  onGetStarted: () => void;
}

const API_URL = import.meta.env.VITE_API_URL as string;

export default function LandingPage({ onGetStarted }: LandingPageProps) {
  const [packages, setPackages] = useState<TokenPackage[]>([]);

  useEffect(() => {
    if (!API_URL) return;
    fetch(`${API_URL}/v1/billing/packages`)
      .then(r => r.json())
      .then(data => setPackages(data.packages || []))
      .catch(() => {});
  }, []);

  const formatPrice = (cents: number, currency: string) => {
    const amount = cents / 100;
    return new Intl.NumberFormat('en-EU', {
      style: 'currency',
      currency: currency.toUpperCase(),
      minimumFractionDigits: 2,
    }).format(amount);
  };

  const features = [
    {
      icon: Sparkles,
      title: 'Background Removal',
      description: 'AI-powered background removal that handles complex edges, transparency, and fine details like hair and jewelry.',
    },
    {
      icon: Layers,
      title: 'Scene Generation',
      description: 'Generate photorealistic product scenes with AI. Match your brand aesthetic with custom prompts and style presets.',
    },
    {
      icon: ZoomIn,
      title: 'Smart Upscaling',
      description: 'Enhance resolution up to 4x without artifacts. Real-ESRGAN powered upscaling preserves texture and sharpness.',
    },
    {
      icon: ShoppingBag,
      title: 'Shopify Integration',
      description: 'Connect your store, select products, process images, and push results back — all without leaving the platform.',
    },
  ];

  return (
    <div className="landing">
      {/* Ambient background */}
      <div className="landing-glow" />

      {/* Navigation */}
      <nav className="landing-nav">
        <div className="landing-nav-inner">
          <div className="landing-nav-logo">
            <span className="landing-nav-diamond">&#9670;</span>
            OPAL
          </div>
          <button className="landing-nav-cta" onClick={onGetStarted}>
            Get started
            <ArrowRight size={15} />
          </button>
        </div>
      </nav>

      {/* Hero */}
      <section className="landing-hero">
        <div className="landing-hero-inner">
          <div className="landing-badge">AI-Powered Image Processing</div>
          <h1 className="landing-h1">
            Product photos that
            <span className="landing-h1-accent"> sell</span>
          </h1>
          <p className="landing-hero-sub">
            Transform raw product images into professional e-commerce photography.
            Background removal, AI-generated scenes, and intelligent upscaling — processed
            in seconds, not hours.
          </p>
          <div className="landing-hero-actions">
            <button className="landing-btn-primary" onClick={onGetStarted}>
              Start for free
              <ArrowRight size={16} />
            </button>
            <a href="#features" className="landing-btn-ghost">
              See how it works
            </a>
          </div>
          <div className="landing-hero-proof">
            <div className="landing-proof-avatars">
              <div className="landing-proof-dot" style={{ background: '#6366f1' }} />
              <div className="landing-proof-dot" style={{ background: '#8b5cf6' }} />
              <div className="landing-proof-dot" style={{ background: '#a78bfa' }} />
            </div>
            <span>Trusted by e-commerce sellers across Europe</span>
          </div>
        </div>
      </section>

      {/* Pipeline visual */}
      <section className="landing-pipeline">
        <div className="landing-pipeline-inner">
          <div className="landing-pipeline-step">
            <div className="landing-pipeline-num">01</div>
            <div className="landing-pipeline-label">Upload</div>
          </div>
          <div className="landing-pipeline-arrow">&#8594;</div>
          <div className="landing-pipeline-step">
            <div className="landing-pipeline-num">02</div>
            <div className="landing-pipeline-label">Remove BG</div>
          </div>
          <div className="landing-pipeline-arrow">&#8594;</div>
          <div className="landing-pipeline-step">
            <div className="landing-pipeline-num">03</div>
            <div className="landing-pipeline-label">Generate Scene</div>
          </div>
          <div className="landing-pipeline-arrow">&#8594;</div>
          <div className="landing-pipeline-step">
            <div className="landing-pipeline-num">04</div>
            <div className="landing-pipeline-label">Upscale & Export</div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="landing-features" id="features">
        <div className="landing-section-inner">
          <div className="landing-section-header">
            <div className="landing-badge">Features</div>
            <h2 className="landing-h2">Everything your product images need</h2>
            <p className="landing-section-sub">
              A complete pipeline from raw photo to store-ready imagery.
              Each step is optional — use what you need.
            </p>
          </div>
          <div className="landing-features-grid">
            {features.map((f, i) => (
              <div key={i} className="landing-feature-card">
                <div className="landing-feature-icon">
                  <f.icon size={22} />
                </div>
                <h3>{f.title}</h3>
                <p>{f.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing */}
      {packages.length > 0 && (
        <section className="landing-pricing" id="pricing">
          <div className="landing-section-inner">
            <div className="landing-section-header">
              <div className="landing-badge">Pricing</div>
              <h2 className="landing-h2">Simple, token-based pricing</h2>
              <p className="landing-section-sub">
                Buy tokens, use them when you need them. No subscriptions, no monthly commitments.
                Each image processing step costs 1 token.
              </p>
            </div>
            <div className="landing-pricing-grid">
              {packages.map((pkg, i) => {
                const isPopular = i === 1;
                const pricePerToken = pkg.price_cents / pkg.tokens / 100;
                return (
                  <div
                    key={pkg.id}
                    className={`landing-price-card ${isPopular ? 'landing-price-popular' : ''}`}
                  >
                    {isPopular && <div className="landing-price-badge">Most popular</div>}
                    <div className="landing-price-name">{pkg.name}</div>
                    <div className="landing-price-amount">
                      {formatPrice(pkg.price_cents, pkg.currency)}
                    </div>
                    <div className="landing-price-tokens">{pkg.tokens} tokens</div>
                    <div className="landing-price-per">
                      {formatPrice(Math.round(pricePerToken * 100), pkg.currency)} per token
                    </div>
                    <ul className="landing-price-features">
                      <li><Check size={14} /> All processing steps included</li>
                      <li><Check size={14} /> Tokens never expire</li>
                      <li><Check size={14} /> Shopify integration</li>
                      {i >= 1 && <li><Check size={14} /> Brand profiles &amp; scene templates</li>}
                      {i >= 2 && <li><Check size={14} /> Priority processing</li>}
                    </ul>
                    <button
                      className={`landing-price-btn ${isPopular ? 'landing-price-btn-primary' : ''}`}
                      onClick={onGetStarted}
                    >
                      Get started
                    </button>
                  </div>
                );
              })}
            </div>
          </div>
        </section>
      )}

      {/* Final CTA */}
      <section className="landing-cta">
        <div className="landing-cta-inner">
          <h2 className="landing-h2">Ready to upgrade your product images?</h2>
          <p className="landing-section-sub">
            Sign up in seconds. No credit card required to get started.
          </p>
          <button className="landing-btn-primary landing-btn-lg" onClick={onGetStarted}>
            Create your free account
            <ArrowRight size={18} />
          </button>
        </div>
      </section>

      {/* Footer */}
      <footer className="landing-footer">
        <div className="landing-footer-inner">
          <div className="landing-footer-brand">
            <span className="landing-nav-diamond">&#9670;</span>
            OPAL
          </div>
          <div className="landing-footer-text">
            AI-Powered Product Image Processing for E-commerce
          </div>
        </div>
      </footer>
    </div>
  );
}
