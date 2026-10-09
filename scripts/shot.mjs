#!/usr/bin/env node
/**
 * Minimal Chrome DevTools Protocol driver used for local smoke testing:
 * opens a page, optionally clicks a button, waits, then writes a screenshot.
 *
 * Usage: node scripts/shot.mjs <url> <output.png> [clickSelector] [waitMs]
 */

import { spawn } from 'node:child_process';
import { writeFileSync } from 'node:fs';
import { setTimeout as sleep } from 'node:timers/promises';

const [url, output, clickSelector, waitMsArg] = process.argv.slice(2);
const waitMs = Number(waitMsArg ?? 3500);
const PORT = 9222 + Math.floor(Math.random() * 500);

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
  for (let attempt = 0; attempt < 60; attempt += 1) {
    try {
      const response = await fetch(`http://127.0.0.1:${PORT}/json/list`);
      const targets = await response.json();
      const page = targets.find((t) => t.type === 'page');
      if (page) return page;
    } catch {
      /* browser not ready yet */
    }
    await sleep(250);
  }
  throw new Error('chromium devtools endpoint never became ready');
}

let socket;
let nextId = 1;
const pending = new Map();

function send(method, params = {}) {
  const id = nextId++;
  socket.send(JSON.stringify({ id, method, params }));
  return new Promise((resolve, reject) => pending.set(id, { resolve, reject }));
}

try {
  const target = await getTarget();
  socket = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => {
    socket.onopen = resolve;
    socket.onerror = reject;
  });

  socket.onmessage = (event) => {
    const message = JSON.parse(event.data);
    if (message.id && pending.has(message.id)) {
      const { resolve, reject } = pending.get(message.id);
      pending.delete(message.id);
      message.error ? reject(new Error(message.error.message)) : resolve(message.result);
    }
  };

  await send('Page.enable');
  await send('Runtime.enable');
  await send('Emulation.setDeviceMetricsOverride', {
    width: 1440,
    height: 1000,
    deviceScaleFactor: 1,
    mobile: false,
  });

  await send('Page.navigate', { url });
  await sleep(waitMs);

  if (clickSelector) {
    const result = await send('Runtime.evaluate', {
      expression: `(() => {
        const nodes = [...document.querySelectorAll(${JSON.stringify(clickSelector)})];
        const target = nodes.find((n) => n.offsetParent !== null) ?? nodes[0];
        if (!target) return 'NOT_FOUND';
        target.click();
        return 'CLICKED';
      })()`,
      returnByValue: true,
    });
    console.log(`click ${clickSelector}: ${result.result.value}`);
    await sleep(waitMs);
  }

  const errors = await send('Runtime.evaluate', {
    expression: 'JSON.stringify(window.__errors ?? [])',
    returnByValue: true,
  });

  const shot = await send('Page.captureScreenshot', { format: 'png' });
  writeFileSync(output, Buffer.from(shot.data, 'base64'));
  console.log(`wrote ${output}; page errors: ${errors.result.value}`);
} finally {
  socket?.close();
  chrome.kill('SIGKILL');
}