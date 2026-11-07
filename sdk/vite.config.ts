import { fileURLToPath } from 'node:url';
import { defineConfig } from 'vite';

// Library build: ES module plus UMD (Section 3.3). The core has no runtime dependencies.
export default defineConfig({
  build: {
    target: 'es2020',
    sourcemap: true,
    emptyOutDir: false, // keep the .d.ts files emitted by tsc -p tsconfig.build.json
    lib: {
      entry: fileURLToPath(new URL('./src/index.ts', import.meta.url)),
      name: 'BotGuard',
      formats: ['es', 'umd'],
      fileName: (format) => (format === 'es' ? 'botguard.js' : 'botguard.umd.cjs'),
    },
  },
});
