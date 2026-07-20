const TARGET = process.env.PROXY_TARGET || 'http://127.0.0.1:5001';

const proxyConfig = {
  '/api': { target: TARGET, changeOrigin: true, secure: false },
  '/admin/api': { target: TARGET, changeOrigin: true, secure: false },
  '/admin/payments/': { target: TARGET, changeOrigin: true, secure: false },
  '/admin/generate-ia-report': { target: TARGET, changeOrigin: true, secure: false },
  '/admin/analyze-receipt': { target: TARGET, changeOrigin: true, secure: false },
  '/admin/reports/': { target: TARGET, changeOrigin: true, secure: false },
  '/admin/csp-reports/': { target: TARGET, changeOrigin: true, secure: false },
  '/admin/yape/': { target: TARGET, changeOrigin: true, secure: false },
  '/admin/ai/': { target: TARGET, changeOrigin: true, secure: false },
  '/therapist/api': { target: TARGET, changeOrigin: true, secure: false },
  '/uploads': { target: TARGET, changeOrigin: true, secure: false },
  '/login': { target: TARGET, changeOrigin: true, secure: false },
  '/logout': { target: TARGET, changeOrigin: true, secure: false },
  '/dashboard': { target: TARGET, changeOrigin: true, secure: false },
  '/moscowle': {
    target: TARGET,
    changeOrigin: true,
    secure: false,
    rewrite: (path) => path.replace(/^\/moscowle/, ''),
  },
};

module.exports = proxyConfig;
