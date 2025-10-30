import { defineConfig } from 'vite';
import * as fs from 'fs';
import * as path from 'path';
import vue from '@vitejs/plugin-vue';

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    strictPort: false,
    fs: {
      allow: [path.resolve(__dirname, '..')]
    },
    // 简易静态映射：/examples/* -> 上级项目根的 examples 目录
    middlewareMode: false,
  },
  configureServer(server) {
    const examplesDir = path.resolve(__dirname, '../examples');
    const outputsLatestDir = path.resolve(__dirname, '../outputs/latest');
    server.middlewares.use('/examples', (req, res, next) => {
      try {
        const url = req.url || '/';
        const rel = url.replace(/^\/?examples\/?/, '');
        const safe = rel.replace(/\\/g, '/');
        const filePath = path.join(examplesDir, safe);
        if (!filePath.startsWith(examplesDir)) { res.statusCode = 403; res.end('Forbidden'); return; }
        if (!fs.existsSync(filePath) || !fs.statSync(filePath).isFile()) { res.statusCode = 404; res.end('Not Found'); return; }
        res.setHeader('Content-Type', 'application/json; charset=utf-8');
        fs.createReadStream(filePath).pipe(res);
      } catch (e) { next(); }
    });
    server.middlewares.use('/outputs/latest', (req, res, next) => {
      try {
        const url = req.url || '/';
        const rel = url.replace(/^\/?outputs\/latest\/?/, '');
        const safe = rel.replace(/\\/g, '/');
        const filePath = path.join(outputsLatestDir, safe);
        if (!filePath.startsWith(outputsLatestDir)) { res.statusCode = 403; res.end('Forbidden'); return; }
        if (!fs.existsSync(filePath)) { res.statusCode = 404; res.end('Not Found'); return; }
        const stat = fs.statSync(filePath);
        if (stat.isDirectory()) { next(); return; }
        const ext = path.extname(filePath).toLowerCase();
        if (ext === '.tif' || ext === '.tiff') res.setHeader('Content-Type', 'image/tiff');
        else if (ext === '.parquet') res.setHeader('Content-Type', 'application/octet-stream');
        else res.setHeader('Content-Type', 'application/octet-stream');
        fs.createReadStream(filePath).pipe(res);
      } catch (e) { next(); }
    });
    server.middlewares.use('/__dev/outputs', (_req, res) => {
      try {
        const bands = fs.readdirSync(outputsLatestDir).filter(d => {
          const p = path.join(outputsLatestDir, d);
          return fs.existsSync(p) && fs.statSync(p).isDirectory() && fs.existsSync(path.join(p, `${d}_field_strength.tif`));
        });
        res.setHeader('Content-Type', 'application/json; charset=utf-8');
        res.end(JSON.stringify({ bands }));
      } catch {
        res.statusCode = 200; res.setHeader('Content-Type', 'application/json'); res.end(JSON.stringify({ bands: [] }));
      }
    });
  }
});



