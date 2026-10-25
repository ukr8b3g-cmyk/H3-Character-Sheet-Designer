import test from 'node:test';
import assert from 'node:assert/strict';
import {pathToFileURL} from 'node:url';
import {DEFAULT_JSON, parseReference13State} from '../../web/reference13_state.js';
import {installDesigner} from '../../web/reference13_integration.js';
let JSDOM;
try { ({JSDOM} = await import(process.env.H3_JSDOM_PATH ? pathToFileURL(process.env.H3_JSDOM_PATH).href : 'jsdom')); } catch {}
const domTest = (name, fn) => test(name, {skip: !JSDOM && 'Set H3_JSDOM_PATH to the declared jsdom dependency.'}, fn);
const tick = () => new Promise(resolve => setImmediate(resolve));
const choose = (node, value) => { node.value = value; node.dispatchEvent(new Event('change', {bubbles: true})); };

function setup() {
  const dom = new JSDOM('<!doctype html><body></body>', {url: 'http://localhost/'});
  const names = ['window', 'document', 'AbortController', 'Event', 'KeyboardEvent', 'HTMLElement'];
  const saved = Object.fromEntries(names.map(name => [name, globalThis[name]]));
  for (const name of names) globalThis[name] = dom.window[name];
  let locale = 'en';
  const settings = new dom.window.EventTarget(), requests = [], transactions = [], nodes = [];
  const graph = {_nodes: nodes,
    beforeChange(node) { transactions.push({node, phase: 'before', raw: node.widgets[0].value}); },
    afterChange(node) { transactions.push({node, phase: 'after', raw: node.widgets[0].value}); }};
  const app = {graph, ui: {settings}, extensionManager: {setting: {get: () => locale}}};
  const api = {fetchApi(path, options) { return new Promise(resolve => requests.push({path, options, resolve})); }};
  function node() {
    const element = document.createElement('textarea'); element.value = DEFAULT_JSON;
    const original = {name: 'state_json', value: DEFAULT_JSON, type: 'customtext', element, options: {}};
    const native = [{name: 'use_layout_image', value: false}, {name: 'style', value: 'none'}];
    const item = {type: 'H3CharacterSheetDesignerReference13', widgets: [original, ...native], graph,
      size: [300, 100], inputs: [1, 2, 3].map(i => ({name: `reference_image_${i}`, link: null})),
      onAdded() { return 'added'; }, onRemoved() { return 'removed'; }, onConfigure() { return 'configured'; },
      isInputConnected(index) { return this.inputs[index].link !== null; },
      setSize(value) { this.size = value; }, setDirtyCanvas() {},
      serialize() { return {widgets_values: this.widgets.filter(w => w.serialize !== false).map(w => w.value)}; },
      addDOMWidget(name, type, element, options) {
        const widget = {name, type, element, options, onRemove() { element.remove(); }};
        Object.defineProperty(widget, 'value', {get: options.getValue, set: options.setValue});
        this.widgets.push(widget); document.body.append(element); return widget;
      }};
    nodes.push(item); const record = installDesigner(item, app, api);
    assert(record, 'actual Reference13 installDesigner must install its real UI');
    return {item, original, record};
  }
  function resolve(index = requests.length - 1, prompt = 'current preview') {
    const request = requests[index], state = parseReference13State(JSON.parse(request.options.body).state_json);
    const layout = {canvas: [2208, 1280], feet_y: null,
      panels: state.views.map((id, i) => ({id, rect: [i / state.views.length, 0, 1 / state.views.length, 1]}))};
    request.resolve({ok: true, json: async () => ({width: 2208, height: 1280, max_resolution: 16384,
      layout, semantic_layout: layout, prompt})});
  }
  return {node, app, api, requests, transactions, resolve,
    locale(value) { locale = value; settings.dispatchEvent(new Event('Comfy.Locale.change')); },
    cleanup() { for (const node of nodes) node.onRemoved?.(); dom.window.close(); for (const name of names) {
      if (saved[name] === undefined) delete globalThis[name]; else globalThis[name] = saved[name];
    } }};
}
function draftHeight(record, value) {
  choose(record.ui.root.querySelector('[data-height-presets]'), 'custom');
  const input = record.ui.root.querySelector('[data-field="body_height"]');
  input.value = value; input.dispatchEvent(new Event('input', {bubbles: true})); return input;
}

domTest('Reference13 real DOM has three roles and four independent saved appearance controls', t => {
  const h = setup(); t.after(h.cleanup); const {item, original, record} = h.node(); const root = record.ui.root;
  assert.equal(root.querySelectorAll('[data-reference-role]').length, 3);
  for (const [index, role] of ['head', 'clothing_back', 'footwear'].entries()) choose(root.querySelector(`[data-reference-role="reference_image_${index + 1}"]`), role);
  for (const [field, value] of Object.entries({hand_state: 'gloved', clothing_type: 'pants', footwear_state: 'unshod'})) choose(root.querySelector(`[data-appearance-choice="${field}"]`), value);
  root.querySelector('[data-view="clothing_front"]').click();
  root.querySelector('[data-clothing-mode="garment"]').click();
  const serialized = item.serialize(); assert.equal(serialized.widgets_values.length, 3);
  const state = parseReference13State(serialized.widgets_values[0]);
  assert.deepEqual(state.reference_roles, {reference_image_1: 'head', reference_image_2: 'clothing_back', reference_image_3: 'footwear'});
  assert.equal(state.hand_state, 'gloved'); assert.equal(state.clothing_mode, 'garment');
  assert.equal(state.clothing_type, 'pants'); assert.equal(state.footwear_state, 'unshod');
  assert.equal(item.widgets[0], original); assert.equal(record.widget.serialize, false);
  const saved = original.value; h.locale('ja'); assert.equal(root.lang, 'ja'); assert.equal(original.value, saved);
});
domTest('input followed immediately by serialize flushes the Reference13 numeric draft', t => {
  const h = setup(); t.after(h.cleanup); const {item, original, record} = h.node();
  draftHeight(record, '1344'); assert.equal(parseReference13State(original.value).size.body_height, 1120);
  const state = parseReference13State(item.serialize().widgets_values[0]);
  assert.equal(state.size.body_height, 1344); assert.equal(h.transactions.length, 2);
});
domTest('invalid numeric draft blocks serialize without overwriting the canonical state', t => {
  const h = setup(); t.after(h.cleanup); const {item, original, record} = h.node();
  draftHeight(record, '673'); assert.throws(() => item.serialize()); assert.equal(original.value, DEFAULT_JSON);
  assert.equal(record.ui.root.querySelector('[data-field="body_height"]').getAttribute('aria-invalid'), 'true');
  draftHeight(record, '672'); assert.equal(parseReference13State(item.serialize().widgets_values[0]).size.body_height, 672);
});
domTest('invalid part draft also blocks workflow serialization', t => {
  const h = setup(); t.after(h.cleanup); const {item, original, record} = h.node();
  const input = record.ui.root.querySelector('[data-part-prompt]'); input.value = 'x'.repeat(1001);
  input.dispatchEvent(new Event('input', {bubbles: true}));
  assert.throws(() => item.serialize()); assert.equal(original.value, DEFAULT_JSON);
  input.value = 'silver pin'; input.dispatchEvent(new Event('input', {bubbles: true}));
  assert.doesNotThrow(() => item.serialize()); assert(original.value.includes('silver pin'));
});
domTest('canonical restore drives real DOM for Undo/Redo and configuration reload', t => {
  const h = setup(); t.after(h.cleanup); const {item, original, record} = h.node();
  const control = record.ui.root.querySelector('[data-appearance-choice="hand_state"]');
  choose(control, 'gloved'); const after = original.value;
  assert.equal(h.transactions.length, 2);
  original.value = DEFAULT_JSON; assert.equal(item.onConfigure(), 'configured'); assert.equal(control.value, 'reference');
  original.value = after; item.onConfigure(); assert.equal(control.value, 'gloved');
  assert.equal(item.serialize().widgets_values[0], after);
});
domTest('remove then re-add the same node reinstalls one UI and a working serialize hook', t => {
  const h = setup(); t.after(h.cleanup); const {item, original, record} = h.node();
  const role = record.ui.root.querySelector('[data-reference-role="reference_image_3"]'); choose(role, 'hands');
  const saved = original.value; assert.equal(item.onRemoved(), 'removed'); assert(record.disposed);
  assert.equal(item.widgets.filter(w => w.name.startsWith('h3_designer_ui')).length, 0);
  assert.equal(item.onAdded(), 'added'); const fresh = installDesigner(item, h.app, h.api);
  assert(fresh); assert.notEqual(fresh, record); assert.equal(item.widgets.filter(w => w.name.startsWith('h3_designer_ui')).length, 1);
  assert.equal(original.value, saved); assert.equal(fresh.ui.root.querySelector('[data-reference-role="reference_image_3"]').value, 'hands');
  draftHeight(fresh, '1344'); assert.equal(parseReference13State(item.serialize().widgets_values[0]).size.body_height, 1344);
});
domTest('late Reference13 response cannot replace the current three-role preview', async t => {
  const h = setup(); t.after(h.cleanup); const {record} = h.node(); const old = h.requests.length - 1;
  choose(record.ui.root.querySelector('[data-reference-role="reference_image_3"]'), 'head');
  const current = h.requests.length - 1; assert(current > old);
  h.resolve(current, 'new role result'); await tick(); h.resolve(old, 'stale result'); await tick();
  assert.equal(record.controller.preview.prompt, 'new role result');
});
domTest('two Reference13 nodes keep independent drafts, role choices and native widgets', t => {
  const h = setup(); t.after(h.cleanup); const a = h.node(), b = h.node();
  choose(a.record.ui.root.querySelector('[data-reference-role="reference_image_2"]'), 'clothing');
  draftHeight(a.record, '1344'); a.item.serialize();
  assert.equal(b.original.value, DEFAULT_JSON); assert.equal(b.record.ui.root.querySelector('[data-field="body_height"]').value, '1120');
  assert.equal(b.item.widgets.find(w => w.name === 'style').value, 'none');
});
