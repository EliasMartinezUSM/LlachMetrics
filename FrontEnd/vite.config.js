import react from '@vitejs/plugin-react'
import { fileURLToPath } from 'node:url'
import { defineConfig, loadEnv } from 'vite'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const configDir = fileURLToPath(new URL('.', import.meta.url))
  const env = loadEnv(mode, configDir, '')
  // Sirve la API bajo /api en el mismo origen del frontend. Así la cookie de sesión
  // HttpOnly es de primera parte y funciona con SameSite=Lax en cualquier navegador.
  const apiProxy = {
    '/api': {
      target: env.API_PROXY_TARGET || 'http://127.0.0.1:8000',
      changeOrigin: true,
      rewrite: (path) => path.replace(/^\/api/, ''),
    },
  }

  return {
    plugins: [react()],
    server: {
      host: '0.0.0.0',
      allowedHosts: env.VITE_DEV_TUNNEL_HOST
        ? [env.VITE_DEV_TUNNEL_HOST]
        : [],
      proxy: apiProxy,
    },
    preview: {
      proxy: apiProxy,
    },
  }
})
