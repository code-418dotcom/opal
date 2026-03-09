import { useState, useEffect } from 'react';
import {
  Eraser, Image, Maximize, ArrowRight, Check, Store, Sparkles,
  FlaskConical, Layers, Palette, ShoppingBag, Zap, TrendingUp,
  Camera, BarChart3,
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
              <span className="landing-store-logo">
                <svg viewBox="0 0 109.5 124.5" width="22" height="25" fill="currentColor" aria-label="Shopify">
                  <path d="M95.6 28.2c-.1-.6-.6-1-1.1-1-.5 0-10.3-.8-10.3-.8s-6.8-6.8-7.5-7.5c-.7-.7-2.1-.5-2.6-.3 0 0-1.4.4-3.7 1.1-2.2-6.3-6-12.1-12.8-12.1h-.6C55.2 5.1 52.9 4 51 4c-15.8.1-23.4 19.7-25.7 29.8-6.1 1.9-10.4 3.2-10.9 3.4-3.4 1.1-3.5 1.2-3.9 4.4C10.2 44 0 122.8 0 122.8l76.2 13.1 38.8-9.5S95.7 28.8 95.6 28.2zM67.3 21.7l-5 1.5c0-3.5-.5-8.4-2-12.5 5 1 7.4 6.6 7 11zM57.1 24.8l-10.7 3.3c1-3.9 3-7.8 6.8-10.3 1.5-1 3.5-2 4.8-2.1-.6 2.2-1 5.6-.9 9.1zM51.1 7.6c1.6 0 2.9.5 4 1.5-6.4 3-13.3 11-16.2 26.7l-8.5 2.6C33.2 27.7 39 7.7 51.1 7.6z"/>
                  <path d="M94.5 27.2c-.5 0-10.3-.8-10.3-.8s-6.8-6.8-7.5-7.5c-.3-.3-.6-.4-1-.4l-5.6 114.3 38.8-9.5S95.7 28.8 95.6 28.2c-.1-.7-.6-1-1.1-1z" opacity=".6"/>
                </svg>
                Shopify
              </span>
              <span className="landing-store-logo">
                <svg viewBox="0 0 2000 2000" width="25" height="25" fill="currentColor" aria-label="WooCommerce">
                  <path d="M183.2 233.6C81.8 233.6 0 315.4 0 416.8v646.4c0 101.4 81.8 183.2 183.2 183.2h1078.7l334.8 320.3V1246.4h220.1c101.4 0 183.2-81.8 183.2-183.2V416.8c0-101.4-81.8-183.2-183.2-183.2H183.2zm243.3 256.7c37.4 0 68.9 14.3 94.6 42.8 25.7 28.6 38.5 67.5 38.5 116.8 0 116.8-60.5 265.3-181.4 445.5-16.3 23.7-38.2 43.3-65.6 58.8-27.4 15.5-54 23.3-79.7 23.3-13.1 0-24.6-4.2-34.4-12.5-9.8-8.3-16.5-19.6-20.2-33.8L117 835.7c-2.4-8.3-1.8-16.1 1.8-23.3 3.6-7.1 9.5-11.9 17.9-14.3 8.3-2.4 16.1-1.5 23.3 2.7 7.1 4.2 11.9 10.4 14.3 18.8l58.3 253.1c1.2 7.1 4.2 10.7 8.9 10.7 3.6 0 8.3-3.6 14.3-10.7 89.2-133.2 133.8-247.2 133.8-342 0-27.4-4.5-49.3-13.4-65.6-8.9-16.3-17.9-24.4-26.8-24.4-7.1 0-14.3 4.2-21.4 12.5-7.1 8.3-12.5 19-16.1 32-3.6 8.3-9.2 14.3-17 17.9-7.7 3.6-15.8 3.6-24.1 0-8.3-3.6-14-9.2-17-17-3-7.7-3-15.8 0-24.1 9.5-29.7 25.4-53.4 47.7-71.3 22.3-17.9 47.4-26.8 75.3-26.8zm471.1 0c37.4 0 68.9 14.3 94.6 42.8 25.7 28.6 38.5 67.5 38.5 116.8 0 116.8-60.5 265.3-181.4 445.5-16.3 23.7-38.2 43.3-65.6 58.8-27.4 15.5-54 23.3-79.7 23.3-13.1 0-24.6-4.2-34.4-12.5-9.8-8.3-16.5-19.6-20.2-33.8l-60.7-274.6c-2.4-8.3-1.8-16.1 1.8-23.3 3.6-7.1 9.5-11.9 17.9-14.3 8.3-2.4 16.1-1.5 23.3 2.7 7.1 4.2 11.9 10.4 14.3 18.8l58.3 253.1c1.2 7.1 4.2 10.7 8.9 10.7 3.6 0 8.3-3.6 14.3-10.7 89.2-133.2 133.8-247.2 133.8-342 0-27.4-4.5-49.3-13.4-65.6-8.9-16.3-17.9-24.4-26.8-24.4-7.1 0-14.3 4.2-21.4 12.5-7.1 8.3-12.5 19-16.1 32-3.6 8.3-9.2 14.3-17 17.9-7.7 3.6-15.8 3.6-24.1 0-8.3-3.6-14-9.2-17-17-3-7.7-3-15.8 0-24.1 9.5-29.7 25.4-53.4 47.7-71.3 22.3-17.9 47.3-26.8 75.2-26.8zm535.2 0c37.4 0 66.9 13.1 88.4 39.3 21.4 26.2 32.1 61.5 32.1 105.9 0 57.1-12.8 117.1-38.5 180-25.7 62.9-62.5 117.1-110.4 162.7-47.9 45.5-97.5 68.3-148.8 68.3-34.5 0-62.2-11.9-83-35.7-20.8-23.8-31.2-56.3-31.2-97.5 0-58.3 12.8-118.6 38.5-180.9 25.7-62.3 62.5-116.2 110.4-161.6 47.9-44.3 97-67.1 148.3-67.1-1.8 5.6-5.8 16.6-5.8 16.6h.1zm-21.4 53.5c-34.5 0-67.8 26.5-100 79.7-32.1 53.1-48.2 110.7-48.2 172.7 0 26.2 5.1 46.7 15.2 61.6 10.1 14.9 22.6 22.3 37.5 22.3 34.5 0 67.8-26.5 100-79.7 32.1-53.1 48.2-110.7 48.2-172.7 0-26.2-5.1-46.7-15.2-61.6-10.1-14.9-22.6-22.3-37.5-22.3z"/>
                </svg>
                WooCommerce
              </span>
              <span className="landing-store-logo">
                <svg viewBox="0 0 338.6 338.6" width="22" height="22" fill="currentColor" aria-label="Etsy">
                  <path d="M169.3 0C75.8 0 0 75.8 0 169.3s75.8 169.3 169.3 169.3 169.3-75.8 169.3-169.3S262.8 0 169.3 0zm57.5 249.4c-7.2 3-12.8 4.5-22 5.5-9 1-63 1-63 1l-1.5-48.5h55.5s2-18.5 2.5-27l-57.5-.5-.5-41h55l4 3.5 10 26h16l-3-56H101v1.5c0 0 6.5 1 11.5 3 5 2 5.5 5.5 5.5 5.5s1 5.5 1 14v125.5c0 8.5-1 13-1 13s-.5 3-5.5 5c-5 2-11.5 3-11.5 3v2h121l12.5-46-7.7 10.5z"/>
                </svg>
                Etsy
              </span>
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
