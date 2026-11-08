/**
 * Measure built SDK bundle sizes (ES module, UMD, and React wrapper) and write
 * `results/system/sdk_size.json` (P6-12).
 *
 * Fails with exit code 1 if the core ES or UMD gzipped bundle exceeds the 30 KB target.
 */
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { gzipSync } from 'node:zlib';

const __dirname = dirname(fileURLToPath(import.meta.url));
const sdkRoot = resolve(__dirname, '..');
const repoRoot = resolve(sdkRoot, '..');
const distDir = resolve(sdkRoot, 'dist');
const outputPath = resolve(repoRoot, 'results', 'system', 'sdk_size.json');

const TARGET_MAX_GZIP_BYTES = 30 * 1024; // 30 KB target (P6-12)

function measureFile(relPath) {
  const fullPath = resolve(distDir, relPath);
  const rawBuffer = readFileSync(fullPath);
  const gzipBuffer = gzipSync(rawBuffer, { level: 9 });
  return {
    file: `dist/${relPath.replace(/\\/g, '/')}`,
    raw_bytes: rawBuffer.byteLength,
    raw_kb: Number((rawBuffer.byteLength / 1024).toFixed(2)),
    gzip_bytes: gzipBuffer.byteLength,
    gzip_kb: Number((gzipBuffer.byteLength / 1024).toFixed(2)),
  };
}

const esBundle = measureFile('botguard.js');
const umdBundle = measureFile('botguard.umd.cjs');
const reactWrapper = measureFile('react/index.js');

const withinBudget =
  esBundle.gzip_bytes <= TARGET_MAX_GZIP_BYTES && umdBundle.gzip_bytes <= TARGET_MAX_GZIP_BYTES;

const report = {
  package: '@botguard/sdk',
  version: '1.0.0',
  target_max_gzip_bytes: TARGET_MAX_GZIP_BYTES,
  target_max_gzip_kb: 30,
  within_target: withinBudget,
  bundles: {
    esm: esBundle,
    umd: umdBundle,
    react: reactWrapper,
  },
};

mkdirSync(dirname(outputPath), { recursive: true });
writeFileSync(outputPath, `${JSON.stringify(report, null, 2)}\n`, 'utf8');

console.log(
  `SDK size report written to ${outputPath}: ESM=${esBundle.gzip_kb} KB gzip, UMD=${umdBundle.gzip_kb} KB gzip (target <= 30 KB)`,
);

if (!withinBudget) {
  console.error(
    `Core bundle exceeded 30 KB gzip target: ESM=${esBundle.gzip_bytes} B, UMD=${umdBundle.gzip_bytes} B`,
  );
  process.exit(1);
}
