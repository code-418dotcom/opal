import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react';
import { api } from '../api';

interface Preferences {
  show_help_tooltips: boolean;
  show_tips_bar: boolean;
  dismissed_tips: string[];
}

interface PreferencesContextType {
  preferences: Preferences;
  updatePreference: (key: string, value: unknown) => void;
  dismissTip: (tipId: string) => void;
  loading: boolean;
}

const DEFAULT_PREFERENCES: Preferences = {
  show_help_tooltips: true,
  show_tips_bar: true,
  dismissed_tips: [],
};

const PreferencesContext = createContext<PreferencesContextType>({
  preferences: DEFAULT_PREFERENCES,
  updatePreference: () => {},
  dismissTip: () => {},
  loading: true,
});

export function PreferencesProvider({ children }: { children: ReactNode }) {
  const [preferences, setPreferences] = useState<Preferences>(DEFAULT_PREFERENCES);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getPreferences()
      .then(({ preferences: prefs }) => {
        setPreferences({ ...DEFAULT_PREFERENCES, ...prefs } as Preferences);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const updatePreference = useCallback((key: string, value: unknown) => {
    setPreferences(prev => {
      const updated = { ...prev, [key]: value };
      api.updatePreferences({ [key]: value }).catch(() => {});
      return updated;
    });
  }, []);

  const dismissTip = useCallback((tipId: string) => {
    setPreferences(prev => {
      const dismissed = [...prev.dismissed_tips, tipId];
      api.updatePreferences({ dismissed_tips: dismissed }).catch(() => {});
      return { ...prev, dismissed_tips: dismissed };
    });
  }, []);

  return (
    <PreferencesContext.Provider value={{ preferences, updatePreference, dismissTip, loading }}>
      {children}
    </PreferencesContext.Provider>
  );
}

export function usePreferences() {
  return useContext(PreferencesContext);
}
