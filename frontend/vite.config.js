import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    port: 5173,
    proxy: {
      // Local FastAPI development server runs on port 8000.
      // Docker uses Nginx to proxy to the same API service internally.
      '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true },
    },
  },
})
