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
    // 使用进程工作目录推导项目根，避免 __dirname 在ESM环境差异
    const projectRoot = process.cwd();
    const examplesDir = path.resolve(projectRoot, '../examples');
    const outputsLatestDir = path.resolve(projectRoot, '../outputs/latest');
    server.middlewares.use('/examples', (req, res, next) => {
      try {
        const url = req.url || '/';
        // 当以 '/examples' 挂载时，req.url 一般为 '/<file>'，只需去掉开头的 '/'
        const rel = url.replace(/^\//, '');
        const safe = rel.replace(/\\/g, '/');
        const filePath = path.join(examplesDir, safe);
        if (!filePath.startsWith(examplesDir)) { res.statusCode = 403; res.end('Forbidden'); return; }
        if (!fs.existsSync(filePath) || !fs.statSync(filePath).isFile()) { res.statusCode = 404; res.end('Not Found'); return; }
        const buf = fs.readFileSync(filePath);
        res.statusCode = 200;
        res.setHeader('Content-Type', 'application/json; charset=utf-8');
        res.setHeader('Cache-Control', 'no-store, max-age=0');
        res.setHeader('Pragma', 'no-cache');
        res.setHeader('Expires', '0');
        res.end(buf);
      } catch (e) { next(); }
    });
    server.middlewares.use('/outputs/latest', (req, res, next) => {
      try {
        const url = req.url || '/';
        // 同理，去掉前导 '/'
        const rel = url.replace(/^\//, '');
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
        res.setHeader('Cache-Control', 'no-store, max-age=0');
        res.setHeader('Pragma', 'no-cache');
        res.setHeader('Expires', '0');
        const buf = fs.readFileSync(filePath);
        res.statusCode = 200;
        res.end(buf);
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
  },
  define: (() => {
    const projectRoot = process.cwd();
    const examplesAbs = (path.resolve(projectRoot, '../examples')).replace(/\\/g, '/');
    return { __EXAMPLES_ABS__: JSON.stringify(examplesAbs) } as Record<string, string>;
  })()
});



