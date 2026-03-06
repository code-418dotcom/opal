import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import './i18n'
import App from './App.tsx'
import { bootMsal, isAuthConfigured } from './auth.ts'
import { detectGeoLanguage } from './i18n'
import i18n from 'i18next'

// MSAL v5 popup flow: the popup window receives a #code=...&state=... hash.
// The state contains interactionType:"popup". The redirect bridge broadcasts
// the response to the parent via BroadcastChannel and closes the popup.
const isMsalPopup = isAuthConfigured() && window.location.hash.includes('code=') && window.location.hash.includes('state=')

if (isMsalPopup) {
  import('@azure/msal-browser/redirect-bridge').then(({ broadcastResponseToMainFrame }) => {
    broadcastResponseToMainFrame().catch(() => {})
  })
} else {
  // Detect language from geolocation on first visit
  detectGeoLanguage().then(lang => {
    if (lang) i18n.changeLanguage(lang)
  })

  bootMsal()
  createRoot(document.getElementById('root')!).render(
    <StrictMode>
      <App />
    </StrictMode>,
  )
}
