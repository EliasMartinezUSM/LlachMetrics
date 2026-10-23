import react from '@vitejs/plugin-react'
import { spawn } from 'node:child_process'
import { existsSync } from 'node:fs'
import net from 'node:net'
import path from 'node:path'
import process from 'node:process'
import { fileURLToPath } from 'node:url'
import { defineConfig, loadEnv } from 'vite'

function resolvePythonExecutable(configDir) {
  const candidates = [
    path.join(configDir, '.venv', 'bin', 'python'),
    path.join(configDir, '..', 'BackEnd', '.venv', 'bin', 'python'),
    'python3',
  ]
  return candidates.find((candidate) => candidate === 'python3' || existsSync(candidate))
}

function isPortListening(port, host = '127.0.0.1') {
  return new Promise((resolve) => {
    const socket = new net.Socket()
    socket.setTimeout(600)
    socket.once('connect', () => {
      socket.destroy()
      resolve(true)
    })
    socket.once('timeout', () => {
      socket.destroy()
      resolve(false)
    })
    socket.once('error', () => {
      socket.destroy()
      resolve(false)
    })
    socket.connect(port, host)
  })
}

function easyOcrBackendPlugin(configDir, port = 8001) {
  let ocrProcess = null

  const ensureBackend = async () => {
    if (ocrProcess) return
    const alreadyUp = await isPortListening(port)
    if (alreadyUp) return

    const pythonBin = resolvePythonExecutable(configDir)
    ocrProcess = spawn(
      pythonBin,
      ['-m', 'uvicorn', 'ocr_server:app', '--host', '127.0.0.1', '--port', String(port)],
      {
        cwd: configDir,
        stdio: 'inherit',
      },
    )

    const cleanup = () => {
      if (ocrProcess && !ocrProcess.killed) {
        ocrProcess.kill('SIGTERM')
        ocrProcess = null
      }
    }

    process.once('exit', cleanup)
    process.once('SIGINT', cleanup)
    process.once('SIGTERM', cleanup)
  }

  return {
    name: 'llachmetrics-easyocr-backend',
    configureServer() {
      ensureBackend()
    },
    configurePreviewServer() {
      ensureBackend()
    },
  }
}

export default defineConfig(({ mode }) => {
  const configDir = fileURLToPath(new URL('.', import.meta.url))
  const env = loadEnv(mode, configDir, '')
  const ocrPort = Number(env.OCR_PORT || 8001)
  const targetUrl = env.API_PROXY_TARGET || `http://127.0.0.1:${ocrPort}`
  const apiProxy = {
    '/api': {
      target: targetUrl,
      changeOrigin: true,
    },
  }

  const devPort = Number(env.PORT || env.VITE_PORT || 5175)
  const previewPort = Number(env.PREVIEW_PORT || 4175)

  return {
    plugins: [react(), easyOcrBackendPlugin(configDir, ocrPort)],
    server: {
      host: '0.0.0.0',
      port: devPort,
      strictPort: false,
      allowedHosts: env.VITE_DEV_TUNNEL_HOST ? [env.VITE_DEV_TUNNEL_HOST] : [],
      proxy: apiProxy,
    },
    preview: {
      host: '0.0.0.0',
      port: previewPort,
      proxy: apiProxy,
    },
  }
})
