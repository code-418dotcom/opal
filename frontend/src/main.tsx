import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { bootMsal } from './auth.ts'

// Start MSAL initialization immediately (non-blocking).
// In popup windows, handleRedirectPromise() processes the #code= hash
// and communicates back to the parent window.
bootMsal()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
