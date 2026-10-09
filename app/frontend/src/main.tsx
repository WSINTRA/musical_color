import { MantineProvider } from '@mantine/core'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import '@mantine/core/styles.css'
import App from './App'
import './index.css'

const queryClient = new QueryClient()

const rootEl = document.getElementById('root')
if (!rootEl) {
  throw new Error('root element #root not found')
}

createRoot(rootEl).render(
  <StrictMode>
    <MantineProvider>
      <QueryClientProvider client={queryClient}>
        <App />
      </QueryClientProvider>
    </MantineProvider>
  </StrictMode>,
)
