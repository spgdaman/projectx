import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { resolve } from 'path';

// Builds popup.jsx → popup/popup.js (single IIFE bundle, no CDN imports)
export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      input: resolve(__dirname, 'popup/popup.jsx'),
      output: {
        entryFileNames: 'popup/popup.js',
        chunkFileNames: 'popup/[name].js',
        assetFileNames: 'popup/[name][extname]',
        format: 'iife',
        name: 'BHKPopup',
        inlineDynamicImports: true,
      },
    },
    outDir: '.',
    emptyOutDir: false,
    copyPublicDir: false,
  },
});
