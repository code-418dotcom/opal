import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { bootMsal } from './auth.ts'

// Initialize MSAL before React mounts. In the popup window this
// processes the #code= hash response and closes the popup immediately.
bootMsal().then(() => {
  createRoot(document.getElementById('root')!).render(
    <StrictMode>
      <App />
    </StrictMode>,
  )
})
