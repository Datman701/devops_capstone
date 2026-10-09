#!/usr/bin/env node
/**
 * End-to-end smoke test through the real UI: books an appointment using only
 * DOM interactions, then asserts it exists via the REST API.
 */

const WEB = process.env.WEB ?? 'http://127.0.0.1:5173';
const API = process.env.API ?? 'http://127.0.0.1:8000';
const PORT = 9700 + Math.floor(Math.random() * 200);

// Unique per run so repeated runs cannot match a row left by an earlier run.
const MARKER = `UI smoke ${new Date().toISOString()}`;

const before = await (await fetch(`${API}/api/appointments/stats`)).json();

const { spawn } = await import('node:child_process');
const { setTimeout: sleep } = await import('node:timers/promises');

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
  await send('Page.navigate', { url: `${WEB}/appointments` });
  await sleep(4000);

  // Open the booking modal.
  await send('Runtime.evaluate', {
    expression: `[...document.querySelectorAll('button.btn--primary')]
      .find((b) => b.offsetParent !== null).click()`,
  });
  await sleep(2500);

  // Pick one of the live free slots, type a reason, submit.
  const outcome = await send('Runtime.evaluate', {
    awaitPromise: true,
    returnByValue: true,
    expression: `(async () => {
      const slotButton = [...document.querySelectorAll('.modal button.btn--sm')]
        .find((b) => /\\d{1,2}:\\d{2}/.test(b.textContent));
      if (!slotButton) return 'NO_FREE_SLOT_BUTTON';
      slotButton.click();
      await new Promise((r) => setTimeout(r, 1200));

      const reason = document.querySelector('#modal-reason');
      const setter = Object.getOwnPropertyDescriptor(
        window.HTMLInputElement.prototype, 'value',
      ).set;
      setter.call(reason, ${JSON.stringify(MARKER)});
      reason.dispatchEvent(new Event('input', { bubbles: true }));
      await new Promise((r) => setTimeout(r, 400));

      const form = reason.closest('form');
      form.requestSubmit();
      await new Promise((r) => setTimeout(r, 2500));

      // Surface any in-modal error banner (e.g. the 409 slot-conflict message).
      const banner = document.querySelector('.modal .form-error');
      return JSON.stringify({ submitted: true, error: banner?.textContent ?? null });
    })()`,
  });
  console.log('form flow:', outcome.result.value);

  await sleep(2000);
  const after = await (await fetch(`${API}/api/appointments/stats`)).json();
  const created = await (await fetch(
    `${API}/api/appointments?limit=200`,
  )).json();
  const smoke = created.filter((a) => a.reason === MARKER);

  console.log(`marker:            ${MARKER}`);
  console.log(`appointments before: ${before.total}`);
  console.log(`appointments after:  ${after.total}`);
  console.log(`rows written via UI: ${smoke.length}`);
  if (smoke[0]) {
    console.log(
      `  -> #${smoke[0].id} ${smoke[0].patient.full_name} with ` +
        `${smoke[0].doctor.full_name} at ${smoke[0].scheduled_at}`,
    );
  }

  const ok = smoke.length === 1 && after.total === before.total + 1;
  console.log(
    ok
      ? 'PASS: exactly one appointment created through the UI and persisted to PostgreSQL'
      : 'FAIL: expected exactly one new appointment',
  );
  process.exitCode = ok ? 0 : 1;
} finally {
  socket?.close();
  chrome.kill('SIGKILL');
}