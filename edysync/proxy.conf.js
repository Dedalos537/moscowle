module.exports = [
  {
    context: ['/api', '/moscowle'],
    target: 'https://www.centrojuanpabloii.com',
    secure: false,
    changeOrigin: true,
    logLevel: 'debug',
  },
  {
    context: ['/admin/api', '/admin/payments', '/admin/analyze-receipt', '/admin/generate-ia-report', '/uploads'],
    target: 'https://www.centrojuanpabloii.com',
    secure: false,
    changeOrigin: true,
    logLevel: 'debug',
  },
];
