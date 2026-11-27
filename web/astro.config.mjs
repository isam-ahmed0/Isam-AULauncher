// CrewLauncher web GUI build.
//
// The static output is written straight into the launcher's resource folder
// (src/launcher/resources/web) so PyInstaller can bundle it with a single
// --add-data entry. Nothing in here is committed: run `npm run build`.
import { defineConfig } from 'astro/config';

export default defineConfig({
  outDir: '../src/launcher/resources/web',
  build: { format: 'directory' },
  server: { host: '127.0.0.1', port: 4321 },
  vite: {
    build: {
      target: 'es2020',
      cssMinify: true,
    },
  },
});
