import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './styles/v2/tokens.css'
import './index.css'
import App from './App.jsx'

async function enableMocksIfNeeded() {
  const enabled = import.meta.env.VITE_MSW_ENABLED === 'true'
  const apiUrl = (import.meta.env.VITE_API_URL ?? '') as string
  const isLocal = apiUrl.includes('localhost') || apiUrl.includes('127.0.0.1')
  if (!enabled || !isLocal || !import.meta.env.DEV) return
  const { worker } = await import('./test/mocks/browser')
  await worker.start({ onUnhandledRequest: 'bypass' })
}

enableMocksIfNeeded().finally(() => {
  createRoot(document.getElementById('root') as HTMLElement).render(
    <StrictMode>
      <App />
    </StrictMode>,
  )
})
