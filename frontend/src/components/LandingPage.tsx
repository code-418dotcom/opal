import { useState, useEffect } from 'react';
import {
  Eraser, Image, Maximize, ArrowRight, Check, Store, Sparkles,
  FlaskConical, Layers, Palette, ShoppingBag, Zap, TrendingUp,
  Globe, Camera, BarChart3,
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import LanguageSelector from './LanguageSelector';

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
  const { t } = useTranslation();
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

  return (
    <div className="landing">
      {/* Multi-layer opal background */}
      <div className="landing-glow" />
      <div className="landing-glow-2" />
      <div className="landing-sparkles" aria-hidden="true">
        {Array.from({ length: 20 }).map((_, i) => (
          <span key={i} className="sparkle" style={{
            left: `${Math.random() * 100}%`,
            top: `${Math.random() * 100}%`,
            animationDelay: `${Math.random() * 5}s`,
            animationDuration: `${2 + Math.random() * 3}s`,
          }} />
        ))}
      </div>

      {/* Navigation */}
      <nav className="landing-nav">
        <div className="landing-nav-inner">
          <div className="landing-nav-logo">
            <span className="landing-nav-diamond">&#9670;</span>
            OPAL
          </div>
          <div className="landing-nav-links">
            <a href="#how" className="landing-nav-link">{t('landing.nav.howItWorks')}</a>
            <a href="#features" className="landing-nav-link">{t('landing.nav.features')}</a>
            <a href="#pricing" className="landing-nav-link">{t('landing.nav.pricing')}</a>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <div className="landing-lang-selector">
              <LanguageSelector />
            </div>
            <button className="landing-nav-cta" onClick={onGetStarted}>
              {t('common.signIn')}
            </button>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="landing-hero">
        <div className="landing-hero-inner">
          <div className="landing-badge">
            <Sparkles size={12} />
            {t('landing.badge')}
          </div>
          <h1 className="landing-h1">
            {t('landing.heroTitle')}
            <span className="landing-h1-accent">{t('landing.heroAccent')}</span>
          </h1>
          <p className="landing-hero-sub" dangerouslySetInnerHTML={{ __html: t('landing.heroSub') }} />
          <div className="landing-hero-actions">
            <button className="landing-btn-primary" onClick={onGetStarted}>
              {t('landing.tryFree')}
              <ArrowRight size={16} />
            </button>
            <a href="#how" className="landing-btn-ghost">
              {t('landing.seeHow')}
            </a>
          </div>
          <p className="landing-hero-note">{t('landing.heroNote')}</p>

          {/* Store logos strip */}
          <div className="landing-stores-strip">
            <span className="landing-stores-label">{t('landing.worksWithLabel')}</span>
            <div className="landing-stores-logos">
              <span className="landing-store-logo"><ShoppingBag size={18} /> Shopify</span>
              <span className="landing-store-logo"><Globe size={18} /> WooCommerce</span>
              <span className="landing-store-logo"><Store size={18} /> Etsy</span>
            </div>
          </div>
        </div>
      </section>

      {/* Pain points — webshop specific */}
      <section className="landing-pain">
        <div className="landing-pain-inner">
          <h2 className="landing-h2">{t('landing.painTitle')}</h2>
          <div className="landing-pain-grid">
            <div className="landing-pain-card">
              <p>&ldquo;{t('landing.pain1')}&rdquo;</p>
            </div>
            <div className="landing-pain-card">
              <p>&ldquo;{t('landing.pain2')}&rdquo;</p>
            </div>
            <div className="landing-pain-card">
              <p>&ldquo;{t('landing.pain3')}&rdquo;</p>
            </div>
          </div>
          <p className="landing-pain-cta">
            {t('landing.painCta')}
          </p>
        </div>
      </section>

      {/* How it works */}
      <section className="landing-pipeline" id="how">
        <div className="landing-section-inner">
          <div className="landing-section-header">
            <h2 className="landing-h2">{t('landing.howTitle')}</h2>
            <p className="landing-section-sub">
              {t('landing.howSub')}
            </p>
          </div>
          <div className="landing-pipeline-inner">
            <div className="landing-pipeline-step">
              <div className="landing-pipeline-num">1</div>
              <div className="landing-pipeline-detail">
                <div className="landing-pipeline-label">{t('landing.step1Label')}</div>
                <div className="landing-pipeline-desc">{t('landing.step1Desc')}</div>
              </div>
            </div>
            <div className="landing-pipeline-arrow">&#8594;</div>
            <div className="landing-pipeline-step">
              <div className="landing-pipeline-num">2</div>
              <div className="landing-pipeline-detail">
                <div className="landing-pipeline-label">{t('landing.step2Label')}</div>
                <div className="landing-pipeline-desc">{t('landing.step2Desc')}</div>
              </div>
            </div>
            <div className="landing-pipeline-arrow">&#8594;</div>
            <div className="landing-pipeline-step">
              <div className="landing-pipeline-num">3</div>
              <div className="landing-pipeline-detail">
                <div className="landing-pipeline-label">{t('landing.step3Label')}</div>
                <div className="landing-pipeline-desc">{t('landing.step3Desc')}</div>
              </div>
            </div>
            <div className="landing-pipeline-arrow">&#8594;</div>
            <div className="landing-pipeline-step">
              <div className="landing-pipeline-num">4</div>
              <div className="landing-pipeline-detail">
                <div className="landing-pipeline-label">{t('landing.step4Label')}</div>
                <div className="landing-pipeline-desc">{t('landing.step4Desc')}</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Core features — expanded with new capabilities */}
      <section className="landing-features" id="features">
        <div className="landing-section-inner">
          <div className="landing-section-header">
            <div className="landing-badge">
              <Sparkles size={12} />
              {t('landing.featuresBadge')}
            </div>
            <h2 className="landing-h2">{t('landing.featuresTitle')}</h2>
            <p className="landing-section-sub">
              {t('landing.featuresSub')}
            </p>
          </div>
          <div className="landing-features-grid landing-features-grid-3">
            <div className="landing-feature-card">
              <div className="landing-feature-icon"><Eraser size={22} /></div>
              <h3>{t('landing.feature1Title')}</h3>
              <p>{t('landing.feature1Desc')}</p>
            </div>
            <div className="landing-feature-card">
              <div className="landing-feature-icon"><Image size={22} /></div>
              <h3>{t('landing.feature2Title')}</h3>
              <p>{t('landing.feature2Desc')}</p>
            </div>
            <div className="landing-feature-card">
              <div className="landing-feature-icon"><Maximize size={22} /></div>
              <h3>{t('landing.feature3Title')}</h3>
              <p>{t('landing.feature3Desc')}</p>
            </div>
            <div className="landing-feature-card">
              <div className="landing-feature-icon"><Layers size={22} /></div>
              <h3>{t('landing.feature5Title')}</h3>
              <p>{t('landing.feature5Desc')}</p>
            </div>
            <div className="landing-feature-card">
              <div className="landing-feature-icon"><FlaskConical size={22} /></div>
              <h3>{t('landing.feature6Title')}</h3>
              <p>{t('landing.feature6Desc')}</p>
            </div>
            <div className="landing-feature-card">
              <div className="landing-feature-icon"><Palette size={22} /></div>
              <h3>{t('landing.feature7Title')}</h3>
              <p>{t('landing.feature7Desc')}</p>
            </div>
          </div>
        </div>
      </section>

      {/* Store integration spotlight */}
      <section className="landing-integration-spotlight">
        <div className="landing-section-inner">
          <div className="landing-spotlight-content">
            <div className="landing-spotlight-text">
              <div className="landing-badge"><Store size={12} /> {t('landing.integrationBadge')}</div>
              <h2 className="landing-h2">{t('landing.integrationTitle')}</h2>
              <p>{t('landing.integrationDesc')}</p>
              <ul className="landing-spotlight-list">
                <li><Check size={16} /> {t('landing.integrationPoint1')}</li>
                <li><Check size={16} /> {t('landing.integrationPoint2')}</li>
                <li><Check size={16} /> {t('landing.integrationPoint3')}</li>
                <li><Check size={16} /> {t('landing.integrationPoint4')}</li>
              </ul>
            </div>
            <div className="landing-spotlight-visual">
              <div className="landing-spotlight-card">
                <div className="landing-spotlight-card-header">
                  <ShoppingBag size={16} /> {t('landing.integrationCardTitle')}
                </div>
                <div className="landing-spotlight-card-body">
                  <div className="landing-spotlight-stat">
                    <Zap size={14} />
                    <span>{t('landing.integrationStat1')}</span>
                  </div>
                  <div className="landing-spotlight-stat">
                    <TrendingUp size={14} />
                    <span>{t('landing.integrationStat2')}</span>
                  </div>
                  <div className="landing-spotlight-stat">
                    <Camera size={14} />
                    <span>{t('landing.integrationStat3')}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* A/B Testing highlight */}
      <section className="landing-ab-highlight">
        <div className="landing-section-inner">
          <div className="landing-section-header">
            <div className="landing-badge"><FlaskConical size={12} /> {t('landing.abBadge')}</div>
            <h2 className="landing-h2">{t('landing.abTitle')}</h2>
            <p className="landing-section-sub">{t('landing.abSub')}</p>
          </div>
          <div className="landing-ab-steps">
            <div className="landing-ab-step">
              <div className="landing-ab-step-num">1</div>
              <h4>{t('landing.abStep1Title')}</h4>
              <p>{t('landing.abStep1Desc')}</p>
            </div>
            <div className="landing-ab-step">
              <div className="landing-ab-step-num">2</div>
              <h4>{t('landing.abStep2Title')}</h4>
              <p>{t('landing.abStep2Desc')}</p>
            </div>
            <div className="landing-ab-step">
              <div className="landing-ab-step-num">3</div>
              <h4>{t('landing.abStep3Title')}</h4>
              <p>{t('landing.abStep3Desc')}</p>
            </div>
          </div>
        </div>
      </section>

      {/* Brand consistency callout */}
      <section className="landing-brand-callout">
        <div className="landing-brand-inner">
          <div className="landing-brand-text">
            <h2 className="landing-h2">{t('landing.brandTitle')}</h2>
            <p>{t('landing.brandDesc')}</p>
            <button className="landing-btn-primary" onClick={onGetStarted}>
              {t('landing.brandCta')}
              <ArrowRight size={16} />
            </button>
          </div>
        </div>
      </section>

      {/* Social proof / numbers */}
      <section className="landing-proof">
        <div className="landing-proof-inner">
          <div className="landing-proof-item">
            <BarChart3 size={20} />
            <span className="landing-proof-stat">{t('landing.proofStat1')}</span>
            <span className="landing-proof-label">{t('landing.proofLabel1')}</span>
          </div>
          <div className="landing-proof-item">
            <Zap size={20} />
            <span className="landing-proof-stat">{t('landing.proofStat2')}</span>
            <span className="landing-proof-label">{t('landing.proofLabel2')}</span>
          </div>
          <div className="landing-proof-item">
            <Store size={20} />
            <span className="landing-proof-stat">{t('landing.proofStat3')}</span>
            <span className="landing-proof-label">{t('landing.proofLabel3')}</span>
          </div>
        </div>
      </section>

      {/* Pricing */}
      {packages.length > 0 && (
        <section className="landing-pricing" id="pricing">
          <div className="landing-section-inner">
            <div className="landing-section-header">
              <div className="landing-badge">
                <Sparkles size={12} />
                {t('landing.pricingBadge')}
              </div>
              <h2 className="landing-h2">{t('landing.pricingTitle')}</h2>
              <p className="landing-section-sub">
                {t('landing.pricingSub')}
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
                    {isPopular && <div className="landing-price-badge">{t('landing.mostPopular')}</div>}
                    <div className="landing-price-name">{pkg.name}</div>
                    <div className="landing-price-amount">
                      {formatPrice(pkg.price_cents, pkg.currency)}
                    </div>
                    <div className="landing-price-tokens">{pkg.tokens} {t('common.tokens')}</div>
                    <div className="landing-price-per">
                      {formatPrice(Math.round(pricePerToken * 100), pkg.currency)} {t('landing.perToken')}
                    </div>
                    <ul className="landing-price-features">
                      <li><Check size={14} /> {t('landing.priceFeature1')}</li>
                      <li><Check size={14} /> {t('landing.priceFeature2')}</li>
                      <li><Check size={14} /> {t('landing.priceFeature3')}</li>
                      {i >= 1 && <li><Check size={14} /> {t('landing.priceFeature4')}</li>}
                      {i >= 2 && <li><Check size={14} /> {t('landing.priceFeature5')}</li>}
                    </ul>
                    <button
                      className={`landing-price-btn ${isPopular ? 'landing-price-btn-primary' : ''}`}
                      onClick={onGetStarted}
                    >
                      {t('landing.getStarted')}
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
          <h2 className="landing-h2">{t('landing.ctaTitle')} <span className="landing-h1-accent">{t('landing.ctaAccent')}</span></h2>
          <p className="landing-section-sub">
            {t('landing.ctaSub')}
          </p>
          <button className="landing-btn-primary landing-btn-lg" onClick={onGetStarted}>
            {t('landing.ctaBtn')}
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
            {t('landing.footerTagline')}
          </div>
        </div>
      </footer>
    </div>
  );
}
