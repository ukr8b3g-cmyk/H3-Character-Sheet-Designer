import test from 'node:test';
import assert from 'node:assert/strict';
import {pathToFileURL} from 'node:url';
import {DEFAULT_JSON, parseReference13State, VIEW_IDS} from '../../web/reference13_state.js';
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
  function node(type = 'H3CharacterSheetDesignerReference13') {
    const element = document.createElement('textarea'); element.value = DEFAULT_JSON;
    const original = {name: 'state_json', value: DEFAULT_JSON, type: 'customtext', element, options: {}};
    const native = [{name: 'use_layout_image', value: false}, {name: 'style', value: 'none'}];
    const item = {type, widgets: [original, ...native], graph,
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
    const request = requests[index];
    const state = parseReference13State(JSON.parse(request.options.body).state_json, undefined, request.path.includes('/minimax_image/'));
    const layout = {canvas: [2208, 1280], feet_y: null,
      panels: state.views.map((id, i) => ({id, rect: [i / state.views.length, 0, 1 / state.views.length, 1]}))};
    request.resolve({ok: true, json: async () => ({width: 2208, height: 1280, max_resolution: 16384,
      layout, semantic_layout: layout, prompt, default_view_prompts: Object.fromEntries(VIEW_IDS.map(v => [v, "Native H3 " + v])), view_prompts: ["Panel example"]})});
  }
  return {node, app, api, requests, transactions, resolve,
    locale(value) { locale = value; settings.dispatchEvent(new Event('Comfy.Locale.change')); },
    cleanup() { for (const node of nodes) node.onRemoved?.(); dom.window.close(); for (const name of names) {
      if (saved[name] === undefined) delete globalThis[name]; else globalThis[name] = saved[name];
    } }};
}

domTest('MiniMax H3 Image saves Auto resolution and restores it after Manual and reload', async t => {
  const h = setup(); t.after(h.cleanup);
  const {item, original, record} = h.node('MiniMaxH3ImageCharacterSheetDesigner');
  const root = record.ui.root;
  const resolution = root.querySelector('[data-resolution-profile]');
  assert.equal(resolution.value, 'current');
  choose(resolution, 'high');
  const saved = item.serialize().widgets_values[0];
  assert.equal(JSON.parse(saved).resolution_profile, 'high');
  choose(resolution, 'max_8mp');
  const savedEight = item.serialize().widgets_values[0];
  assert.equal(JSON.parse(savedEight).resolution_profile, 'max_8mp');
  choose(resolution, 'max_16mp');
  const savedSixteen = item.serialize().widgets_values[0];
  assert.equal(JSON.parse(JSON.parse(h.requests.at(-1).options.body).state_json).resolution_profile, 'max_16mp');
  h.resolve(); await tick();
  root.querySelector('[data-mode="manual"]').click();
  assert.equal(JSON.parse(original.value).size.mode, 'manual');
  assert(resolution.disabled);
  root.querySelector('[data-mode="auto"]').click();
  assert.equal(resolution.value, 'max_16mp');
  assert(!resolution.disabled);
  original.value = savedEight; item.onConfigure();
  assert.equal(resolution.value, 'max_8mp');
  original.value = savedSixteen; item.onConfigure();
  assert.equal(resolution.value, 'max_16mp');
  original.value = saved; item.onConfigure();
  assert.equal(resolution.value, 'high');
  h.locale('ja');
  assert.equal(resolution.selectedOptions[0].textContent, '高精細');
  choose(resolution, 'current');
  assert(!Object.hasOwn(JSON.parse(original.value), 'resolution_profile'));
  const legacy = h.node('H3CharacterSheetDesignerReferenceV13');
  assert.equal(legacy.record.ui.root.querySelector('[data-resolution-profile]'), null);
});
for (const nodeType of ['H3CharacterSheetDesignerReferenceV13', 'MiniMaxH3ImageCharacterSheetDesigner']) {
domTest(`${nodeType} editor flushes, reloads, resets and retains reference switches`, async t => {
  const h = setup(); t.after(h.cleanup);
  const {item, original, record} = h.node(nodeType);
  h.resolve(); await tick();
  const root = record.ui.root;
  root.querySelector('[data-tab="prompts"]').click();
  const panel = root.querySelector('[id$="-prompts-panel"]');
  const input = panel.querySelector('textarea');
  assert.equal(input.value, 'Native H3 face_front');
  input.value = 'H3 custom portrait'; input.dispatchEvent(new Event('input', {bubbles:true}));
  const saved = item.serialize().widgets_values[0];
  assert.equal(JSON.parse(saved).view_prompts.face_front, 'H3 custom portrait');
  original.value = DEFAULT_JSON; item.onConfigure();
  original.value = saved; item.onConfigure();
  assert.equal(input.value, 'H3 custom portrait');
  h.resolve(); await tick();
  const select = panel.querySelector('select');
  choose(select, 'clothing_back');
  input.value = ''; input.dispatchEvent(new Event('input', {bubbles:true}));
  panel.querySelector('button').click();
  assert.equal(JSON.parse(original.value).view_prompts.clothing_back, '');
  panel.querySelectorAll('button')[1].click();
  assert.equal(Object.hasOwn(JSON.parse(original.value).view_prompts, 'clothing_back'), false);
  choose(select, 'face_front');
  input.value = 'x'.repeat(2001); input.dispatchEvent(new Event('input', {bubbles:true}));
  assert.throws(() => item.serialize());
  assert.equal(JSON.parse(original.value).view_prompts.face_front, 'H3 custom portrait');
  h.locale('ja');
  assert.equal(root.querySelector('[data-tab="prompts"]').textContent, 'プロンプト');
  assert.equal(panel.querySelector('button').textContent, '適用');
  const native = item.widgets.filter(w => ['use_layout_image','style'].includes(w.name));
  assert.deepEqual(native.map(w=>w.value), [false,'none']);
  if (nodeType === 'MiniMaxH3ImageCharacterSheetDesigner') {
    assert(h.requests.every(r => r.path === '/h3_character_sheet_designer/minimax_image/preview'));
    assert(root.textContent.includes('v1.4.0'));
  }
});
}
