import { PublicClientApplication, InteractionRequiredAuthError, type AccountInfo } from '@azure/msal-browser';

const ENTRA_CLIENT_ID = import.meta.env.VITE_ENTRA_CLIENT_ID as string;
const ENTRA_AUTHORITY = import.meta.env.VITE_ENTRA_AUTHORITY as string;

const msalConfig = {
  auth: {
    clientId: ENTRA_CLIENT_ID || '',
    authority: ENTRA_AUTHORITY || '',
    redirectUri: window.location.origin,
  },
  cache: {
    cacheLocation: 'sessionStorage' as const,
  },
};

// Lazy-init MSAL — creating with empty clientId throws
let _msalInstance: PublicClientApplication | null = null;

function msal(): PublicClientApplication {
  if (!_msalInstance) {
    _msalInstance = new PublicClientApplication(msalConfig);
  }
  return _msalInstance;
}

export const isAuthConfigured = (): boolean =>
  Boolean(ENTRA_CLIENT_ID && ENTRA_AUTHORITY);

export async function initializeMsal(): Promise<void> {
  if (!isAuthConfigured()) return;
  await msal().initialize();
  await msal().handleRedirectPromise();
}

export function getAccount(): AccountInfo | null {
  if (!isAuthConfigured()) return null;
  const accounts = msal().getAllAccounts();
  return accounts.length > 0 ? accounts[0] : null;
}

export async function login(): Promise<void> {
  await msal().loginPopup({
    scopes: [`api://${ENTRA_CLIENT_ID}/access`],
  });
}

export async function logout(): Promise<void> {
  const account = getAccount();
  if (account) {
    await msal().logoutPopup({ account });
  }
}

export async function getAccessToken(): Promise<string | null> {
  if (!isAuthConfigured()) return null;

  const account = getAccount();
  if (!account) return null;

  try {
    const response = await msal().acquireTokenSilent({
      scopes: [`api://${ENTRA_CLIENT_ID}/access`],
      account,
    });
    return response.accessToken;
  } catch (e) {
    if (e instanceof InteractionRequiredAuthError) {
      const response = await msal().acquireTokenPopup({
        scopes: [`api://${ENTRA_CLIENT_ID}/access`],
      });
      return response.accessToken;
    }
    console.error('Failed to acquire token:', e);
    return null;
  }
}
