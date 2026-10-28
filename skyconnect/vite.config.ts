import path from 'node:path';
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

const TESTBED = process.env.SKYCONNECT_TESTBED || 'https://196.189.236.103';
const SPA = '/app/agent_dashboard/skyconnect/';

export default defineConfig({
  base: process.env.SKYCONNECT_BASE || SPA,
  plugins: [
    react(),
    tailwindcss(),
    {
      name: 'skyconnect-dev-spa',
      configureServer(server) {
        server.middlewares.use((req, res, next) => {
          const u = (req.url || '').split('?')[0];
          const method = (req.method || 'GET').toUpperCase();
          if (
            method !== 'POST' &&
            (u === '/login' ||
              u === '/login/' ||
              u === '/login.php' ||
              u === '/core/user_settings/user_login.php')
          ) {
            res.statusCode = 302;
            res.setHeader('Location', '/app/agent_dashboard/skyconnect_signin.php');
            res.end();
            return;
          }
          if (u === '/' || u === '/app/agent_dashboard' || u === '/app/agent_dashboard/') {
            res.statusCode = 302;
            res.setHeader('Location', SPA);
            res.end();
            return;
          }
          next();
        });
      },
    },
  ],
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
      '/logout.php': { target: TESTBED, changeOrigin: true, secure: false },
      '/core': { target: TESTBED, changeOrigin: true, secure: false },
      '/app': {
        target: TESTBED,
        changeOrigin: true,
        secure: false,
        bypass(req) {
          const u = (req.url || '').split('?')[0];
          if (u === '/app/agent_dashboard/skyconnect' || u.startsWith('/app/agent_dashboard/skyconnect/')) {
            return req.url || u;
          }
          if (u === '/app/agent_dashboard' || u === '/app/agent_dashboard/') return SPA;
          return null;
        },
      },
      '/wss': {
        target: TESTBED,
        ws: true,
        changeOrigin: true,
        secure: false,
      },
      '/asr': { target: 'http://127.0.0.1:8100', changeOrigin: true },
      '/v1/transcribe': { target: 'http://127.0.0.1:8100', changeOrigin: true },
      '/v1/evaluate': { target: 'http://127.0.0.1:8100', changeOrigin: true },
      '/health': { target: 'http://127.0.0.1:8100', changeOrigin: true },
    },
  },
});
