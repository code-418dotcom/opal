import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { LogIn } from 'lucide-react';
import { login } from '../auth';
import OpalLogo from './OpalLogo';

interface LoginPageProps {
  onLoginSuccess: () => void;
}

export default function LoginPage({ onLoginSuccess }: LoginPageProps) {
  const { t } = useTranslation();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleLogin = async () => {
    setLoading(true);
    setError(null);
    try {
      await login();
      onLoginSuccess();
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Login failed';
      if (!msg.includes('user_cancelled')) {
        setError(msg);
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="login-logo">
          <span className="logo-icon"><OpalLogo size={48} /></span>
          <h1>OPAL</h1>
          <p className="login-subtitle">{t('login.subtitle')}</p>
        </div>

        <p className="login-description">
          {t('login.description')}
        </p>

        {error && <div className="error-banner">{error}</div>}

        <button
          className="login-button"
          onClick={handleLogin}
          disabled={loading}
        >
          <LogIn size={18} />
          {loading ? t('login.signingIn') : t('common.signIn')}
        </button>

        <p className="login-footer-text">
          {t('login.footerText')}
        </p>
      </div>
    </div>
  );
}
