import test from 'node:test';
import assert from 'node:assert/strict';
import {pathToFileURL} from 'node:url';
import {DEFAULT_JSON, parseState, serializeState, DEFAULT_STATE} from '../../web/state.js';
let JSDOM;
try { ({JSDOM} = await import(process.env.H3_JSDOM_PATH ? pathToFileURL(process.env.H3_JSDOM_PATH).href : 'jsdom')); } catch {}
const domTest = (name, fn) => test(name, {skip: !JSDOM && 'Optional jsdom is unavailable; set H3_JSDOM_PATH to its api.js or install jsdom for DOM tests.'}, fn);
let installDesigner, createExtension;
if (JSDOM) ({installDesigner, createExtension} = await import('../../web/integration.js'));
const tick = () => new Promise(resolve => setImmediate(resolve));
function setup() {
  const dom = new JSDOM('<!doctype html><html><head></head><body></body></html>', {url: 'http://localhost/'});
  const globals = ['window', 'document', 'AbortController', 'Event', 'KeyboardEvent', 'HTMLElement'];
  const savedGlobals = Object.fromEntries(globals.map(key => [key, globalThis[key]]));
  for (const key of globals) globalThis[key] = dom.window[key];
  let locale = 'en'; const settings = new dom.window.EventTarget();
  const app = {extensionManager: {setting: {get: () => locale}}, ui: {settings}, graph: {_nodes: []}};
  const requests = [], transactions = [], registry = new Set();
  const api = {fetchApi: (path, opts) => new Promise((resolve, reject) => requests.push({path, opts, resolve, reject}))};
  const graph = app.graph;
  graph.beforeChange = node => transactions.push(['before', node.widgets.find(w => w.name === 'state_json').value]);
  graph.afterChange = node => transactions.push(['after', node.widgets.find(w => w.name === 'state_json').value]);
  function node(raw = DEFAULT_JSON, prefixWidget = false) {
    const element = document.createElement('textarea'); element.value = raw;
    const original = {name: 'state_json', type: 'customtext', value: raw, options: {}, element, onRemove() { registry.delete(original); element.remove(); }};
    const item = {type: 'H3CharacterSheetDesigner', comfyClass: 'H3CharacterSheetDesigner', size: [300, 100], widgets: prefixWidget ? [{name: 'other', value: 'kept'}, original] : [original], graph, onConfigure() { return 'configure-original'; }, onRemoved() { return 'remove-original'; }, onAdded() { registry.add(original); return 'add-original'; },
      setSize(size) { this.size = size; }, setDirtyCanvas() {},
      addDOMWidget(name, type, element, options) {
        const widget = {name, type, element, options, onRemove() { registry.delete(widget); element.remove(); }};
        Object.defineProperty(widget, 'value', {get: options.getValue, set: options.setValue});
        this.widgets.push(widget); document.body.append(element); registry.add(widget);
        const previous = this.onAdded; this.onAdded = function (...args) { const result = previous?.apply(this, args); registry.add(widget); return result; };
        return widget;
      },
    };
    graph._nodes.push(item); const record = installDesigner(item, app, api); return {item, original, record};
  }
  function resolve(index = requests.length - 1, width = 2208, height = 1280) {
    const request = requests[index], raw = JSON.parse(request.opts.body).state_json, state = parseState(raw);
    request.resolve({ok: true, json: async () => ({width, height, max_resolution: 16384, layout: {canvas: [width, height], panels: state.views.map((id, i) => ({id, rect: [i / state.views.length, 0, 1 / state.views.length, 1]})), feet_y: state.views.some(id => id.startsWith('body_')) ? 1 : null}})});
  }
  return {dom, app, requests, transactions, registry, node, resolve, locale(value) { locale = value; settings.dispatchEvent(new Event('Comfy.Locale.change')); }, cleanup() { for (const node of graph._nodes) node.onRemoved?.(); dom.window.close(); for (const key of globals) { if (savedGlobals[key] === undefined) delete globalThis[key]; else globalThis[key] = savedGlobals[key]; } }};
}

domTest('single named STRING keeps original position; no second generation widget; instance hooks preserve returns', async t => {
  const h = setup(); t.after(h.cleanup); const {item, original, record} = h.node(DEFAULT_JSON, true);
  assert.equal(item.widgets.length, 2); assert.equal(item.widgets[0].name, 'other'); assert.equal(item.widgets[1].name, 'state_json'); assert.equal(item.widgets[1].serialize, true); assert.equal(item.widgets[1].options.dynamicPrompts, false);
  assert.equal(item.onAdded(), 'add-original'); assert.equal(h.registry.has(original), false); assert.equal(h.registry.has(record.widget), true);
  assert.equal(item.onConfigure({}), 'configure-original'); assert.equal(item.onRemoved(), 'remove-original'); assert.equal(record.controller.disposed, true);
});

domTest('click → immediate save/queue uses latest raw, one Undo transaction; locale makes none', async t => {
  const h = setup(); t.after(h.cleanup); const {record, item} = h.node(); const root = record.ui.root;
  root.querySelector('[data-view="hands"]').click();
  const saved = item.widgets.find(w => w.name === 'state_json').value;
  assert.ok(parseState(saved).views.includes('hands')); assert.equal(h.transactions.length, 2);
  assert.equal(root.querySelector('[data-view="hands"]').getAttribute('aria-pressed'), 'true');
  h.locale('ja-JP'); assert.equal(root.lang, 'ja'); assert.equal(root.querySelector('[data-view="hands"] .h3-card-label').textContent, '両手'); assert.equal(item.widgets[0].value, saved); assert.equal(h.transactions.length, 2);
  h.locale('fr'); assert.equal(root.lang, 'en');
});

domTest('draft inputs remain separate; valid Enter commits once, invalid draft does not', async t => {
  const h = setup(); t.after(h.cleanup); const {record} = h.node(); const input = record.ui.root.querySelector('[data-field="body_height"]');
  input.value = '673'; input.dispatchEvent(new Event('input', {bubbles: true}));
  assert.equal(record.controller.raw, DEFAULT_JSON); assert.match(input.parentElement.parentElement.textContent, /Uncommitted/);
  input.dispatchEvent(new KeyboardEvent('keydown', {key: 'Enter', bubbles: true}));
  assert.equal(record.controller.raw, DEFAULT_JSON); assert.equal(input.getAttribute('aria-invalid'), 'true');
  input.value = '672'; input.dispatchEvent(new Event('input', {bubbles: true})); input.dispatchEvent(new KeyboardEvent('keydown', {key: 'Enter', bubbles: true}));
  assert.equal(record.controller.state.size.body_height, 672); assert.equal(h.transactions.length, 2); assert.equal(input.getAttribute('aria-invalid'), 'false');
  input.dispatchEvent(new Event('blur')); assert.equal(h.transactions.length, 2);
});

domTest('Auto fields show actual computed dimensions; Manual captures latest preview only', async t => {
  const h = setup(); t.after(h.cleanup); const {record} = h.node(); const root = record.ui.root, manual = root.querySelector('[data-mode="manual"]');
  assert.equal(manual.disabled, true); h.resolve(); await tick();
  assert.equal(root.querySelector('[data-field="manual_width"]').value, '2208'); assert.equal(record.controller.state.size.manual_width, 2240);
  assert.equal(manual.disabled, false); manual.click();
  assert.equal(record.controller.state.size.mode, 'manual'); assert.equal(record.controller.state.size.manual_width, 2208); assert.equal(root.querySelector('[data-field="manual_width"]').disabled, false);
});

domTest('restoration preserves malformed text and requires explicit repair; no silent reset', async t => {
  const h = setup(); t.after(h.cleanup); const bad = DEFAULT_JSON.replace('1120', '1120.0'), {record, item} = h.node(bad);
  assert.equal(record.widget.value, bad); assert.equal(record.controller.state, null); assert.equal(h.requests.length, 0); assert.equal(record.ui.root.querySelector('[data-view="hands"]').disabled, true);
  assert.equal(record.ui.root.querySelector('textarea').value, bad);
  record.ui.root.querySelector('textarea').value = DEFAULT_JSON; record.ui.root.querySelector('.h3-apply').click(); assert.equal(record.widget.value, DEFAULT_JSON); assert.equal(h.transactions.length, 2);
  item.widgets.find(w => w.name === 'state_json').value = bad; item.onConfigure({}); assert.equal(record.widget.value, bad); assert.equal(record.controller.state, null);
});

domTest('new/duplicate instances own independent values, DOM, requests and unique SVG IDs', async t => {
  const h = setup(); t.after(h.cleanup); const first = h.node(), second = h.node(first.record.widget.value);
  assert.notEqual(first.record.ui.root, second.record.ui.root);
  first.record.controller.toggle('hands'); assert.equal(second.record.widget.value, DEFAULT_JSON);
  const ids = [...document.querySelectorAll('svg [id]')].map(el => el.id); assert.equal(ids.length, new Set(ids).size);
  h.resolve(1); await tick(); assert.ok(second.record.controller.preview); assert.equal(first.record.controller.preview, null);
});

domTest('restore and deleted nodes ignore in-flight responses; locale listener cleans up', async t => {
  const h = setup(); t.after(h.cleanup); const {record, item} = h.node();
  record.widget.value = DEFAULT_JSON; h.resolve(0, 1344, 768); await tick(); assert.equal(record.controller.preview, null);
  const root = record.ui.root; item.onRemoved(); h.resolve(1); await tick(); assert.equal(record.controller.preview, null); assert.equal(document.body.contains(root), false);
  const oldLang = root.lang; h.locale('ja'); assert.equal(root.lang, oldLang);
});

domTest('fallback retains exactly one ordinary input when DOM API is absent', t => {
  const h = setup(); t.after(h.cleanup); const widget = {name: 'state_json', value: DEFAULT_JSON, options: {}}; const node = {widgets: [widget]};
  assert.equal(installDesigner(node, h.app, {}), null); assert.equal(node.widgets.length, 1); assert.equal(node.widgets[0], widget); assert.equal(node.h3DesignerCompatibility.graphical, false); assert.match(widget.options.tooltip, /Graphical designer unavailable/);
});

domTest('preset single and auxiliary-only cases render current selections and accessible controls', async t => {
  const h = setup(); t.after(h.cleanup); const {record} = h.node(); const root = record.ui.root;
  const preset = root.querySelector('select.h3-select'); preset.value = 'single'; preset.dispatchEvent(new Event('change'));
  assert.deepEqual(record.controller.state.views, ['body_front']); root.querySelector('[data-view="body_front"]').click(); assert.deepEqual(record.controller.state.views, ['body_front']); assert.match(root.querySelector('.h3-error').textContent, /at least one/);
  const state = structuredClone(DEFAULT_STATE); state.views = ['hands', 'feet']; record.widget.value = serializeState(state); h.resolve(); await tick();
  assert.equal(root.querySelectorAll('.h3-panel').length, 2); assert.equal(root.querySelectorAll('.h3-baseline').length, 0); assert.equal(root.querySelectorAll('[aria-pressed="true"].h3-card').length, 2);
});

domTest('failed DOM setup retains the original normal STRING widget', t => {
  const h = setup(); t.after(h.cleanup); const original = {name: 'state_json', value: DEFAULT_JSON, options: {}};
  const node = {widgets: [original], addDOMWidget() { throw new Error('not supported'); }};
  assert.equal(installDesigner(node, h.app, h.requests), null);
  assert.deepEqual(node.widgets, [original]); assert.equal(original.value, DEFAULT_JSON); assert.equal(node.h3DesignerCompatibility.graphical, false);
});

domTest('locale does not reset numeric drafts; restored values clear stale drafts without Undo', async t => {
  const h = setup(); t.after(h.cleanup); const {record} = h.node(); const input = record.ui.root.querySelector('[data-field="body_height"]');
  input.value = '999'; input.dispatchEvent(new Event('input', {bubbles: true})); h.locale('ja');
  assert.equal(input.value, '999'); assert.match(input.parentElement.parentElement.textContent, /未確定/); assert.equal(h.transactions.length, 0);
  record.widget.value = DEFAULT_JSON; assert.equal(input.value, '1120'); assert.equal(h.transactions.length, 0);
});

domTest('afterConfigureGraph re-reads standard widget restoration without writing defaults or history', t => {
  const h = setup(); t.after(h.cleanup); const {record, item} = h.node(); const state = structuredClone(DEFAULT_STATE); state.views = ['body_left'];
  const restored = JSON.stringify(state, null, 2); record.widget.value = restored;
  createExtension(h.app, {}).afterConfigureGraph();
  assert.equal(item.widgets.find(w => w.name === 'state_json').value, restored); assert.deepEqual(record.controller.state.views, ['body_left']); assert.equal(h.transactions.length, 0);
});

domTest('append-then-throw DOM setup rolls back registry, hooks, and extra serialized widget', t => {
  const h = setup(); t.after(h.cleanup); const original = {name: 'state_json', value: DEFAULT_JSON, options: {}}; let removed = false;
  const priorAdded = () => 'original';
  const node = {widgets: [original], onAdded: priorAdded, addDOMWidget(name, type, element, options) {
    const candidate = {name, type, element, options, onRemove() { removed = true; }};
    this.widgets.push(candidate); this.onAdded = () => 'leaked callback'; throw new Error('partly installed');
  }};
  assert.equal(installDesigner(node, h.app, {}), null); assert.deepEqual(node.widgets, [original]); assert.equal(removed, true); assert.equal(node.onAdded, priorAdded);
});
