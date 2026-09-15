import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // Em dev dentro do Codespace, o navegador só fala com a porta
      // 5173 (mesma origem). O próprio Vite repassa /api/* para o
      // backend na rede interna do container, evitando problemas de
      // CORS entre portas públicas diferentes do Codespaces.
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})
