import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path'; // Adicionado para lidar com caminhos de forma robusta

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],

  // --- Configurações do Servidor de Desenvolvimento ---
  // Esta seção afeta apenas quando você roda `npm run dev`.
  server: {
    // A configuração de 'proxy' é crucial para o desenvolvimento local.
    // Ela resolve problemas de CORS ao fazer requisições do frontend (ex: localhost:5173)
    // para o backend (ex: localhost:5000), fazendo com que o navegador pense
    // que ambas as requisições vêm da mesma origem.
    proxy: {
      // Qualquer requisição que o frontend faça para um caminho que comece com '/api'
      // será interceptada e redirecionada para o backend.
      '/api': {
        target: 'http://127.0.0.1:5000', // O endereço do seu backend Flask local.
        changeOrigin: true, // Essencial para que o backend receba a requisição corretamente.
        
        // A linha 'rewrite' foi removida pois é desnecessária. O Vite já anexa 
        // o caminho da requisição ao 'target' por padrão. Por exemplo, uma chamada a 
        // '/api/v1/ranking/full' é automaticamente enviada para 
        // 'http://127.0.0.1:5000/api/v1/ranking/full', que é o comportamento desejado.
      },
    },
  },

  // --- Configurações para o Build de Produção ---
  // Esta seção afeta quando você roda `npm run build`.
  build: {
    outDir: 'dist',    // O diretório de saída para os arquivos de produção. 'dist' é o padrão.
    sourcemap: false,  // Desabilitar source maps em produção para otimizar o tamanho e a segurança.
  },

  // --- Configuração de Alias (Boa Prática) ---
  // Define um atalho '@' para o diretório 'src'. Isso permite importações mais limpas.
  // Exemplo: em vez de `import { Button } from '../../components/ui/button'`,
  // você pode usar `import { Button } from '@/components/ui/button'`.
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
});
