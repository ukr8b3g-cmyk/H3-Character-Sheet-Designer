import test from 'node:test';
import assert from 'node:assert/strict';
import {DEFAULT_JSON, DEFAULT_STATE, VIEW_IDS, PRESETS, parseState, serializeState, parseJSONStrict, DesignerController, getLocale, subscribeLocale, StateError, presetOf, PART_IDS, PART_PROMPT_MAX_LENGTH, MAX_BYTES, migratePartState} from '../../web/state.js';
const clone = () => structuredClone(DEFAULT_STATE);
const tick = () => new Promise(resolve => setImmediate(resolve));
function preview(raw, width = 2208, height = 1280) {
  const state = parseState(raw);
  return {width, height, max_resolution: 16384, layout: {canvas: [width, height], panels: state.views.map((id, i) => ({id, rect: [i / state.views.length, 0, 1 / state.views.length, 1]})), feet_y: state.views.some(id => id.startsWith('body_')) ? 1 : null}};
}
function deferredController(raw = DEFAULT_JSON) {
  const calls = [], commits = [], transactions = [];
  const controller = new DesignerController({raw, requestPreview: (value, signal) => new Promise((resolve, reject) => calls.push({raw: value, signal, resolve, reject})), transaction: fn => { transactions.push('before'); fn(); transactions.push('after'); }, onCommit: value => commits.push(value)});
  return {controller, calls, commits, transactions};
}

test('canonical schema matches default, order and semantic normalization', () => {
  assert.equal(DEFAULT_JSON, '{"schema_version":1,"views":["face_front","body_front","body_left","body_back"],"size":{"mode":"auto","body_height":1120,"manual_width":2240,"manual_height":1280}}');
  const state = clone(); state.views = ['feet', 'body_back', 'feet', 'face_front'];
  const raw = JSON.stringify({size: {manual_height: 1280, body_height: 1120, manual_width: 2240, mode: 'auto'}, views: state.views, schema_version: 1}, null, 2);
  assert.equal(serializeState(parseState(raw)), serializeState(state));
  assert.deepEqual(parseState(raw).views, ['face_front', 'body_back', 'feet']);
  assert.equal(presetOf(DEFAULT_STATE), 'basic');
});

test('strict parser refuses duplicate keys including escaped duplicates and nested size keys', () => {
  for (const raw of ['{"x":1,"x":2}', '{"x":1,"\\u0078":2}', DEFAULT_JSON.replace('"mode":"auto"', '"mode":"auto","mode":"manual"')]) assert.throws(() => parseJSONStrict(raw), error => error.code === 'duplicateKey');
});

test('malformed values, unknown fields and floating JSON integer tokens are rejected', () => {
  const rawCases = [DEFAULT_JSON.replace('"schema_version":1', '"schema_version":1.0'), DEFAULT_JSON.replace('1120', '1120.0'), DEFAULT_JSON.replace('1120', '112e1'), DEFAULT_JSON.replace('1120', 'NaN'), DEFAULT_JSON.replace('1120', 'Infinity'), DEFAULT_JSON.replace('1120', '1e999'), DEFAULT_JSON + 'x', '{', '[1,]', '{"a":1,}'];
  for (const raw of rawCases) assert.throws(() => parseState(raw));
  const changes = [s => { s.schema_version = true; }, s => { s.schema_version = 2; }, s => { s.views = []; }, s => { s.views = ['bogus']; }, s => { s.views = [true]; }, s => { s.size.mode = 'other'; }, s => { s.size.body_height = 1119; }, s => { s.size.body_height = true; }, s => { s.size.body_height = '1120'; }, s => { s.size.body_height = 32.5; }, s => { s.extra = 1; }, s => { delete s.size.manual_width; }, s => { s.size.extra = 1; }];
  for (const change of changes) { const state = clone(); change(state); assert.throws(() => parseState(JSON.stringify(state))); }
  assert.throws(() => parseState(DEFAULT_JSON, 1024), error => error.code === 'maxSize');
  assert.throws(() => parseState(' '.repeat(MAX_BYTES + 1)), error => error.code === 'oversize');
  assert.throws(() => parseJSONStrict('"' + 'あ'.repeat(Math.ceil(MAX_BYTES / 3)) + '"'), error => error.code === 'oversize');
});

test('all 127 selections canonicalize without calculating layout in JS', () => {
  for (let mask = 1; mask < 1 << VIEW_IDS.length; mask++) { const state = clone(); state.views = VIEW_IDS.filter((_, i) => mask & (1 << i)).reverse(); const result = parseState(serializeState(state)); assert.deepEqual(result.views, VIEW_IDS.filter((_, i) => mask & (1 << i))); }
});

test('view clicks synchronously own the serialized value for immediate save/API/queue', t => {
  const h = deferredController(); t.after(() => h.controller.dispose());
  h.controller.toggle('hands');
  assert.ok(parseState(h.controller.raw).views.includes('hands'));
  assert.equal(h.commits.at(-1), h.controller.raw);
  assert.deepEqual(h.transactions, ['before', 'after']);
  h.controller.toggle('feet');
  assert.equal(parseState(h.controller.raw).views.length, 6);
  assert.equal(h.calls.at(-1).raw, h.controller.raw);
  assert.equal(h.controller.pending, true);
});

test('one preset is one transaction and keeps every size setting', t => {
  const state = clone(); state.size.mode = 'manual'; state.size.manual_width = 3200;
  const h = deferredController(serializeState(state)); t.after(() => h.controller.dispose());
  h.controller.preset('single');
  assert.deepEqual(h.controller.state.views, PRESETS.single);
  assert.deepEqual(h.controller.state.size, state.size);
  assert.equal(h.commits.length, 1);
  assert.throws(() => h.controller.toggle('body_front'), error => error.code === 'lastView');
  assert.equal(h.commits.length, 1);
});

test('stale requests are ignored including A → B → A with equal raw strings', async t => {
  const h = deferredController(); t.after(() => h.controller.dispose());
  const original = h.controller.raw; h.controller.toggle('hands'); h.controller.toggle('hands'); assert.equal(h.controller.raw, original);
  h.calls[0].resolve(preview(original, 1344, 768)); await tick(); assert.equal(h.controller.preview, null);
  h.calls[1].resolve(preview(h.calls[1].raw)); await tick(); assert.equal(h.controller.preview, null);
  h.calls[2].resolve(preview(original)); await tick(); assert.equal(h.controller.preview.width, 2208); assert.equal(h.controller.isCurrentPreview, true);
  assert.equal(h.calls[0].signal.aborted, true);
});

test('preview never canonicalizes or writes persistent raw input', async t => {
  const raw = JSON.stringify(DEFAULT_STATE, null, 2), h = deferredController(raw); t.after(() => h.controller.dispose());
  h.calls[0].resolve({...preview(raw), state_json: 'server-must-never-overwrite'}); await tick();
  assert.equal(h.controller.raw, raw); assert.equal(h.commits.length, 0);
});

test('Auto to Manual is gated on matching preview and copies both dimensions atomically', async t => {
  const h = deferredController(); t.after(() => h.controller.dispose());
  assert.throws(() => h.controller.setMode('manual'), error => error.code === 'updating');
  h.calls[0].resolve(preview(h.controller.raw)); await tick(); h.controller.setMode('manual');
  assert.deepEqual(h.controller.state.size, {mode: 'manual', body_height: 1120, manual_width: 2208, manual_height: 1280});
  assert.equal(h.commits.length, 1);
  h.controller.setSize('manual_width', '3200'); h.controller.preset('detail');
  assert.equal(h.controller.state.size.manual_width, 3200);
  h.controller.setMode('auto'); assert.equal(h.controller.state.size.manual_width, 3200);
});

test('latest-only gating survives restore/Undo even if value is equal', async t => {
  const h = deferredController(); t.after(() => h.controller.dispose());
  h.controller.restore(DEFAULT_JSON); assert.equal(h.commits.length, 0); assert.equal(h.transactions.length, 0);
  h.calls[0].resolve(preview(DEFAULT_JSON, 1344, 768)); await tick(); assert.equal(h.controller.preview, null);
  h.calls[1].resolve(preview(DEFAULT_JSON)); await tick(); assert.equal(h.controller.preview.width, 2208);
});

test('deleted node ignores late responses and cancels active request', async () => {
  const h = deferredController(); h.controller.dispose(); assert.equal(h.calls[0].signal.aborted, true);
  h.calls[0].resolve(preview(DEFAULT_JSON)); await tick(); assert.equal(h.controller.preview, null); assert.equal(h.controller.disposed, true);
});

test('invalid saved input is preserved, refuses changes, explicit repair is one commit', t => {
  const raw = DEFAULT_JSON.replace('"schema_version":1', '"schema_version":999'), h = deferredController(raw); t.after(() => h.controller.dispose());
  assert.equal(h.controller.raw, raw); assert.equal(h.controller.state, null); assert.equal(h.calls.length, 0);
  h.controller.preset('detail'); assert.equal(h.controller.raw, raw);
  h.controller.applyRaw(DEFAULT_JSON); assert.equal(h.controller.raw, DEFAULT_JSON); assert.equal(h.commits.length, 1);
});

test('preview failure leaves current state intact, retry is advisory, no old success substituted', async t => {
  const h = deferredController(); t.after(() => h.controller.dispose());
  h.calls[0].resolve(preview(DEFAULT_JSON)); await tick(); h.controller.toggle('feet');
  const raw = h.controller.raw; h.calls[1].reject(new Error('offline')); await tick();
  assert.equal(h.controller.raw, raw); assert.equal(h.controller.isCurrentPreview, false); assert.ok(h.controller.previewError);
  void h.controller.refreshPreview(); h.calls[2].resolve(preview(raw)); await tick();
  assert.equal(h.controller.raw, raw); assert.equal(h.controller.isCurrentPreview, true); assert.equal(h.commits.length, 1);
});

test('invalid preview data is refused without rollback', async t => {
  const h = deferredController(); t.after(() => h.controller.dispose());
  h.calls[0].resolve({...preview(DEFAULT_JSON), layout: {canvas: [2208, 1280], panels: [], feet_y: null}}); await tick();
  assert.equal(h.controller.preview, null); assert.equal(h.controller.previewError.code, 'preview'); assert.equal(h.controller.raw, DEFAULT_JSON);
});

test('numeric drafts validate strictly without hidden rounding', t => {
  const h = deferredController(); t.after(() => h.controller.dispose());
  for (const invalid of ['', '1120.0', '1e3', '-32', '31', '1119', 'NaN']) assert.throws(() => h.controller.setSize('body_height', invalid));
  assert.equal(h.commits.length, 0); h.controller.setSize('body_height', ' 672 '); assert.equal(h.controller.state.size.body_height, 672);
});

test('locale uses preferred Comfy setting only, never browser locale', () => {
  const eventTarget = new EventTarget(); let value = 'JA-jp', calls = 0;
  eventTarget.getSettingValue = () => { calls++; return 'ja'; };
  const app = {extensionManager: {setting: {get: () => value}}, ui: {settings: eventTarget}};
  assert.equal(getLocale(app), 'ja'); value = 'fr'; assert.equal(getLocale(app), 'en'); value = undefined; assert.equal(getLocale(app), 'en'); assert.equal(calls, 0);
  delete app.extensionManager; assert.equal(getLocale(app), 'ja');
  let notifications = 0; const unsubscribe = subscribeLocale(app, locale => { assert.equal(locale, 'ja'); notifications++; });
  eventTarget.dispatchEvent(new Event('Comfy.Locale.change')); unsubscribe(); eventTarget.dispatchEvent(new Event('Comfy.Locale.change')); assert.equal(notifications, 1);
  assert.equal(getLocale({}), 'en');
});

test('timeout releases Manual gate without rolling back and can retry', async t => {
  let count = 0;
  const controller = new DesignerController({raw: DEFAULT_JSON, timeoutMs: 5, requestPreview: async raw => { if (count++ === 0) return new Promise(() => {}); return preview(raw); }});
  t.after(() => controller.dispose());
  await new Promise(resolve => setTimeout(resolve, 20));
  assert.equal(controller.pending, false); assert.equal(controller.previewError.code, 'timeout'); assert.equal(controller.raw, DEFAULT_JSON);
  await controller.refreshPreview(); assert.equal(controller.isCurrentPreview, true);
});

test('duplicate logical no-op makes no transaction and a retry does not alter generation state', async t => {
  const h = deferredController(); t.after(() => h.controller.dispose());
  assert.equal(h.controller.preset('basic'), false); assert.equal(h.controller.setSize('body_height', '1120'), false);
  assert.equal(h.transactions.length, 0); assert.equal(h.commits.length, 0);
  void h.controller.refreshPreview(); h.calls[0].resolve(preview(DEFAULT_JSON, 1344, 768)); await tick(); assert.equal(h.controller.preview, null);
  h.calls[1].resolve(preview(DEFAULT_JSON)); await tick(); assert.equal(h.controller.isCurrentPreview, true); assert.equal(h.commits.length, 0);
});


test('part migration is explicit; empty opening, selections, and restoration retain v1', t => {
  const h = deferredController(); t.after(() => h.controller.dispose());
  h.controller.setPartPrompt('footwear', '   '); assert.equal(h.controller.raw, DEFAULT_JSON);
  h.controller.toggle('feet'); assert.equal(h.controller.state.schema_version, 1);
  h.controller.setPartPrompt('footwear', '黒いブーツ');
  assert.equal(h.controller.state.schema_version, 2); assert.deepEqual(h.controller.state.part_prompts, {footwear: '黒いブーツ'});
  const saved = h.controller.raw;
  h.controller.preset('single'); h.controller.setSize('body_height', '672');
  assert.deepEqual(h.controller.state.part_prompts, {footwear: '黒いブーツ'});
  h.controller.restore(DEFAULT_JSON); assert.equal(h.controller.raw, DEFAULT_JSON);
  h.controller.restore(saved); assert.equal(h.controller.state.part_prompts.footwear, '黒いブーツ');
  h.controller.setPartPrompt('footwear', ''); assert.equal(h.controller.state.schema_version, 2); assert.deepEqual(h.controller.state.part_prompts, {});
});

test('v2 has exact keys, canonical parts, bounded well-formed Unicode, and no interpretation', () => {
  const v2 = migratePartState(DEFAULT_STATE);
  const literal = '  背面の「FLOWER」 {red|blue} C:\\design\n白い手袋 🌸  ';
  v2.part_prompts = {other: '末尾', back_clothing: literal, face: '\ufeff '};
  const normalized = parseState(serializeState(v2));
  assert.deepEqual(Object.keys(normalized.part_prompts), ['back_clothing', 'other']);
  assert.equal(normalized.part_prompts.back_clothing, literal);
  for (const prompts of [[], null, 'no', {unknown: 'x'}, {face: true}, {face: 12}, {face: '\ud800'}, {face: '\udc00'}, {face: 'x'.repeat(PART_PROMPT_MAX_LENGTH + 1)}]) {
    assert.throws(() => serializeState({...v2, part_prompts: prompts}));
  }
  for (const text of ['あ'.repeat(1000), '🌸'.repeat(500), '\u0000'.repeat(1000)]) {
    const state = {...v2, part_prompts: Object.fromEntries(PART_IDS.map(part => [part, text]))};
    assert.deepEqual(parseState(serializeState(state)), state);
    // Python can return ASCII escaped canonical state; this also fits the limit.
    const escaped = serializeState(state).replace(/[\u007f-\uffff]/g, char => '\\u' + char.charCodeAt(0).toString(16).padStart(4, '0'));
    assert(new TextEncoder().encode(escaped).length < MAX_BYTES); assert.deepEqual(parseState(escaped), state);
  }
  assert.throws(() => parseState(JSON.stringify({...v2, schema_version: 3})), error => error.code === 'version');
  assert.throws(() => parseState(JSON.stringify({...DEFAULT_STATE, part_prompts: {}})), error => error.code === 'keys');
});

test('part edits synchronously update Queue, skip duplicate blur commits and survive stale preview', async t => {
  const h = deferredController(); t.after(() => h.controller.dispose());
  h.controller.setPartPrompt('face', 'サングラス'); const saved = h.controller.raw;
  assert.equal(h.commits.at(-1), saved); assert.equal(JSON.parse(saved).part_prompts.face, 'サングラス');
  assert.equal(h.controller.setPartPrompt('face', 'サングラス'), false); assert.equal(h.commits.length, 1);
  h.calls[0].resolve(preview(DEFAULT_JSON)); await tick(); assert.equal(h.controller.preview, null);
  h.calls[1].resolve(preview(saved)); await tick(); assert.equal(h.controller.isCurrentPreview, true);
  assert.throws(() => h.controller.setPartPrompt('face', 'x'.repeat(1001)), error => error.code === 'partLength');
  assert.equal(h.controller.raw, saved);
});
