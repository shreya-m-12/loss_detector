import http from 'http';
import { spawn } from 'child_process';
import path from 'path';

const PORT = 3000;
const FLASK_TARGET_PORT = 5000;
const FLASK_TARGET_HOST = '127.0.0.1';

// Ensure Flask is running
function ensureFlaskRunning() {
  const checkReq = http.request(
    {
      hostname: FLASK_TARGET_HOST,
      port: FLASK_TARGET_PORT,
      path: '/health',
      method: 'GET',
      timeout: 1000,
    },
    (res) => {
      // Flask already running
    }
  );

  checkReq.on('error', () => {
    console.log('[server.ts] Starting Flask backend process on port 5000...');
    const flaskProcess = spawn('python3', ['app.py'], {
      cwd: path.resolve(__dirname, '.'),
      stdio: 'inherit',
      env: { ...process.env, FLASK_PORT: '5000' },
    });

    flaskProcess.on('exit', (code) => {
      console.log(`[server.ts] Flask process exited with code ${code}`);
    });
  });

  checkReq.end();
}

ensureFlaskRunning();

// Create HTTP reverse proxy server on port 3000
const server = http.createServer((req, res) => {
  const options: http.RequestOptions = {
    hostname: FLASK_TARGET_HOST,
    port: FLASK_TARGET_PORT,
    path: req.url,
    method: req.method,
    headers: {
      ...req.headers,
      host: `${FLASK_TARGET_HOST}:${FLASK_TARGET_PORT}`,
      'x-forwarded-host': req.headers.host || 'localhost:3000',
      'x-forwarded-proto': 'http',
    },
  };

  const proxyReq = http.request(options, (proxyRes) => {
    res.writeHead(proxyRes.statusCode || 200, proxyRes.headers);
    proxyRes.pipe(res);
  });

  proxyReq.on('error', (err) => {
    console.error('[Proxy Error]', err.message);
    if (!res.headersSent) {
      res.writeHead(502, { 'Content-Type': 'text/html' });
      res.end(`
        <div style="font-family: sans-serif; padding: 40px; text-align: center;">
          <h2>Starting Analytics Backend...</h2>
          <p>The Python Flask and MySQL engine is initializing. Please refresh in a few seconds.</p>
        </div>
      `);
    }
  });

  req.pipe(proxyReq);
});

server.listen(PORT, '0.0.0.0', () => {
  console.log(`[server.ts] Reverse proxy gateway listening on port ${PORT} -> Flask :${FLASK_TARGET_PORT}`);
});
