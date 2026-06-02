#!/usr/bin/env node
const fs = require('fs');
const path = require('path');

const RESET = '\x1b[0m';
const BOLD = '\x1b[1m';
const RED = '\x1b[38;2;255;111;111m';
const GREEN = '\x1b[38;2;183;242;76m';
const YELLOW = '\x1b[38;2;255;190;130m';
const MAGENTA = '\x1b[38;2;255;160;255m';
const CYAN = '\x1b[38;2;120;210;255m';
const CREAM = '\x1b[38;2;255;238;200m';
const GRAY = '\x1b[38;2;205;205;205m';
const SOFT = '\x1b[38;2;105;115;120m';

function s(text, ...styles) {
  const value = String(text || '');
  return value ? styles.join('') + value + RESET : value;
}

function get(obj, path, fallback = '') {
  let cur = obj;
  for (const key of path) {
    if (!cur || typeof cur !== 'object') return fallback;
    cur = cur[key];
  }
  return cur == null ? fallback : cur;
}

function short(value, max) {
  const text = String(value || '').trim();
  return text.length <= max ? text : text.slice(0, Math.max(0, max - 1)) + '…';
}

function middleShort(value, max) {
  const text = String(value || '').trim();
  if (text.length <= max) return text;
  if (max <= 1) return text.slice(0, max);
  const head = Math.ceil((max - 1) * 0.6);
  const tail = Math.max(0, max - 1 - head);
  return text.slice(0, head) + '…' + (tail ? text.slice(-tail) : '');
}

function usedPct(data) {
  const raw = Number(get(data, ['context', 'usedPercent'], 0));
  return Math.max(0, Math.min(100, Number.isFinite(raw) ? Math.round(raw) : 0));
}

function ctxStyle(used) {
  if (used >= 75) return RED;
  if (used >= 50) return YELLOW;
  return GREEN;
}

function ctxBar(used) {
  const filled = Math.max(0, Math.min(10, Math.round(used / 10)));
  const color = ctxStyle(used);
  return s('▰'.repeat(filled), color) + s('▱'.repeat(10 - filled), SOFT);
}

function runState(text) {
  const state = short(text || 'Ready', 12);
  const key = state.toLowerCase();
  if (['blocked', 'error', 'failed'].includes(key)) return s(state, RED, BOLD);
  if (['working', 'running', 'thinking'].includes(key)) return s(state, RED);
  return s(state, RED);
}

function permissions(data) {
  const permissions = String(get(data, ['status', 'permissions'], ''));
  const approval = String(get(data, ['status', 'approvalMode'], ''));
  const text = permissions || approval || '';
  const key = `${permissions} ${approval}`.toLowerCase();
  if (key.includes('yolo') || key.includes('never') || key.includes('danger')) {
    return s(short(text || 'YOLO', 12), MAGENTA, BOLD);
  }
  return s(short(text, 14), GRAY);
}

function normalizeStatus(status) {
  const key = String(status || '').trim();
  return ({
    pendingInit: 'pending',
    pending_init: 'pending',
    running: 'run',
    completed: 'done',
    errored: 'err',
    interrupted: 'int',
    shutdown: 'off',
    notFound: 'lost',
    not_found: 'lost',
  })[key] || key.toLowerCase() || 'unknown';
}

function agentLabel(item) {
  if (!item || typeof item !== 'object') return '';
  const name = String(item.name || 'Agent').trim();
  const role = String(item.role || '').trim();
  return role ? `${name} [${role}]` : name;
}

function findUp(start, name) {
  let dir = path.resolve(String(start || process.cwd()));
  while (true) {
    const candidate = path.join(dir, name);
    if (fs.existsSync(candidate)) return candidate;
    const parent = path.dirname(dir);
    if (parent === dir) return '';
    dir = parent;
  }
}

function readJson(file) {
  try {
    return JSON.parse(fs.readFileSync(file, 'utf8'));
  } catch (_) {
    return null;
  }
}

function statusColor(status) {
  const key = String(status || '').toLowerCase();
  if (key === 'planning') return YELLOW;
  if (key === 'in_progress') return GREEN;
  if (key === 'completed' || key === 'done') return GRAY;
  if (key === 'blocked' || key === 'failed') return RED;
  return CYAN;
}

function trellisSegment(data) {
  const cwd = get(data, ['workspace', 'cwd'], process.cwd());
  const trellisDir = findUp(cwd, '.trellis');
  if (!trellisDir) return '';

  const sessionsDir = path.join(trellisDir, '.runtime', 'sessions');
  let sessionFiles = [];
  try {
    sessionFiles = fs
      .readdirSync(sessionsDir)
      .filter((name) => name.endsWith('.json'))
      .map((name) => path.join(sessionsDir, name))
      .sort((a, b) => fs.statSync(b).mtimeMs - fs.statSync(a).mtimeMs);
  } catch (_) {
    return '';
  }

  for (const sessionFile of sessionFiles) {
    const session = readJson(sessionFile);
    const taskRef = session && typeof session.current_task === 'string' ? session.current_task : '';
    if (!taskRef) continue;

    const repoRoot = path.dirname(trellisDir);
    const taskDir = path.isAbsolute(taskRef) ? taskRef : path.join(repoRoot, taskRef);
    const task = readJson(path.join(taskDir, 'task.json'));
    if (!task || typeof task !== 'object') continue;

    const current = path.basename(taskDir);
    const status = String(task.status || 'unknown');
    const priority = String(task.priority || '').trim();
    const assignee = String(task.assignee || task.creator || '').trim();
    const bits = [
      s(status, statusColor(status)),
      priority ? s(priority, MAGENTA) : '',
      assignee ? s(assignee, CYAN) : '',
      s(current, CREAM),
    ].filter(Boolean);
    return bits.join(s(' · ', GRAY));
  }

  return '';
}

function agentsLine(data, branch) {
  const agents = get(data, ['agents'], {});
  const items = Array.isArray(agents.items) ? agents.items : [];
  const counts = {};
  for (const item of items) {
    const key = normalizeStatus(item && item.status);
    counts[key] = (counts[key] || 0) + 1;
  }

  const total = Number.isInteger(agents.total) ? agents.total : items.length;
  const parts = [];
  const trellis = trellisSegment(data);
  if (trellis) {
    parts.push(trellis);
  }

  if (total > 0) {
    const bits = [];
    if (counts.run) bits.push(`${s(counts.run, BOLD)} run`);
    if (counts.pending) bits.push(`${s(counts.pending, CYAN)} wait`);
    if (counts.done) bits.push(`${s(counts.done, GREEN)} done`);
    const failures = (counts.err || 0) + (counts.int || 0) + (counts.lost || 0);
    if (failures) bits.push(`${s(failures, RED, BOLD)} err`);
    if (!bits.length) bits.push(s('idle', GRAY));
    parts.push(`${s('agents', GREEN)} ${total}: ${bits.join(s(' / ', GRAY))}`);
    const current =
      String(agents.current || '').trim() ||
      agentLabel(items.find((item) => normalizeStatus(item && item.status) === 'run'));
    if (current) parts.push(s(short(current, 28), BOLD));
  } else {
    parts.push(`${s('agents', GREEN)} ${s('0', GREEN)}`);
  }

  const left = `  ${parts.join(` ${s('|', GRAY)} `)}`;
  if (!branch) return left;
  return `${left} ${s('·', GRAY)} ${s(middleShort(branch, 42), CYAN)}`;
}

let data = {};
try {
  const input = fs.readFileSync(0, 'utf8');
  data = input.trim() ? JSON.parse(input) : {};
} catch (_) {}

const used = usedPct(data);
const modelName = String(get(data, ['model', 'displayName'], get(data, ['model', 'id'], 'codex')) || '').trim();
const reasoningEffort = String(get(data, ['model', 'reasoningEffort'], '') || '').trim();
const model = short(
  reasoningEffort && !modelName.toLowerCase().includes(reasoningEffort.toLowerCase())
    ? `${modelName} ${reasoningEffort}`
    : modelName,
  26,
);
const state = get(data, ['status', 'runState'], 'Ready');
const currentDirRaw = get(data, ['workspace', 'currentDir'], process.cwd().split('/').pop());
const branch = String(get(data, ['git', 'branch'], '') || '').trim();
const firstLeft = [
  s(model, BOLD),
  permissions(data),
  runState(state),
  `ctx ${s(`${used}%`, ctxStyle(used))} [${ctxBar(used)}]`,
  s(middleShort(currentDirRaw, 42), CREAM),
].filter(Boolean).join(` ${s('·', GRAY)} `);

console.log(firstLeft);
console.log(agentsLine(data, branch));
