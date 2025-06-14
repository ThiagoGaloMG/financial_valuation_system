import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    outDir: 'dist', // Onde os arquivos de build serão gerados
  },
  server: {
    proxy: {
      // Proxy para redirecionar chamadas de API para o backend Flask
      '/api': {
        target: 'http://localhost:5000', // Endereço do seu backend Flask em desenvolvimento
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '/api'), // Garante que o path /api seja mantido
      },
    },
  },
});
