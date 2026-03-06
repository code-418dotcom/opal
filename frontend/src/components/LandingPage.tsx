import { useState, useEffect } from 'react';
import { Eraser, Image, Maximize, ArrowRight, Check, Store, Sparkles } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import LanguageSelector from './LanguageSelector';

// Stock images from Unsplash (free license)
const HERO_IMG = 'https://images.unsplash.com/photo-1556228578-0d85b1a4d571?w=860&h=480&fit=crop&q=80';
const BEFORE_IMG = 'https://images.unsplash.com/photo-1523293182086-7651a899d37f?w=440&h=260&fit=crop&q=80';
const AFTER_IMG = 'https://images.unsplash.com/photo-1612817288484-6f916006741a?w=440&h=260&fit=crop&q=80';

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

  const features = [
    {
      icon: Eraser,
      title: t('landing.feature1Title'),
      description: t('landing.feature1Desc'),
    },
    {
      icon: Image,
      title: t('landing.feature2Title'),
      description: t('landing.feature2Desc'),
    },
    {
      icon: Maximize,
      title: t('landing.feature3Title'),
      description: t('landing.feature3Desc'),
    },
    {
      icon: Store,
      title: t('landing.feature4Title'),
      description: t('landing.feature4Desc'),
    },
  ];

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

          {/* Hero product image with opal frame */}
          <div className="landing-hero-image">
            <div className="landing-hero-image-glow" />
            <img
              src={HERO_IMG}
              alt={t('landing.heroImgAlt')}
              loading="eager"
            />
          </div>
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

      {/* Before / After showcase */}
      <section className="landing-showcase">
        <div className="landing-showcase-inner">
          <div className="landing-section-header">
            <h2 className="landing-h2">{t('landing.showcaseTitle')}</h2>
            <p className="landing-section-sub">
              {t('landing.showcaseSub')}
            </p>
          </div>
          <div className="landing-showcase-grid">
            <div className="landing-showcase-card">
              <img src={BEFORE_IMG} alt={t('landing.beforeAlt')} loading="lazy" />
              <div className="landing-showcase-label">{t('landing.beforeLabel')}</div>
            </div>
            <div className="landing-showcase-card landing-showcase-after">
              <img src={AFTER_IMG} alt={t('landing.afterAlt')} loading="lazy" />
              <div className="landing-showcase-label">{t('landing.afterLabel')}</div>
            </div>
          </div>
        </div>
      </section>

      {/* Pain point bridge */}
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

      {/* Features */}
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
