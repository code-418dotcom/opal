import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';

import en from './locales/en.json';
import es from './locales/es.json';
import fr from './locales/fr.json';
import tr from './locales/tr.json';
import de from './locales/de.json';

export const LANGUAGES = [
  { code: 'en', name: 'English', flag: '🇬🇧' },
  { code: 'es', name: 'Español', flag: '🇪🇸' },
  { code: 'fr', name: 'Français', flag: '🇫🇷' },
  { code: 'tr', name: 'Türkçe', flag: '🇹🇷' },
  { code: 'de', name: 'Deutsch', flag: '🇩🇪' },
] as const;

// Map countries to languages for geolocation fallback
const COUNTRY_TO_LANG: Record<string, string> = {
  TR: 'tr',
  DE: 'de', AT: 'de', CH: 'de',
  ES: 'es', MX: 'es', AR: 'es', CO: 'es', CL: 'es', PE: 'es',
  FR: 'fr', BE: 'fr', SN: 'fr', CI: 'fr',
};

export async function detectGeoLanguage(): Promise<string | null> {
  // Only run once — skip if user already has a stored preference
  if (localStorage.getItem('i18nextLng')) return null;

  try {
    const resp = await fetch('https://ipapi.co/json/', { signal: AbortSignal.timeout(3000) });
    if (!resp.ok) return null;
    const data = await resp.json();
    const country = data.country_code?.toUpperCase();
    return country ? COUNTRY_TO_LANG[country] || null : null;
  } catch {
    return null;
  }
}

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: {
      en: { translation: en },
      es: { translation: es },
      fr: { translation: fr },
      tr: { translation: tr },
      de: { translation: de },
    },
    fallbackLng: 'en',
    interpolation: { escapeValue: false },
    detection: {
      order: ['localStorage', 'navigator'],
      caches: ['localStorage'],
    },
  });

export default i18n;
