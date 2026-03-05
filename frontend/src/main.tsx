import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { bootMsal, isAuthConfigured } from './auth.ts'

// MSAL v5 popup flow: the popup window receives a #code=...&state=... hash.
// The state contains interactionType:"popup". The redirect bridge broadcasts
// the response to the parent via BroadcastChannel and closes the popup.
const isMsalPopup = isAuthConfigured() && window.location.hash.includes('code=') && window.location.hash.includes('state=')

if (isMsalPopup) {
  import('@azure/msal-browser/redirect-bridge').then(({ broadcastResponseToMainFrame }) => {
    broadcastResponseToMainFrame().catch(() => {})
  })
} else {
  bootMsal()
  createRoot(document.getElementById('root')!).render(
    <StrictMode>
      <App />
    </StrictMode>,
  )
}
