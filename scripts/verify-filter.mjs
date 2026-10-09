#!/usr/bin/env node
/**
 * Verifies the appointments filter uses an explicit "Apply filter" button:
 * changing a control must NOT trigger a request, and clicking Apply must
 * trigger exactly one request carrying the chosen filter.
 */
import { spawn } from 'node:child_process';
import { setTimeout as sleep } from 'node:timers/promises';

const WEB = process.env.WEB ?? 'http://127.0.0.1:5173';
const PORT = 9800 + Math.floor(Math.random() * 150);

const chrome = spawn(
  'chromium',
  [
    '--headless',
    '--no-sandbox',
    '--disable-gpu',
    '--disable-dev-shm-usage',
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
  const result = await send('Runtime.evaluate', {
    expression,
    returnByValue: true,
  });
  if (result.exceptionDetails) {
    throw new Error(result.exceptionDetails.exception?.description ?? 'eval failed');
  }
  return result.result.value;
};

const failures = [];
const check = (label, ok, detail) => {
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${label}${detail ? ` (${detail})` : ''}`);
  if (!ok) failures.push(label);
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

  // Count every /api/appointments request the page makes.
  await send('Network.enable');
  let appointmentCalls = [];
  socket.addEventListener('message', (event) => {
    const message = JSON.parse(event.data);
    if (message.method === 'Network.requestWillBeSent') {
      const url = message.params.request.url;
      if (url.includes('/api/appointments')) appointmentCalls.push(url);
    }
  });

  await send('Page.navigate', { url: `${WEB}/appointments` });
  await sleep(5000);

  const onLoad = appointmentCalls.length;
  // React StrictMode double-invokes effects in development, so each fetch runs
  // twice. The bug this guards against was an unbounded refetch loop, so assert
  // on a tight bound rather than an exact count.
  check('no request storm on load', onLoad <= 4, `${onLoad} request(s)`);

  const hasButton = await evaluate(
    `!![...document.querySelectorAll('button')]
       .find((b) => /apply filter/i.test(b.textContent) && b.offsetParent !== null)`,
  );
  check('Apply filter button is rendered', hasButton === true);

  const disabledBefore = await evaluate(
    `[...document.querySelectorAll('button')]
       .find((b) => /apply filter/i.test(b.textContent)).disabled`,
  );
  check('Apply disabled while filters are clean', disabledBefore === true);

  // Change a filter WITHOUT applying.
  appointmentCalls = [];
  await evaluate(`(() => {
    const select = document.querySelector('#filter-status');
    const setter = Object.getOwnPropertyDescriptor(
      window.HTMLSelectElement.prototype, 'value').set;
    setter.call(select, 'confirmed');
    select.dispatchEvent(new Event('change', { bubbles: true }));
  })()`);
  await sleep(2000);
  check(
    'changing a filter does not refetch',
    appointmentCalls.length === 0,
    `${appointmentCalls.length} request(s)`,
  );

  const disabledAfter = await evaluate(
    `[...document.querySelectorAll('button')]
       .find((b) => /apply filter/i.test(b.textContent)).disabled`,
  );
  check('Apply enabled once a filter changed', disabledAfter === false);

  await evaluate(`[...document.querySelectorAll('button')]
      .find((b) => /apply filter/i.test(b.textContent)).click()`);
  await sleep(2500);
  const applied = appointmentCalls.filter((u) => u.includes('status=confirmed')).length;
  check('Apply triggers one filtered request', applied === 1, `${applied} request(s)`);

  // Reset should clear both draft and applied filters.
  appointmentCalls = [];
  await evaluate(`[...document.querySelectorAll('button')]
      .find((b) => b.textContent.trim() === 'Reset' && b.offsetParent !== null).click()`);
  await sleep(2000);
  const afterReset = appointmentCalls.filter((u) => !u.includes('status=')).length;
  check('Reset clears the applied filter', afterReset >= 1, `${afterReset} request(s)`);

  const resetValue = await evaluate(`document.querySelector('#filter-status').value`);
  check('Reset clears the dropdown', resetValue === '', `value="${resetValue}"`);
} finally {
  socket?.close();
  chrome.kill('SIGKILL');
}

if (failures.length) {
  console.error(`\n${failures.length} check(s) failed`);
  process.exit(1);
}
console.log('\nAll filter checks passed');