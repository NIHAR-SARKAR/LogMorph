import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import { fileURLToPath } from 'url'
import fs from 'fs'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, __dirname, '')

  const port = parseInt(env.VITE_PORT || '3000', 10)
  const allowedHosts = (env.VITE_ALLOWED_HOSTS || 'localhost')
    .split(',')
    .map((h) => h.trim())
    .filter(Boolean)

  const backendUrl = env.VITE_BACKEND_URL || 'http://localhost:8000'
  const proxySecure = env.VITE_PROXY_SECURE === 'true'

  const sslKeyFile = env.VITE_SSL_KEY_FILE || ''
  const sslCertFile = env.VITE_SSL_CERT_FILE || ''
  const useHttps = Boolean(sslKeyFile && sslCertFile)

  const httpsConfig = useHttps
    ? {
        https: {
          key: fs.readFileSync(sslKeyFile),
          cert: fs.readFileSync(sslCertFile),
        },
      }
    : {}

  return {
    plugins: [react()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },
    server: {
      port,
      allowedHosts,
      ...httpsConfig,
      proxy: {
        '/api': {
          target: backendUrl,
          changeOrigin: true,
          secure: proxySecure,
        },
      },
    },
    build: {
      outDir: 'dist',
      sourcemap: true,
    },
  }
})
