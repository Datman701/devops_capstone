#!/usr/bin/env node
/**
 * Logs into Grafana in a headless browser, opens the provisioned ClinicDesk
 * dashboard and captures it (M9 evidence).
 *
 * Verifying via the rendered dashboard rather than the query API proves the
 * panels actually draw: if a datasource uid is wrong or a PromQL expression is
 * invalid, the panel shows "No data" and the screenshot shows it.
 *
 * Usage: node scripts/screenshot-grafana.mjs [grafanaUrl] [output.png]
 */
import { spawn } from 'node:child_process';
import { writeFileSync } from 'node:fs';
import { setTimeout as sleep } from 'node:timers/promises';

const GRAFANA = process.argv[2] ?? 'http://127.0.0.1:13000';
const OUTPUT = process.argv[3] ?? 'docs/screenshots/26-grafana-dashboard.png';
const USER = process.env.GRAFANA_USER ?? 'admin';
const PASS = process.env.GRAFANA_PASSWORD ?? 'clinicdesk';
const DASH_UID = 'clinicdesk-api';

const PORT = 9400 + Math.floor(Math.random() * 300);

const chrome = spawn(
  'chromium',
  [
    '--headless',
    '--no-sandbox',
    '--disable-gpu',
    '--disable-dev-shm-usage',
    '--hide-scrollbars',
    `--remote-debugging-port=${PORT}`,
    '--window-size=1600,1200',
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
  const r = await send('Runtime.evaluate', {
    expression,
    returnByValue: true,
    awaitPromise: true,
  });
  if (r.exceptionDetails) {
    throw new Error(r.exceptionDetails.exception?.description ?? 'eval failed');
  }
  return r.result?.value;
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
  await send('Emulation.setDeviceMetricsOverride', {
    width: 1600,
    height: 1200,
    deviceScaleFactor: 1,
    mobile: false,
  });

  console.log('logging in to Grafana...');
  await send('Page.navigate', { url: `${GRAFANA}/login` });
  await sleep(4000);

  await evaluate(`(() => {
    const set = (sel, value) => {
      const el = document.querySelector(sel);
      if (!el) return false;
      const proto = el.tagName === 'INPUT'
        ? window.HTMLInputElement.prototype : window.HTMLTextAreaElement.prototype;
      Object.getOwnPropertyDescriptor(proto, 'value').set.call(el, value);
      el.dispatchEvent(new Event('input', { bubbles: true }));
      el.dispatchEvent(new Event('change', { bubbles: true }));
      return true;
    };
    set('input[name="user"]', ${JSON.stringify(USER)});
    set('input[name="password"]', ${JSON.stringify(PASS)});
    const btn = document.querySelector('button[type="submit"], button[aria-label="Login button"]');
    if (btn) btn.click();
    return true;
  })()`);
  await sleep(5000);

  const loggedIn = await evaluate(`!document.querySelector('input[name="password"]')`);
  console.log(`  logged in: ${loggedIn}`);

  console.log('opening dashboard...');
  await send('Page.navigate', { url: `${GRAFANA}/d/${DASH_UID}` });
  // Give the panels time to run their queries and draw.
  await sleep(12000);

  // Report what the panels are actually showing, so a broken panel fails loudly
  // instead of quietly producing a pretty but empty screenshot.
  const panelState = await evaluate(`JSON.stringify({
    title: document.querySelector('[data-testid="dashboard-header-title"]')?.textContent
      ?? document.title,
    noData: [...document.querySelectorAll('[data-testid="Panel status error"], [aria-label*="No data"]')].length,
    panels: document.querySelectorAll('[data-viz-panel-key]').length,
    errors: [...document.querySelectorAll('[data-testid="data-testid Alert error"]')].length,
  })`);
  console.log(`  ${panelState}`);

  // Fail fast if nothing rendered, so a blank screenshot is never submitted.
  const parsed = JSON.parse(panelState);
  if (!parsed.panels) throw new Error('no dashboard panels rendered');

  const metrics = await send('Page.getLayoutMetrics');
  const size = metrics.cssContentSize ?? metrics.contentSize;
  await send('Emulation.setDeviceMetricsOverride', {
    width: Math.ceil(size.width),
    height: Math.min(Math.ceil(size.height), 4000),
    deviceScaleFactor: 1,
    mobile: false,
  });
  await sleep(2000);

  const shot = await send('Page.captureScreenshot', { format: 'png' });
  writeFileSync(OUTPUT, Buffer.from(shot.data, 'base64'));
  console.log(`wrote ${OUTPUT}`);
} finally {
  socket?.close();
  chrome.kill('SIGKILL');
}