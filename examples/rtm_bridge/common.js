import path from 'node:path';
import http from 'node:http';
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';

export const DEFAULT_APP_ID = '54f9b64b82204d74b35e3b9c5430a020';
export const DEFAULT_CHROME_PATH = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export function log(...args) {
  const ts = new Date().toISOString().replace('T', ' ').replace('Z', '');
  console.log(`[${ts}]`, ...args);
}

export function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export function extractDeviceIdFromWsUrl(wsUrl) {
  const url = new URL(wsUrl);
  const marker = '/robots/ws/';
  const index = url.pathname.indexOf(marker);
  if (index < 0) {
    throw new Error(`Invalid robot WS url: ${wsUrl}`);
  }
  return decodeURIComponent(url.pathname.slice(index + marker.length));
}

export async function connectDeviceViaRest(wsUrl, armType) {
  const url = new URL(wsUrl);
  const base = `${url.protocol === 'wss:' ? 'https:' : 'http:'}//${url.host}`;
  const response = await fetch(`${base}/robots/connect`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      arm_type: armType,
      device_id: extractDeviceIdFromWsUrl(wsUrl),
    }),
  });

  const text = await response.text();
  let body;
  try {
    body = JSON.parse(text);
  } catch {
    body = text;
  }

  if (!response.ok) {
    throw new Error(`REST connect failed (${response.status}): ${JSON.stringify(body)}`);
  }
  return body;
}

export function resolveAgoraRtmScriptPath() {
  return path.join(__dirname, 'node_modules', 'agora-rtm', 'agora-rtm.js');
}

export function resolveAgoraRtcScriptPath() {
  const base = path.join(__dirname, 'node_modules', 'agora-rtc-sdk-ng');
  const candidates = [
    path.join(base, 'AgoraRTC_N-production.js'),
    path.join(base, 'AgoraRTC_N.js'),
    path.join(base, 'AgoraRTC_N-4.23.0.js'),
    path.join(base, 'AgoraRTC_N-4.23.1.js'),
    path.join(base, 'AgoraRTC_N-4.24.0.js'),
  ];
  for (const candidate of candidates) {
    if (fs.existsSync(candidate)) {
      return candidate;
    }
  }
  throw new Error(`AgoraRTC script not found. Ensure agora-rtc-sdk-ng is installed in ${base}`);
}

export async function createBrowserHostServer() {
  const html = '<!doctype html><html><head><meta charset="utf-8"></head><body></body></html>';
  const server = http.createServer((req, res) => {
    res.writeHead(200, {
      'Content-Type': 'text/html; charset=utf-8',
      'Cache-Control': 'no-store',
    });
    res.end(html);
  });

  await new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(0, '127.0.0.1', resolve);
  });

  const address = server.address();
  if (!address || typeof address === 'string') {
    throw new Error('Failed to determine browser host server address');
  }

  return {
    url: `http://127.0.0.1:${address.port}/`,
    async close() {
      await new Promise((resolve, reject) => {
        server.close((error) => {
          if (error) reject(error);
          else resolve();
        });
      });
    },
  };
}
