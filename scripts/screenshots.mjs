#!/usr/bin/env node
/**
 * Captures the submission screenshots (M1, M4, M8, M10) in a single headless
 * Chromium session, so every image comes from one consistent browser run
 * against the Docker Compose stack.
 *
 * Usage: node scripts/screenshots.mjs [baseUrl] [outDir]
 */
import { spawn } from 'node:child_process';
import { mkdirSync, writeFileSync } from 'node:fs';
import { setTimeout as sleep } from 'node:timers/promises';

const BASE = process.argv[2] ?? 'http://127.0.0.1:3000';
const OUT = process.argv[3] ?? 'docs/screenshots';
const PORT = 9300 + Math.floor(Math.random() * 300);

mkdirSync(OUT, { recursive: true });

const chrome = spawn(
  'chromium',
  [
    '--headless',
    '--no-sandbox',
    '--disable-gpu',
    '--disable-dev-shm-usage',
    '--hide-scrollbars',
    `--remote-debugging-port=${PORT}`,
    '--window-size=1440,1000',
    'about:blank',
  ],
  { stdio: 'ignore' },
);

async function getTarget() {
  for (let i = 0; i < 60; i += 1) {
    try {
      const list = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json();
      const page = list.find((t) => t.type === 'page');
      if (page) return page;
    } catch { /* not ready */ }
    await sleep(250);
  }
  throw new Error('devtools never became ready');
}

let socket;
let nextId = 1;
const pending = new Map();
const send = (method, params = {}) => {
  const id = nextId++;
  socket.send(JSON.stringify({ id, method, params }));
  return new Promise((res, rej) => pending.set(id, { res, rej }));
};

const evaluate = async (expression) => {
  const r = await send('Runtime.evaluate', { expression, returnByValue: true });
  return r.result?.value;
};

const viewport = async (width, height) =>
  send('Emulation.setDeviceMetricsOverride', {
    width,
    height,
    deviceScaleFactor: 1,
    mobile: width < 700,
  });

async function shoot(name, { width = 1440, height = 1000, fullPage = true } = {}) {
  await viewport(width, height);
  await sleep(600);
  const params = { format: 'png' };
  if (fullPage) {
    const metrics = await send('Page.getLayoutMetrics');
    const size = metrics.cssContentSize ?? metrics.contentSize;
    params.captureBeyondViewport = true;
    params.clip = {
      x: 0,
      y: 0,
      width: Math.ceil(size.width),
      height: Math.min(Math.ceil(size.height), 3000),
      scale: 1,
    };
  }
  const shot = await send('Page.captureScreenshot', params);
  const file = `${OUT}/${name}.png`;
  writeFileSync(file, Buffer.from(shot.data, 'base64'));
  console.log(`  wrote ${file}`);
}

const go = async (path, wait = 3500) => {
  await send('Page.navigate', { url: `${BASE}${path}` });
  await sleep(wait);
};

try {
  const target = await getTarget();
  socket = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((res, rej) => { socket.onopen = res; socket.onerror = rej; });
  socket.onmessage = (event) => {
    const message = JSON.parse(event.data);
    if (message.id && pending.has(message.id)) {
      const { res, rej } = pending.get(message.id);
      pending.delete(message.id);
      message.error ? rej(new Error(message.error.message)) : res(message.result);
    }
  };
  await send('Page.enable');
  await send('Runtime.enable');
  await send('Network.enable');

  console.log('capturing application screenshots...');

  // M1 / M4: the running application, as served by nginx on :3000.
  await go('/', 4500);
  await shoot('01-dashboard');

  await go('/appointments', 4000);
  await shoot('02-appointments');

  // Apply a filter so the screenshot evidences the Apply filter control working.
  await evaluate(`(() => {
    const set = Object.getOwnPropertyDescriptor(
      window.HTMLSelectElement.prototype, 'value').set;
    const select = document.querySelector('#filter-status');
    set.call(select, 'scheduled');
    select.dispatchEvent(new Event('change', { bubbles: true }));
    return true;
  })()`);
  await sleep(800);
  await evaluate(`[...document.querySelectorAll('button')]
      .find((b) => /apply filter/i.test(b.textContent)).click()`);
  await sleep(2500);
  await shoot('03-appointments-filtered');

  await go('/doctors', 3500);
  await shoot('04-doctors');

  await go('/patients', 3500);
  await shoot('05-patients');

  // Booking modal, which also proves the API is reachable from the browser.
  await go('/appointments', 4000);
  await evaluate(`(() => {
    const btn = [...document.querySelectorAll('button')]
      .find((b) => /book appointment/i.test(b.textContent));
    if (!btn) return 'NOT_FOUND';
    btn.click();
    return 'CLICKED';
  })()`);
  await sleep(2500);
  await shoot('06-booking-modal');

  // Responsive check (M1: "responsive and usable UI").
  await go('/', 4500);
  await shoot('07-dashboard-mobile', { width: 414, height: 900 });

  await go('/appointments', 4000);
  await shoot('08-appointments-mobile', { width: 414, height: 900 });

  console.log('done');
} finally {
  socket?.close();
  chrome.kill('SIGKILL');
}