#!/usr/bin/env node
/**
 * Renders captured terminal output to a PNG styled like a terminal, so command
 * transcripts can be submitted as screenshots (the rubric asks for terminal
 * output evidence for pytest, docker compose, Trivy and git history).
 *
 * Usage: node scripts/render-terminal.mjs <input.txt> <output.png> [title]
 */
import { spawn } from 'node:child_process';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname } from 'node:path';
import { setTimeout as sleep } from 'node:timers/promises';

const [input, output, title = 'Terminal'] = process.argv.slice(2);
if (!input || !output) {
  console.error('usage: render-terminal.mjs <input.txt> <output.png> [title]');
  process.exit(1);
}

const raw = readFileSync(input, 'utf8').replace(/\s+$/, '');
const lines = raw.split('\n');

// Keep the capture readable: long transcripts are trimmed from the middle,
// with a marker so nothing looks silently missing.
const MAX_LINES = 52;
let shown = lines;
let trimmed = 0;
if (lines.length > MAX_LINES) {
  const head = Math.ceil(MAX_LINES * 0.65);
  const tail = MAX_LINES - head - 1;
  shown = [
    ...lines.slice(0, head),
    `  ... ${lines.length - head - tail} lines omitted ...`,
    ...lines.slice(lines.length - tail),
  ];
  trimmed = lines.length;
}

const esc = (s) =>
  s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

// Basic ANSI colouring so PASS/FAIL, warnings and totals stand out.
function colour(line) {
  const e = esc(line);
  if (/^\s*(PASS|✓|✅)/i.test(line)) return `<span class="ok">${e}</span>`;
  if (/^\s*(FAIL|ERROR|✗|❌)/i.test(line)) return `<span class="bad">${e}</span>`;
  if (/warning|deprecat/i.test(line)) return `<span class="warn">${e}</span>`;
  if (/\b\d+ passed\b|\bTotal: 0\b|0 vulnerabilities|healthy/i.test(line))
    return `<span class="ok">${e}</span>`;
  if (/^\$ /.test(line)) return `<span class="cmd">${e}</span>`;
  return e;
}

const html = `<!doctype html>
<html><head><meta charset="utf-8">
<style>
  * { box-sizing: border-box; }
  body {
    margin: 0;
    padding: 28px;
    background: #0d1117;
    font-family: ui-monospace, "DejaVu Sans Mono", "Liberation Mono", Menlo, monospace;
  }
  .window {
    border: 1px solid #30363d;
    border-radius: 10px;
    overflow: hidden;
    background: #0d1117;
    box-shadow: 0 12px 40px rgba(0,0,0,.45);
  }
  .titlebar {
    display: flex; align-items: center; gap: 8px;
    padding: 10px 14px;
    background: #161b22;
    border-bottom: 1px solid #30363d;
  }
  .dot { width: 12px; height: 12px; border-radius: 50%; }
  .t { margin-left: 10px; color: #8b949e; font-size: 12px; }
  pre {
    margin: 0;
    padding: 18px 20px;
    color: #c9d1d9;
    font-size: 13px;
    line-height: 1.5;
    white-space: pre-wrap;
    word-break: break-word;
  }
  .ok   { color: #3fb950; }
  .bad  { color: #f85149; }
  .warn { color: #d29922; }
  .cmd  { color: #79c0ff; font-weight: 600; }
</style></head>
<body>
  <div class="window">
    <div class="titlebar">
      <span class="dot" style="background:#ff5f57"></span>
      <span class="dot" style="background:#febc2e"></span>
      <span class="dot" style="background:#28c840"></span>
      <span class="t">${esc(title)}</span>
    </div>
    <pre>${shown.map(colour).join('\n')}</pre>
  </div>
</body></html>`;

mkdirSync(dirname(output), { recursive: true });

const PORT = 9600 + Math.floor(Math.random() * 200);
const chrome = spawn(
  'chromium',
  [
    '--headless',
    '--no-sandbox',
    '--disable-gpu',
    '--disable-dev-shm-usage',
    '--hide-scrollbars',
    `--remote-debugging-port=${PORT}`,
    '--window-size=1500,900',
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

  const dataUrl = `data:text/html;charset=utf-8,${encodeURIComponent(html)}`;
  await send('Page.navigate', { url: dataUrl });
  await sleep(1200);

  const metrics = await send('Page.getLayoutMetrics');
  const size = metrics.cssContentSize ?? metrics.contentSize;
  await send('Emulation.setDeviceMetricsOverride', {
    width: Math.ceil(size.width),
    height: Math.ceil(size.height),
    deviceScaleFactor: 1,
    mobile: false,
  });
  await sleep(400);

  const shot = await send('Page.captureScreenshot', { format: 'png' });
  writeFileSync(output, Buffer.from(shot.data, 'base64'));
  console.log(`wrote ${output} (${trimmed || raw.split('\n').length} source lines)`);
} finally {
  socket?.close();
  chrome.kill('SIGKILL');
}