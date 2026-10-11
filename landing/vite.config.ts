import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// LANDING_BASE: '/' en producción (raíz de centrojuanpabloii.com), '/nuevo/' para la vista previa.
export default defineConfig({
  base: process.env.LANDING_BASE || '/',
  plugins: [react()],
  // El contenido por defecto vive en el backend (app/data) para que landing y API partan del mismo texto.
  server: { fs: { allow: ['..'] }, port: 5180 },
  build: { target: 'es2020', cssCodeSplit: true, sourcemap: false },
});
