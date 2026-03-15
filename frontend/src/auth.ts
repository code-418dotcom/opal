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

let _msalInstance: PublicClientApplication | null = null;
let _initPromise: Promise<void> | null = null;

function msal(): PublicClientApplication {
  if (!_msalInstance) {
    _msalInstance = new PublicClientApplication(msalConfig);
  }
  return _msalInstance;
}

export const isAuthConfigured = (): boolean =>
  Boolean(ENTRA_CLIENT_ID && ENTRA_AUTHORITY);

/**
 * Must be called ASAP on page load — before React mounts.
 * In the popup window, this processes the #code= hash and closes the popup.
 * Returns a promise that resolves when MSAL is ready.
 */
export function bootMsal(): Promise<void> {
  if (!isAuthConfigured()) return Promise.resolve();
  if (!_initPromise) {
    _initPromise = msal().initialize().then(() => {
      return msal().handleRedirectPromise();
    }).then(() => {});
  }
  return _initPromise;
}

export async function initializeMsal(): Promise<void> {
  return bootMsal();
}

export function getAccount(): AccountInfo | null {
  if (!isAuthConfigured()) return null;
  const accounts = msal().getAllAccounts();
  return accounts.length > 0 ? accounts[0] : null;
}

export async function login(): Promise<void> {
  await bootMsal();
  await msal().loginPopup({
    scopes: [`api://${ENTRA_CLIENT_ID}/access`],
    redirectUri: `${window.location.origin}/blank.html`,
  });
}

export async function logout(): Promise<void> {
  const account = getAccount();
  if (account) {
    try {
      // End both local and Entra SSO session so re-login requires credentials
      await msal().logoutPopup({
        account,
        mainWindowRedirectUri: window.location.origin,
      });
    } catch {
      // Fallback: if popup blocked/fails, at least clear local state
      await msal().clearCache();
    }
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
