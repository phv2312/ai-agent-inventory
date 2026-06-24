import { resolve } from 'node:path';
import { defineConfig } from 'vite';

export default defineConfig({
    build: {
        lib: {
            entry: resolve(__dirname, 'src/widget-runtime/index.ts'),
            name: 'KN',
            formats: ['iife'],
            fileName: () => 'kn-runtime.iife.js',
        },
        outDir: resolve(__dirname, 'src/assets'),
        emptyOutDir: false,
        rollupOptions: {
            output: {
                extend: true,
            },
        },
    },
});
