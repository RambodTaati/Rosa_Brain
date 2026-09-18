import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  base: '/',
  build: {
    outDir: '../rosa_brain/static/app',
    emptyOutDir: true,
    sourcemap: false,
  },
  server: {
    proxy: {
      '/v1': 'http://127.0.0.1:8765',
      '/health': 'http://127.0.0.1:8765',
    },
  },
})
