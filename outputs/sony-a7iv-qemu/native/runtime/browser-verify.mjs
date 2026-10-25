#!/usr/bin/env node
/* Drive the loopback camera panel with a real local Chrome over CDP.
 * No MCP dependency. Captures page screenshots plus the raw QEMU scanout
 * (frame.png) around each action, and can watch scanout changes over time.
 *
 * Usage:
 *   node browser-verify.mjs --url http://localhost:18764/<token>/ \
 *     --actions FN,MENU,PLAY --watch 5 --out evidence/browser-run
 */
import { spawn } from 'node:child_process';
import { createHash } from 'node:crypto';
import { mkdtemp, mkdir, rm, writeFile } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';

const CHROME = process.env.CHROME_PATH ||
  'C:/Program Files/Google/Chrome/Application/chrome.exe';

function arg(name, fallback = undefined) {
  const prefix = `--${name}=`;
  const index = process.argv.findIndex(v => v === `--${name}` || v.startsWith(prefix));
  if (index < 0) return fallback;
  const found = process.argv[index];
  if (found.startsWith(prefix)) return found.slice(prefix.length);
  const next = process.argv[index + 1];
  if (next !== undefined && !next.startsWith('--')) return next;
  return true;
}

const url = arg('url');
if (!url) {
  console.error('browser-verify: --url is required');
  process.exit(2);
}
const outDir = path.resolve(arg('out', 'browser-verify-out'));
const actions = String(arg('actions', '')).split(',').map(v => v.trim()).filter(Boolean);
const videoUrl = arg('video', '');
const videoFile = arg('file', '');
const photoCapture = arg('photo', false);
const audioCheck = arg('audio', false);
const shutterCheck = arg('shutter', false);
const shutterFile = arg('shutter-file', '');
const watchSeconds = Number(arg('watch', 0));
const waitMs = Number(arg('wait', 700));
const port = Number(arg('port', 9333));
const width = Number(arg('width', 1200));
const height = Number(arg('height', 900));

const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
const sha256 = buffer => createHash('sha256').update(buffer).digest('hex');
const base = new URL(url);

async function getJson(route) {
  const response = await fetch(new URL(route, base), { cache: 'no-store' });
  if (!response.ok) throw new Error(`${route}: HTTP ${response.status}`);
  return response.json();
}

async function captureFrame(step) {
  const started = Date.now();
  const response = await fetch(new URL('frame.png', base), { cache: 'no-store' });
  if (!response.ok) throw new Error(`frame.png: HTTP ${response.status}`);
  const buffer = Buffer.from(await response.arrayBuffer());
  const file = path.join(outDir, `frame-${step}.png`);
  await writeFile(file, buffer);
  return { file, bytes: buffer.length, sha256: sha256(buffer), fetch_ms: Date.now() - started };
}

async function launchChrome(profile) {
  const child = spawn(CHROME, [
    '--headless=new',
    `--remote-debugging-port=${port}`,
    `--user-data-dir=${profile}`,
    `--window-size=${width},${height}`,
    '--no-first-run',
    '--no-default-browser-check',
    '--disable-background-networking',
    '--disable-component-update',
    '--disable-renderer-backgrounding',
    '--hide-scrollbars',
    url,
  ], { stdio: ['ignore', 'pipe', 'pipe'] });
  let stderr = '';
  child.stderr.on('data', chunk => { stderr = (stderr + chunk).slice(-8192); });
  const deadline = Date.now() + 30000;
  while (Date.now() < deadline) {
    try {
      const list = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
      const page = list.find(t => t.type === 'page' && t.url.startsWith('http'));
      if (page?.webSocketDebuggerUrl) return { child, page, stderr: () => stderr };
    } catch {}
    if (child.exitCode !== null) throw new Error(`Chrome exited (${child.exitCode}): ${stderr}`);
    await sleep(200);
  }
  throw new Error(`Chrome did not expose CDP: ${stderr}`);
}

async function connect(wsUrl) {
  const ws = new WebSocket(wsUrl);
  await new Promise((resolve, reject) => {
    ws.addEventListener('open', resolve, { once: true });
    ws.addEventListener('error', () => reject(new Error('CDP socket error')), { once: true });
  });
  let nextId = 1;
  const pending = new Map();
  const events = [];
  ws.addEventListener('message', event => {
    const message = JSON.parse(event.data);
    if (message.id) {
      const waiter = pending.get(message.id);
      if (!waiter) return;
      pending.delete(message.id);
      if (message.error) waiter.reject(new Error(JSON.stringify(message.error)));
      else waiter.resolve(message.result);
    } else {
      events.push(message);
    }
  });
  const send = (method, params = {}) => new Promise((resolve, reject) => {
    const id = nextId++;
    pending.set(id, { resolve, reject });
    ws.send(JSON.stringify({ id, method, params }));
  });
  return { ws, send, events };
}

async function evaluate(cdp, expression) {
  const result = await cdp.send('Runtime.evaluate', {
    expression, awaitPromise: true, returnByValue: true,
  });
  if (result.exceptionDetails) {
    throw new Error(result.exceptionDetails.exception?.description || 'evaluation failed');
  }
  return result.result.value;
}

async function waitPage(cdp) {
  const deadline = Date.now() + 45000;
  while (Date.now() < deadline) {
    try {
      const ready = await evaluate(cdp,
        'document.readyState === "complete" && !!document.querySelector("#state") && !!document.querySelector("#frame")');
      if (ready) return;
    } catch {}
    await sleep(250);
  }
  throw new Error('camera panel did not become ready');
}

async function screenshot(cdp, file) {
  const result = await cdp.send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false });
  const buffer = Buffer.from(result.data, 'base64');
  await writeFile(file, buffer);
  return { file, bytes: buffer.length, sha256: sha256(buffer) };
}

async function clickKey(cdp, key) {
  const rect = await evaluate(cdp, `(() => {
    const el = document.querySelector('[data-key=${JSON.stringify(key)}]');
    if (!el) return null;
    const r = el.getBoundingClientRect();
    return { x: r.x + r.width / 2, y: r.y + r.height / 2, disabled: el.disabled };
  })()`);
  if (!rect) throw new Error(`button ${key} not found`);
  if (rect.disabled) throw new Error(`button ${key} is disabled before click`);
  for (const type of ['mousePressed', 'mouseReleased']) {
    await cdp.send('Input.dispatchMouseEvent', {
      type, x: rect.x, y: rect.y, button: 'left', clickCount: 1,
    });
  }
  return rect;
}

async function clickSelector(cdp, selector) {
  const rect = await evaluate(cdp, `(() => {
    const el = document.querySelector(${JSON.stringify(selector)});
    if (!el) return null;
    const r = el.getBoundingClientRect();
    return { x: r.x + r.width / 2, y: r.y + r.height / 2, disabled: !!el.disabled };
  })()`);
  if (!rect) throw new Error(`element ${selector} not found`);
  if (rect.disabled) throw new Error(`element ${selector} is disabled before click`);
  for (const type of ['mousePressed', 'mouseReleased']) {
    await cdp.send('Input.dispatchMouseEvent', {
      type, x: rect.x, y: rect.y, button: 'left', clickCount: 1,
    });
  }
  return rect;
}

async function audioProbe(cdp) {
  return evaluate(cdp, `(() => ({
    ctx: typeof audioCtx === 'undefined' || !audioCtx ? 'missing' : audioCtx.state,
    enabled: typeof sysSoundOn === 'boolean' ? sysSoundOn : null,
    beeps: window.__beepCount || 0,
    label: document.querySelector('#sysSound')?.textContent || '',
  }))()`);
}

async function waitIdle(cdp, key, timeoutMs) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const state = await evaluate(cdp, `(() => {
      const el = document.querySelector('[data-key=${JSON.stringify(key)}]');
      return { disabled: el ? el.disabled : null, text: document.querySelector('#state')?.textContent || '',
        frame: document.querySelector('#frame')?.src || '' };
    })()`);
    if (state.disabled === false) return state;
    await sleep(250);
  }
  throw new Error(`timeout waiting for ${key} to finish`);
}

await mkdir(outDir, { recursive: true });
const profile = await mkdtemp(path.join(os.tmpdir(), 'a7m4-chrome-'));
let chrome;
let cdp;
const report = { url, started: new Date().toISOString(), actions: [], watch: [], errors: [] };
try {
  const launched = await launchChrome(profile);
  chrome = launched.child;
  cdp = await connect(launched.page.webSocketDebuggerUrl);
  await cdp.send('Page.enable');
  await cdp.send('Runtime.enable');
  await waitPage(cdp);
  report.status_before = await getJson('status.json');
  if (shutterCheck) {
    report.shutter_fetch = await evaluate(cdp, `(async () => {
      const r = await fetch('sounds/shutter-ka-sha-8k.wav', { cache: 'no-store' });
      const b = await r.arrayBuffer();
      return { status: r.status, bytes: b.byteLength, type: r.headers.get('content-type') };
    })()`);
    await evaluate(cdp, `(() => {
      const s = document.querySelector('#shutterSound');
      s.value = 'ka8';
      s.dispatchEvent(new Event('change'));
      return s.value;
    })()`);
    await sleep(1200);
    await clickSelector(cdp, '#testShutterSound');
    await sleep(800);
    report.shutter = await evaluate(cdp, `(() => ({
      ctx: audioCtx && audioCtx.state,
      select: document.querySelector('#shutterSound').value,
      label: document.querySelector('#shutterState').textContent,
      probe: window.__shutter,
    }))()`);
    if (!report.shutter_fetch || report.shutter_fetch.status !== 200 || report.shutter_fetch.bytes < 1000) {
      throw new Error(`shutter candidate fetch failed: ${JSON.stringify(report.shutter_fetch)}`);
    }
    if (!report.shutter.probe || report.shutter.probe.plays < 1) {
      throw new Error(`shutter candidate did not play: ${JSON.stringify(report.shutter)}`);
    }
    if (shutterFile) {
      const document = await cdp.send('DOM.getDocument', { depth: -1 });
      const input = await cdp.send('DOM.querySelector', {
        nodeId: document.root.nodeId, selector: '#shutterFile',
      });
      if (!input.nodeId) throw new Error('shutter file input not found');
      await cdp.send('DOM.setFileInputFiles', { nodeId: input.nodeId, files: [shutterFile] });
      await sleep(1800);
      report.shutter_custom = await evaluate(cdp, `(() => ({
        mode: window.__shutter.mode,
        plays: window.__shutter.plays,
        cached: window.__shutter.cached,
        select: document.querySelector('#shutterSound').value,
        label: document.querySelector('#shutterState').textContent,
      }))()`);
      if (report.shutter_custom.mode !== 'custom' || report.shutter_custom.plays < 2) {
        throw new Error(`custom shutter upload did not take effect: ${JSON.stringify(report.shutter_custom)}`);
      }
      report.page_shutter_custom = await screenshot(cdp, path.join(outDir, 'page-shutter-custom.png'));
    }
  }
  if (audioCheck) {
    report.audio_instrumented = await evaluate(cdp, `(() => {
      window.__beepCount = 0;
      const P = window.AudioContext || window.webkitAudioContext;
      if (!P || !P.prototype.createOscillator) return false;
      if (!P.prototype.__a7m4Patched) {
        const original = P.prototype.createOscillator;
        P.prototype.createOscillator = function () {
          const osc = original.call(this);
          const start = osc.start.bind(osc);
          osc.start = (...args) => { window.__beepCount += 1; return start(...args); };
          return osc;
        };
        P.prototype.__a7m4Patched = true;
      }
      return true;
    })()`);
    await clickSelector(cdp, '#sysSound');
    await sleep(300);
    await clickSelector(cdp, '#sysSound');
    await sleep(500);
    report.audio = await audioProbe(cdp);
    if (!report.audio_instrumented || report.audio.beeps < 1) {
      throw new Error(`system sound probe failed: ${JSON.stringify(report.audio)}`);
    }
  }
  if (videoFile) {
    const document = await cdp.send('DOM.getDocument', { depth: -1 });
    const input = await cdp.send('DOM.querySelector', {
      nodeId: document.root.nodeId, selector: '#videoFile',
    });
    if (!input.nodeId) throw new Error('video file input not found');
    await cdp.send('DOM.setFileInputFiles', { nodeId: input.nodeId, files: [videoFile] });
    const deadline = Date.now() + 180000;
    let media = { readyState: 0, videoWidth: 0, text: '' };
    while (Date.now() < deadline) {
      media = await evaluate(cdp, `(() => ({
        readyState: document.querySelector('#videoEl').readyState,
        videoWidth: document.querySelector('#videoEl').videoWidth,
        text: document.querySelector('#videoState').textContent,
      }))()`);
      if (media.text.includes('失败')) throw new Error(media.text);
      if (media.readyState >= 2 && media.videoWidth > 0) break;
      await sleep(500);
    }
    if (!(media.readyState >= 2 && media.videoWidth > 0)) {
      throw new Error(`video upload/transcode did not become playable: ${JSON.stringify(media)}`);
    }
    report.file_input = { path: videoFile, media };
    await sleep(1500);
  } else if (videoUrl) {
    await evaluate(cdp, `(async () => {
      const v = document.querySelector('#videoEl');
      v.src = ${JSON.stringify(videoUrl)};
      v.muted = true; v.loop = true;
      await v.play();
      return v.readyState;
    })()`);
    await sleep(1800);
  }

  if (photoCapture) {
    if (!videoFile && !videoUrl) throw new Error('--photo requires --file or --video');
    await evaluate(cdp, `document.querySelector('#shutter').click(); 'clicked'`);
    const photoDeadline = Date.now() + 600000;
    let photoState = '';
    while (Date.now() < photoDeadline) {
      photoState = await evaluate(cdp, `document.querySelector('#videoState').textContent`);
      if (photoState.includes('已写入虚拟卡') || photoState.includes('失败')) break;
      await sleep(500);
    }
    if (!photoState.includes('已写入虚拟卡')) throw new Error(`photo bridge failed: ${photoState}`);
    await evaluate(cdp, `document.querySelector('#playPhoto').click(); 'play'`);
    await sleep(2500);
    report.photo = { state: photoState };
    report.photo_playback = await evaluate(cdp, `(() => ({
      overlay: document.querySelector('#playOverlay').classList.contains('show'),
      display: getComputedStyle(document.querySelector('#playOverlay')).display,
      name: document.querySelector('.playTop span:nth-child(2)')?.textContent || '',
      count: document.querySelector('.playTop span:last-child')?.textContent || '',
      button: document.querySelector('#playPhoto').textContent,
      videoState: document.querySelector('#videoState').textContent,
    }))()`);
    if (audioCheck) report.audio_photo = await audioProbe(cdp);
    report.page_photo = await screenshot(cdp, path.join(outDir, 'page-photo-playback.png'));
    await clickSelector(cdp, '#playBack');
    await sleep(600);
    report.photo_return = await evaluate(cdp, `(() => ({
      overlay: document.querySelector('#playOverlay').classList.contains('show'),
      display: getComputedStyle(document.querySelector('#playOverlay')).display,
      button: document.querySelector('#playPhoto').textContent,
      videoState: document.querySelector('#videoState').textContent,
    }))()`);
    report.page_photo_return = await screenshot(cdp, path.join(outDir, 'page-photo-return.png'));
    if (!report.photo_playback.overlay || report.photo_return.overlay) {
      throw new Error(`playback overlay did not toggle: ${JSON.stringify({play: report.photo_playback, back: report.photo_return})}`);
    }
  }

  const initialFrame = await captureFrame('00-before');
  report.page_before = await screenshot(cdp, path.join(outDir, 'page-00-before.png'));
  report.initial = { frame: initialFrame, state: await evaluate(cdp, 'document.querySelector("#state").textContent') };

  let index = 0;
  for (const key of actions) {
    index += 1;
    const step = `${String(index).padStart(2, '0')}-${key.toLowerCase()}`;
    const startedAt = Date.now();
    try {
      const rect = await clickKey(cdp, key);
      const idle = await waitIdle(cdp, key, key === 'RESTART' ? 180000 : 30000);
      await sleep(waitMs);
      const frame = await captureFrame(step);
      const page = await screenshot(cdp, path.join(outDir, `page-${step}.png`));
      report.actions.push({
        key, rect, elapsed_ms: Date.now() - startedAt, state: idle.text,
        frame, page, changed_from_before: frame.sha256 !== initialFrame.sha256,
      });
    } catch (error) {
      report.errors.push({ key, error: String(error) });
      try { report.page_error = await screenshot(cdp, path.join(outDir, `page-error-${step}.png`)); } catch {}
      break;
    }
  }

  if (watchSeconds > 0) {
    const startedAt = Date.now();
    let previous = null;
    let samples = 0;
    while (Date.now() - startedAt < watchSeconds * 1000) {
      const frame = await captureFrame(`watch-${String(samples).padStart(4, '0')}`);
      report.watch.push({ t_ms: Date.now() - startedAt, sha256: frame.sha256, bytes: frame.bytes,
        changed: previous === null ? null : frame.sha256 !== previous });
      previous = frame.sha256;
      samples += 1;
      await sleep(500);
    }
    report.watch_summary = {
      samples, unique_sha256: new Set(report.watch.map(v => v.sha256)).size,
      changed_samples: report.watch.filter(v => v.changed).length,
      duration_ms: Date.now() - startedAt,
    };
  }

  report.status_after = await getJson('status.json');
  await sleep(1200);
  report.fw = await evaluate(cdp, 'window.__fw || null');
  if (audioCheck) report.audio_final = await audioProbe(cdp);
  report.final = {
    frame: await captureFrame('99-final'),
    page: await screenshot(cdp, path.join(outDir, 'page-99-final.png')),
    state: await evaluate(cdp, 'document.querySelector("#state").textContent'),
  };
  report.ok = report.errors.length === 0;
} catch (error) {
  report.errors.push({ fatal: String(error) });
  report.ok = false;
  process.exitCode = 1;
} finally {
  try { cdp?.ws.close(); } catch {}
  try { chrome?.kill(); } catch {}
  await sleep(300);
  try { await rm(profile, { recursive: true, force: true }); } catch {}
  report.finished = new Date().toISOString();
  const file = path.join(outDir, 'report.json');
  await writeFile(file, JSON.stringify(report, null, 2));
  console.log(JSON.stringify({ ok: report.ok, report: file,
    actions: report.actions.map(a => ({ key: a.key, frame: a.frame.sha256, changed: a.changed_from_before })),
    watch: report.watch_summary || null, errors: report.errors }, null, 2));
}
