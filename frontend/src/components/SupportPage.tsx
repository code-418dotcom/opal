/**
 * Support & Contact page — accessible at /support
 * Required for Shopify App Store submission.
 */
import OpalLogo from './OpalLogo';
import './LegalPage.css';

export default function SupportPage() {
  return (
    <div className="legal-page">
      <div className="legal-page-header">
        <a href="/" className="legal-logo">
          <span className="legal-logo-icon"><OpalLogo size={22} /></span> OPAL
        </a>
      </div>
      <div className="legal-page-content">
        <h1>Support & Contact</h1>

        <section>
          <h2>Get Help</h2>
          <p>
            Need help with Opal? We're here for you. Whether you're setting up your
            first A/B test, connecting your store, or have questions about your account,
            reach out and we'll get back to you within 24 hours on business days.
          </p>
        </section>

        <section>
          <h2>Contact Us</h2>
          <div className="support-contact-grid">
            <div className="support-contact-card">
              <h3>Email Support</h3>
              <p>For general questions, technical issues, or account inquiries:</p>
              <a href="mailto:support@opaloptics.com" className="support-link">
                support@opaloptics.com
              </a>
            </div>
            <div className="support-contact-card">
              <h3>Data & Privacy</h3>
              <p>For GDPR requests, data export, or privacy-related questions:</p>
              <a href="mailto:privacy@opaloptics.com" className="support-link">
                privacy@opaloptics.com
              </a>
            </div>
          </div>
        </section>

        <section>
          <h2>Common Questions</h2>

          <div className="support-faq">
            <details>
              <summary>How do I connect my Shopify store?</summary>
              <p>
                Install the Opal A/B Testing app from the Shopify App Store. Your store
                will be automatically connected when you open the app. Go to Settings
                to configure the tracking pixel.
              </p>
            </details>

            <details>
              <summary>How does the pixel tracking work?</summary>
              <p>
                Opal's web pixel automatically tracks product views, add-to-carts, and
                checkout conversions on your storefront. It runs in a sandboxed
                environment and does not collect personal customer data. Configure it
                from the Settings page in the app.
              </p>
            </details>

            <details>
              <summary>How do I cancel my subscription?</summary>
              <p>
                Go to Plans & Billing in the Opal app and click "Cancel subscription."
                You'll retain Pro features until the end of your current billing period.
                You can also uninstall the app from your Shopify admin.
              </p>
            </details>

            <details>
              <summary>What happens to my data if I uninstall?</summary>
              <p>
                Your test data and results are preserved for 90 days. You can request
                full data deletion by contacting support@opaloptics.com. We comply with
                all Shopify and GDPR data deletion requirements.
              </p>
            </details>

            <details>
              <summary>How do I request my data or delete my account?</summary>
              <p>
                Under GDPR, you have the right to access, export, or delete your data.
                Contact privacy@opaloptics.com or use the data management features in
                your account settings. We respond within 30 days.
              </p>
            </details>
          </div>
        </section>

        <section>
          <h2>Business Information</h2>
          <p>
            Opal Optics<br />
            The Netherlands<br />
            KvK: [Registration pending]
          </p>
        </section>
      </div>
      <div className="legal-page-footer">
        <p>&copy; {new Date().getFullYear()} Opal Optics. All rights reserved.</p>
        <div className="legal-footer-links">
          <a href="/privacy">Privacy Policy</a>
          <a href="/terms">Terms of Service</a>
          <a href="/">Home</a>
        </div>
      </div>
    </div>
  );
}
