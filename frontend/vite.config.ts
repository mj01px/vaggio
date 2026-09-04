import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'node:path'

const BACKEND = 'http://127.0.0.1:8000'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    // import.meta.dirname, e nao __dirname: o carregador nativo de config
    // do Vite nao expoe as globais de CommonJS.
    alias: { '@': path.join(import.meta.dirname, 'src') },
  },
  server: {
    // Fixa IPv4: sem isso o Vite sobe so em [::1] nesta maquina e
    // http://127.0.0.1:5173 nao conecta.
    host: '127.0.0.1',
    port: 5173,
    // Chamar /api pelo proxy em dev evita CORS e mantem a mesma origem
    // que a build de producao usa atras do nginx. Quem muda a porta da API
    // muda `BACKEND` aqui e o `runserver` do scripts/dev.bat, nos dois.
    proxy: {
      '/api': { target: BACKEND, changeOrigin: true },
    },
  },
})
