import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    // Forward /api/... requests to Flask so the browser never hits cross-origin problems.
    proxy: {
      '/api': 'http://127.0.0.1:5001',
    },
  },
})