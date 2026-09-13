import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import AdminApp from './admin/AdminApp'
import { I18nProvider } from './i18n'
import './index.css'

// Vue totalement séparée : /admin → administration DGI (jamais visible côté contribuable).
const isAdmin = window.location.pathname.startsWith('/admin')

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    {isAdmin ? (
      <AdminApp />
    ) : (
      <I18nProvider>
        <App />
      </I18nProvider>
    )}
  </StrictMode>,
)
