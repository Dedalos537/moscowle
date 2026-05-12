const TARGET = process.env.PROXY_TARGET || 'http://127.0.0.1:5000';

// En desarrollo (apiBaseUrl='') se usan rutas sin /moscowle
// En modo producción local (ng serve -c production, apiBaseUrl='/moscowle') se usan rutas con /moscowle
// El proxy debe aceptar ambos contextos para que funcione en cualquier modo

const common = ['/api', '/admin/api', '/therapist/api', '/uploads', '/login', '/logout'];
const moscowle = common.map(p => '/moscowle' + p);

module.exports = [
  {
    context: [...common, ...moscowle],
    target: TARGET,
    secure: TARGET.startsWith('https'),
    changeOrigin: true,
    logLevel: 'debug',
  },
];
