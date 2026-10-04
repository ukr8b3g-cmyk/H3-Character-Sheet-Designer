/** Semantic state only. Layout, dimensions and prompt compilation stay in Python. */
export const VIEW_IDS = Object.freeze(['face_front', 'face_left', 'body_front', 'body_left', 'body_back', 'hands', 'feet']);
export const PART_IDS = Object.freeze(['head_hair', 'face', 'upper_clothing', 'back_clothing', 'lower_body', 'hands', 'footwear', 'other']);
export const PART_PROMPT_MAX_LENGTH = 1000; // UTF-16 code units, matching textarea maxlength.
export const PRESETS = Object.freeze({
  basic: ['face_front', 'body_front', 'body_left', 'body_back'], detail: [...VIEW_IDS], turnaround: ['body_front', 'body_left', 'body_back'], single: ['body_front'],
});
export const DEFAULT_STATE = Object.freeze({schema_version: 1, views: PRESETS.basic, size: Object.freeze({mode: 'auto', body_height: 1120, manual_width: 2240, manual_height: 1280})});
export const DEFAULT_JSON = JSON.stringify(DEFAULT_STATE);
export const MAX_BYTES = 64 * 1024;
export class StateError extends Error {
  constructor(code, detail = '') { super(detail ? `${code}: ${detail}` : code); this.code = code; this.detail = detail; }
}
const fail = (code, detail) => { throw new StateError(code, detail); };

// JSON.parse silently discards duplicate object keys. This small strict reader does not.
export function parseJSONStrict(raw) {
  if (typeof raw !== 'string') fail('string');
  if (new TextEncoder().encode(raw).length > MAX_BYTES) fail('oversize');
  let cursor = 0;
  const ws = () => { while (/[\x20\t\r\n]/.test(raw[cursor] ?? '\0')) cursor++; };
  const string = () => {
    const start = cursor++;
    while (cursor < raw.length) {
      if (raw[cursor] === '\\') { cursor += 2; continue; }
      if (raw[cursor++] === '"') {
        try { return JSON.parse(raw.slice(start, cursor)); } catch { fail('json'); }
      }
    }
    fail('json');
  };
  const value = (depth = 0) => {
    if (depth > 32) fail('json');
    ws();
    const c = raw[cursor];
    if (c === '"') return string();
    if (c === '{') {
      cursor++; ws(); const object = Object.create(null); const keys = new Set();
      if (raw[cursor] === '}') { cursor++; return object; }
      while (cursor < raw.length) {
        ws(); if (raw[cursor] !== '"') fail('json');
        const key = string(); if (keys.has(key)) fail('duplicateKey', key); keys.add(key);
        ws(); if (raw[cursor++] !== ':') fail('json');
        object[key] = value(depth + 1); ws();
        const delimiter = raw[cursor++];
        if (delimiter === '}') return object;
        if (delimiter !== ',') fail('json');
      }
    } else if (c === '[') {
      cursor++; ws(); const array = [];
      if (raw[cursor] === ']') { cursor++; return array; }
      while (cursor < raw.length) {
        array.push(value(depth + 1)); ws();
        const delimiter = raw[cursor++];
        if (delimiter === ']') return array;
        if (delimiter !== ',') fail('json');
      }
    } else {
      const rest = raw.slice(cursor);
      for (const [token, result] of [['true', true], ['false', false], ['null', null]]) {
        if (rest.startsWith(token)) { cursor += token.length; return result; }
      }
      const number = /^-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?/.exec(rest);
      if (number) { if (/[.eE]/.test(number[0])) fail('integer'); cursor += number[0].length; const result = Number(number[0]); if (!Number.isFinite(result)) fail('json'); return result; }
    }
    fail('json');
  };
  const parsed = value(); ws(); if (cursor !== raw.length) fail('json'); return parsed;
}

function keysExactly(value, keys, path) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) fail('object', path);
  const actual = Object.keys(value);
  if (actual.length !== keys.length || actual.some(key => !keys.includes(key))) fail('keys', path);
}
export function validateSize(value, field, maxResolution = Infinity) {
  if (typeof value !== 'number' || !Number.isSafeInteger(value) || value < 32 || value % 32 !== 0) fail('size', field);
  if (value > maxResolution) fail('maxSize', `${field}: ${maxResolution}`);
  return value;
}
export function normalizeState(state, maxResolution = Infinity) {
  if (!state || typeof state !== 'object' || Array.isArray(state)) fail('object', 'state');
  if (![1, 2].includes(state.schema_version)) fail('version');
  keysExactly(state, state.schema_version === 1 ? ['schema_version', 'views', 'size'] : ['schema_version', 'views', 'size', 'part_prompts'], 'state');
  if (!Array.isArray(state.views) || !state.views.length || state.views.some(view => typeof view !== 'string' || !VIEW_IDS.includes(view))) fail('views');
  keysExactly(state.size, ['mode', 'body_height', 'manual_width', 'manual_height'], 'size');
  if (!['auto', 'manual'].includes(state.size.mode)) fail('mode');
  const normalized = {schema_version: state.schema_version, views: VIEW_IDS.filter(view => state.views.includes(view)), size: {
    mode: state.size.mode,
    body_height: validateSize(state.size.body_height, 'body_height', maxResolution),
    manual_width: validateSize(state.size.manual_width, 'manual_width', maxResolution),
    manual_height: validateSize(state.size.manual_height, 'manual_height', maxResolution),
  }};
  if (state.schema_version === 2) {
    const prompts = state.part_prompts;
    if (!prompts || typeof prompts !== 'object' || Array.isArray(prompts)) fail('object', 'part_prompts');
    if (Object.keys(prompts).some(part => !PART_IDS.includes(part))) fail('parts');
    normalized.part_prompts = {};
    for (const part of PART_IDS) {
      if (!Object.hasOwn(prompts, part)) continue;
      const text = validatePartPrompt(prompts[part]);
      if (text.trim()) normalized.part_prompts[part] = text;
    }
  }
  return normalized;
}
export function validatePartPrompt(text) {
  if (typeof text !== 'string') fail('partText');
  if (text.length > PART_PROMPT_MAX_LENGTH) fail('partLength');
  if (!text.isWellFormed()) fail('partUnicode');
  return text;
}
// Migration is explicit and only invoked by an actual part edit, never on restore.
export function migratePartState(state) {
  const next = normalizeState(state);
  if (next.schema_version === 1) { next.schema_version = 2; next.part_prompts = {}; }
  return next;
}
export const parseState = (raw, maxResolution) => normalizeState(parseJSONStrict(raw), maxResolution);
export const serializeState = (state, maxResolution) => JSON.stringify(normalizeState(state, maxResolution));
export const presetOf = state => Object.entries(PRESETS).find(([, views]) => views.join() === state?.views.join())?.[0] ?? 'custom';

export function getLocale(app) {
  let value;
  try {
    const getter = app?.extensionManager?.setting?.get;
    value = typeof getter === 'function' ? getter.call(app.extensionManager.setting, 'Comfy.Locale') : app?.ui?.settings?.getSettingValue?.('Comfy.Locale');
  } catch { return 'en'; }
  return typeof value === 'string' && value.toLowerCase().split(/[-_]/)[0] === 'ja' ? 'ja' : 'en';
}
export function subscribeLocale(app, callback) {
  const source = app?.ui?.settings;
  if (typeof source?.addEventListener !== 'function' || typeof source?.removeEventListener !== 'function') return () => {};
  const handler = () => callback(getLocale(app));
  source.addEventListener('Comfy.Locale.change', handler);
  return () => source.removeEventListener('Comfy.Locale.change', handler);
}

export function validatePreview(data, state) {
  if (!data || !Number.isSafeInteger(data.width) || !Number.isSafeInteger(data.height) || data.width < 32 || data.height < 32 || data.width % 32 || data.height % 32 || !data.layout || !Array.isArray(data.layout.panels)) fail('preview');
  if (data.layout.canvas?.[0] !== data.width || data.layout.canvas?.[1] !== data.height) fail('preview');
  const panels = data.layout.panels;
  if (panels.length !== state.views.length || panels.some((p, i) => p.id !== state.views[i] || !Array.isArray(p.rect) || p.rect.length !== 4 || p.rect.some(x => !Number.isFinite(x)) || p.rect[0] < 0 || p.rect[1] < 0 || p.rect[2] <= 0 || p.rect[3] <= 0 || p.rect[0] + p.rect[2] > 1.000002 || p.rect[1] + p.rect[3] > 1.000002)) fail('preview');
  if (data.layout.feet_y !== null && (!Number.isFinite(data.layout.feet_y) || data.layout.feet_y < 0 || data.layout.feet_y > 1)) fail('preview');
  return data;
}

/** One persistent value, with separate advisory preview and request identity. */
export class DesignerController {
  constructor({raw, requestPreview, transaction = fn => fn(), onChange = () => {}, onCommit = () => {}, timeoutMs = 15000, readRaw = null, writeRaw = null}) {
    this.readRaw = readRaw; this.writeRaw = writeRaw; this._raw = raw; this.observedRaw = raw; this.state = null; this.error = null; this.preview = null; this.previewRaw = null;
    this.pending = false; this.previewError = null; this.maxResolution = Infinity;
    this.generation = 0; this.requestNumber = 0; this.disposed = false;
    this.requestPreview = requestPreview; this.transaction = transaction; this.onChange = onChange; this.onCommit = onCommit; this.timeoutMs = timeoutMs;
    this.restore(raw, false);
  }
  // Embedded integrations can retain their official widget as the sole value owner.
  // The controller caches parsed/preview state only; raw always reads that source.
  get raw() { return this.readRaw ? this.readRaw() : this._raw; }
  set raw(value) { if (this.writeRaw) this.writeRaw(value); else this._raw = value; }
  syncFromSource() {
    if (!this.disposed && this.raw !== this.observedRaw) { this.restore(this.raw); return true; }
    return false;
  }
  get isCurrentPreview() { return !this.pending && !this.previewError && this.preview !== null && this.previewRaw === this.raw; }
  emit(reason) { if (!this.disposed) this.onChange(this, reason); }
  invalidate() { this.generation++; this.requestNumber++; this.abort?.abort(); this.abort = null; clearTimeout(this.timer); this.pending = false; }
  restore(raw, notify = true) {
    if (this.disposed) return;
    this.invalidate(); this.observedRaw = raw; if (this.raw !== raw) this.raw = raw; this.previewRaw = null; this.previewError = null;
    try { this.state = parseState(raw, this.maxResolution); this.error = null; }
    catch (error) { this.state = null; this.error = error; }
    if (notify) this.emit('restore');
    if (this.state) void this.refreshPreview();
  }
  commit(next) {
    if (this.disposed) return false;
    this.syncFromSource();
    const raw = serializeState(next, this.maxResolution);
    if (raw === this.raw) return false;
    const previous = this.raw;
    this.transaction(() => {
      this.invalidate(); this.observedRaw = raw; this.raw = raw; this.state = parseState(raw, this.maxResolution); this.error = null; this.previewError = null; this.previewRaw = null;
      this.onCommit(raw, previous);
    });
    this.emit('commit'); void this.refreshPreview(); return true;
  }
  change(mutator) {
    this.syncFromSource();
    if (!this.state || this.disposed) return false;
    const next = structuredClone(this.state); mutator(next); return this.commit(next);
  }
  toggle(view) {
    this.syncFromSource();
    if (!VIEW_IDS.includes(view)) fail('views');
    if (this.state?.views.length === 1 && this.state.views[0] === view) fail('lastView');
    return this.change(next => { next.views = next.views.includes(view) ? next.views.filter(id => id !== view) : [...next.views, view]; });
  }
  preset(name) { if (!PRESETS[name]) fail('views'); return this.change(next => { next.views = [...PRESETS[name]]; }); }
  setMode(mode) {
    this.syncFromSource();
    if (mode === this.state?.size.mode) return false;
    if (mode === 'manual') {
      if (!this.isCurrentPreview) fail('updating');
      return this.change(next => { next.size.mode = 'manual'; next.size.manual_width = this.preview.width; next.size.manual_height = this.preview.height; });
    }
    if (mode !== 'auto') fail('mode');
    return this.change(next => { next.size.mode = 'auto'; });
  }
  setSize(field, text) {
    if (!['body_height', 'manual_width', 'manual_height'].includes(field)) fail('keys', field);
    if (typeof text !== 'string' || !/^\d+$/.test(text.trim())) fail('size', field);
    const value = validateSize(Number(text.trim()), field, this.maxResolution);
    return this.change(next => { next.size[field] = value; });
  }
  setPartPrompt(part, text) {
    this.syncFromSource();
    if (!PART_IDS.includes(part)) fail('parts');
    validatePartPrompt(text);
    if (!this.state || this.disposed) return false;
    if (text === this.state.part_prompts?.[part]) return false;
    // Opening an empty editor is not a schema migration or an Undo entry.
    if (!text.trim() && !this.state.part_prompts?.[part]) return false;
    const next = migratePartState(this.state);
    if (text.trim()) next.part_prompts[part] = text;
    else delete next.part_prompts[part];
    return this.commit(next);
  }
  applyRaw(raw) { return this.commit(parseState(raw, this.maxResolution)); }
  async refreshPreview() {
    if (this.syncFromSource()) return;
    if (this.disposed || !this.state) return;
    this.abort?.abort(); clearTimeout(this.timer);
    const abort = new AbortController(); this.abort = abort;
    const generation = this.generation, request = ++this.requestNumber, raw = this.raw, state = this.state;
    const current = () => !this.disposed && this.generation === generation && this.requestNumber === request && this.raw === raw;
    this.pending = true; this.previewError = null; this.emit('pending');
    try {
      const timeout = new Promise((_, reject) => { this.timer = setTimeout(() => { abort.abort(); reject(new StateError('timeout')); }, this.timeoutMs); });
      const result = await Promise.race([this.requestPreview(raw, abort.signal), timeout]);
      if (!current()) return;
      this.preview = validatePreview(result, state); this.previewRaw = raw;
      if (Number.isSafeInteger(result.max_resolution) && result.max_resolution >= 32) this.maxResolution = result.max_resolution;
      this.pending = false; this.previewError = null; this.emit('preview');
    } catch (error) {
      if (!current()) return;
      this.pending = false; this.previewError = error; this.emit('preview-error');
    } finally { if (current()) { clearTimeout(this.timer); this.abort = null; } }
  }
  dispose() { this.invalidate(); this.disposed = true; this.onChange = () => {}; this.onCommit = () => {}; this.requestPreview = null; this.preview = null; this.state = null; }
}
