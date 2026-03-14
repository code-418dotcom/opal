/**
 * Standalone Terms of Service page — accessible at /terms
 * Renders the full ToS for direct linking (e.g., Shopify App Store).
 */
import { useTranslation } from 'react-i18next';
import OpalLogo from './OpalLogo';
import './LegalPage.css';

export default function TermsPage() {
  const { t } = useTranslation();

  const sections = Array.from({ length: 12 }, (_, i) => i + 1);

  return (
    <div className="legal-page">
      <div className="legal-page-header">
        <a href="/" className="legal-logo">
          <span className="legal-logo-icon"><OpalLogo size={22} /></span> OPAL
        </a>
      </div>
      <div className="legal-page-content">
        <h1>{t('landing.terms.title')}</h1>
        <p className="legal-updated">{t('landing.terms.lastUpdated')}</p>
        <p className="legal-intro">{t('landing.terms.intro')}</p>

        {sections.map((n) => (
          <section key={n}>
            <h2>{t(`landing.terms.section${n}Title`)}</h2>
            <p>{t(`landing.terms.section${n}`)}</p>
          </section>
        ))}
      </div>
      <div className="legal-page-footer">
        <p>&copy; {new Date().getFullYear()} Opal Optics. {t('landing.footer.copyright')}</p>
        <div className="legal-footer-links">
          <a href="/privacy">Privacy Policy</a>
          <a href="/support">Support</a>
          <a href="/">Home</a>
        </div>
      </div>
    </div>
  );
}
