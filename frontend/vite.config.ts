import path from 'node:path'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Backend port is picked at runtime by run.sh (defaults collide with sibling
// challenge repos' dev servers when several run at once) and passed through
// so the dev-server proxy points at wherever the backend actually landed.
const backendPort = process.env.VITE_BACKEND_PORT ?? '8000'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': path.resolve(import.meta.dirname, './src'),
    },
  },
  server: {
    proxy: {
      '/api': `http://localhost:${backendPort}`,
    },
  },
})
