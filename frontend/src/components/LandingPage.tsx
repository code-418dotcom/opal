import { useState, useEffect } from 'react';
import { Eraser, Image, Maximize, ArrowRight, Check, Store, Sparkles } from 'lucide-react';

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
      title: 'Clean backgrounds',
      description: 'Drop your product photo in, and we strip away the messy background. Kitchen table, wrinkled bedsheet, whatever — gone. You get a clean cutout, ready for anything.',
    },
    {
      icon: Image,
      title: 'Lifestyle scenes',
      description: 'No studio? No problem. Pick a style and Opal places your product in a realistic setting — marble countertop, wooden table, morning light. Looks like you hired a photographer.',
    },
    {
      icon: Maximize,
      title: 'Sharper images',
      description: 'Blurry phone photo? We make it crisp. Opal sharpens and upscales your images so they look great on any screen, from a phone to a desktop.',
    },
    {
      icon: Store,
      title: 'Works with your store',
      description: 'Connect your Shopify, WooCommerce, or Etsy store. Pull in your product images, polish them, and push them right back. No downloading, no re-uploading.',
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
            <a href="#how" className="landing-nav-link">How it works</a>
            <a href="#features" className="landing-nav-link">Features</a>
            <a href="#pricing" className="landing-nav-link">Pricing</a>
          </div>
          <button className="landing-nav-cta" onClick={onGetStarted}>
            Sign in
          </button>
        </div>
      </nav>

      {/* Hero */}
      <section className="landing-hero">
        <div className="landing-hero-inner">
          <div className="landing-badge">
            <Sparkles size={12} />
            For Shopify, Etsy &amp; WooCommerce sellers
          </div>
          <h1 className="landing-h1">
            Your products deserve
            <span className="landing-h1-accent"> better photos</span>
          </h1>
          <p className="landing-hero-sub">
            You know that feeling when you see a competitor's listing and
            their photos just look <em>professional</em>? That's what Opal does
            for yours. Drop in a photo, get back something you're proud to put
            in your store.
          </p>
          <div className="landing-hero-actions">
            <button className="landing-btn-primary" onClick={onGetStarted}>
              Try it free
              <ArrowRight size={16} />
            </button>
            <a href="#how" className="landing-btn-ghost">
              See how it works
            </a>
          </div>
          <p className="landing-hero-note">No credit card needed. Start with free tokens.</p>

          {/* Hero product image with opal frame */}
          <div className="landing-hero-image">
            <div className="landing-hero-image-glow" />
            <img
              src={HERO_IMG}
              alt="Product photography — skincare bottles styled on a marble surface"
              loading="eager"
            />
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="landing-pipeline" id="how">
        <div className="landing-section-inner">
          <div className="landing-section-header">
            <h2 className="landing-h2">Four steps from meh to beautiful</h2>
            <p className="landing-section-sub">
              The whole thing takes seconds. Seriously.
            </p>
          </div>
          <div className="landing-pipeline-inner">
            <div className="landing-pipeline-step">
              <div className="landing-pipeline-num">1</div>
              <div className="landing-pipeline-detail">
                <div className="landing-pipeline-label">Upload your photo</div>
                <div className="landing-pipeline-desc">Even a phone photo works</div>
              </div>
            </div>
            <div className="landing-pipeline-arrow">&#8594;</div>
            <div className="landing-pipeline-step">
              <div className="landing-pipeline-num">2</div>
              <div className="landing-pipeline-detail">
                <div className="landing-pipeline-label">Remove the background</div>
                <div className="landing-pipeline-desc">Messy kitchen table? Gone</div>
              </div>
            </div>
            <div className="landing-pipeline-arrow">&#8594;</div>
            <div className="landing-pipeline-step">
              <div className="landing-pipeline-num">3</div>
              <div className="landing-pipeline-detail">
                <div className="landing-pipeline-label">Pick a scene</div>
                <div className="landing-pipeline-desc">Marble, wood, studio light</div>
              </div>
            </div>
            <div className="landing-pipeline-arrow">&#8594;</div>
            <div className="landing-pipeline-step">
              <div className="landing-pipeline-num">4</div>
              <div className="landing-pipeline-detail">
                <div className="landing-pipeline-label">Download or push to store</div>
                <div className="landing-pipeline-desc">Listing-ready in seconds</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Before / After showcase */}
      <section className="landing-showcase">
        <div className="landing-showcase-inner">
          <div className="landing-section-header">
            <h2 className="landing-h2">See the difference</h2>
            <p className="landing-section-sub">
              Same product, completely different impression. Opal turns
              everyday photos into images that sell.
            </p>
          </div>
          <div className="landing-showcase-grid">
            <div className="landing-showcase-card">
              <img src={BEFORE_IMG} alt="Before — product on cluttered background" loading="lazy" />
              <div className="landing-showcase-label">Before</div>
            </div>
            <div className="landing-showcase-card landing-showcase-after">
              <img src={AFTER_IMG} alt="After — product styled on clean surface with soft lighting" loading="lazy" />
              <div className="landing-showcase-label">After Opal</div>
            </div>
          </div>
        </div>
      </section>

      {/* Pain point bridge */}
      <section className="landing-pain">
        <div className="landing-pain-inner">
          <h2 className="landing-h2">Sound familiar?</h2>
          <div className="landing-pain-grid">
            <div className="landing-pain-card">
              <p>&ldquo;I spent my whole weekend editing product photos and they still look amateur.&rdquo;</p>
            </div>
            <div className="landing-pain-card">
              <p>&ldquo;A photographer quoted me 500 euros for 10 products. I have 200 products.&rdquo;</p>
            </div>
            <div className="landing-pain-card">
              <p>&ldquo;My products are great, but my listings make them look cheap.&rdquo;</p>
            </div>
          </div>
          <p className="landing-pain-cta">
            Opal handles the photography part so you can focus on running your business.
          </p>
        </div>
      </section>

      {/* Features */}
      <section className="landing-features" id="features">
        <div className="landing-section-inner">
          <div className="landing-section-header">
            <div className="landing-badge">
              <Sparkles size={12} />
              What Opal does
            </div>
            <h2 className="landing-h2">One tool instead of five</h2>
            <p className="landing-section-sub">
              Background removal, scene creation, image sharpening, and store
              integration. Pick what you need — skip what you don't.
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
            <h2 className="landing-h2">Your brand, everywhere</h2>
            <p>
              Set up a brand profile once — your colors, your mood, your style — and
              Opal applies it to every image. Whether you have 10 products or 10,000,
              they'll all look like they belong together.
            </p>
            <button className="landing-btn-primary" onClick={onGetStarted}>
              Create your brand profile
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
                Pricing
              </div>
              <h2 className="landing-h2">Pay for what you use</h2>
              <p className="landing-section-sub">
                Buy tokens, spend them whenever. No subscriptions, no monthly bills
                sneaking up on you. Each image step costs one token.
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
                      <li><Check size={14} /> Every feature included</li>
                      <li><Check size={14} /> Tokens never expire</li>
                      <li><Check size={14} /> Store integrations</li>
                      {i >= 1 && <li><Check size={14} /> Brand profiles &amp; scene library</li>}
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
          <h2 className="landing-h2">Your store deserves images that <span className="landing-h1-accent">shine</span></h2>
          <p className="landing-section-sub">
            Sign up in seconds, get free tokens to try it out. If your
            product photos don't look better, we'll be surprised.
          </p>
          <button className="landing-btn-primary landing-btn-lg" onClick={onGetStarted}>
            Try Opal free
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
            Studio-quality product photos, without the studio
          </div>
        </div>
      </footer>
    </div>
  );
}
