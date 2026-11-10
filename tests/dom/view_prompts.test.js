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
    const request = requests[index], state = parseReference13State(JSON.parse(request.options.body).state_json);
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
domTest('V1.3 editor flushes, reloads, resets and retains reference switches', async t => {
  const h = setup(); t.after(h.cleanup);
  const {item, original, record} = h.node('H3CharacterSheetDesignerReferenceV13');
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
});
