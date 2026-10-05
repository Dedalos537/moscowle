export const environment = {
  production: true,
  docker: true,
  apiBaseUrl: '',
  sentryDsn: '',
  preload: true,
  // Sin secreto de reinicio en la imagen Docker (el codigo usa `|| ''`); evita el error TS2339 del build.
  restartSecret: '',
};
