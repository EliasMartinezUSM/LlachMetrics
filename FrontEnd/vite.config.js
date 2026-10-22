import react from '@vitejs/plugin-react'
import { fileURLToPath } from 'node:url'
import { defineConfig, loadEnv } from 'vite'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const configDir = fileURLToPath(new URL('.', import.meta.url))
  const env = loadEnv(mode, configDir, '')

  return {
    plugins: [react()],
    server: {
      host: '0.0.0.0',
      allowedHosts: env.VITE_DEV_TUNNEL_HOST
        ? [env.VITE_DEV_TUNNEL_HOST]
        : [],
    },
  }
})
