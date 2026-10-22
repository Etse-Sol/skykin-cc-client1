import path from 'node:path';
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

const TESTBED = process.env.SKYCONNECT_TESTBED || 'https://196.189.237.77';

export default defineConfig({
  base: process.env.SKYCONNECT_BASE || '/app/agent_dashboard/skyconnect/',
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { '@': path.resolve(__dirname, 'src') },
  },
  server: {
    port: 5174,
    host: '0.0.0.0',
    proxy: {
      '/api': {
        target: process.env.SKYCONNECT_API || TESTBED,
        changeOrigin: true,
        secure: false,
        rewrite: process.env.SKYCONNECT_API
          ? undefined
          : (p) => p.replace(/^\/api/, '/skyconnect/api'),
      },
      '/login.php': { target: TESTBED, changeOrigin: true, secure: false },
      '/core': { target: TESTBED, changeOrigin: true, secure: false },
      '/app': { target: TESTBED, changeOrigin: true, secure: false },
      '/wss': {
        target: TESTBED,
        ws: true,
        changeOrigin: true,
        secure: false,
      },
    },
  },
});
