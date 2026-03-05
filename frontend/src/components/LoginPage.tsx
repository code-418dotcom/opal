import { useState } from 'react';
import { LogIn } from 'lucide-react';
import { login } from '../auth';

interface LoginPageProps {
  onLoginSuccess: () => void;
}

export default function LoginPage({ onLoginSuccess }: LoginPageProps) {
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
          <span className="logo-icon">&#9670;</span>
          <h1>OPAL</h1>
          <p className="login-subtitle">AI Image Processing</p>
        </div>

        <p className="login-description">
          Transform your product photos into professional e-commerce imagery.
          Background removal, AI-generated scenes, and image upscaling — all in one platform.
        </p>

        {error && <div className="error-banner">{error}</div>}

        <button
          className="login-button"
          onClick={handleLogin}
          disabled={loading}
        >
          <LogIn size={18} />
          {loading ? 'Signing in...' : 'Sign in'}
        </button>

        <p className="login-footer-text">
          New here? Signing in will create your account automatically.
        </p>
      </div>
    </div>
  );
}
