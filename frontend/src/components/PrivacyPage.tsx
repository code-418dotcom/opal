/**
 * Standalone Privacy Policy page — accessible at /privacy
 * Renders the full privacy policy for direct linking (e.g., Shopify App Store).
 */
import { useTranslation } from 'react-i18next';
import OpalLogo from './OpalLogo';
import './LegalPage.css';

export default function PrivacyPage() {
  const { t } = useTranslation();

  const sections = Array.from({ length: 13 }, (_, i) => i + 1);

  return (
    <div className="legal-page">
      <div className="legal-page-header">
        <a href="/" className="legal-logo">
          <span className="legal-logo-icon"><OpalLogo size={22} /></span> OPAL
        </a>
      </div>
      <div className="legal-page-content">
        <h1>{t('landing.privacy.title')}</h1>
        <p className="legal-updated">{t('landing.privacy.lastUpdated')}</p>
        <p className="legal-intro">{t('landing.privacy.intro')}</p>

        {sections.map((n) => (
          <section key={n}>
            <h2>{t(`landing.privacy.section${n}Title`)}</h2>
            {n === 2 ? (
              <div>
                <p>{t('landing.privacy.section2a')}</p>
                <p>{t('landing.privacy.section2b')}</p>
                <p>{t('landing.privacy.section2c')}</p>
                <p>{t('landing.privacy.section2d')}</p>
                <p>{t('landing.privacy.section2e')}</p>
                <p>{t('landing.privacy.section2f')}</p>
              </div>
            ) : n === 13 ? (
              <div>
                <p>{t('landing.privacy.section13a')}</p>
                <p>{t('landing.privacy.section13b')}</p>
                <p>{t('landing.privacy.section13c')}</p>
                <p>{t('landing.privacy.section13d')}</p>
                <p>{t('landing.privacy.section13e')}</p>
                <p>{t('landing.privacy.section13f')}</p>
                <p>{t('landing.privacy.section13g')}</p>
                <p>{t('landing.privacy.section13h')}</p>
              </div>
            ) : (
              <p>{t(`landing.privacy.section${n}`)}</p>
            )}
          </section>
        ))}
      </div>
      <div className="legal-page-footer">
        <p>&copy; {new Date().getFullYear()} Aardvark Hosting. {t('landing.footer.copyright')}</p>
        <div className="legal-footer-links">
          <a href="/terms">Terms of Service</a>
          <a href="/support">Support</a>
          <a href="/">Home</a>
        </div>
      </div>
    </div>
  );
}
