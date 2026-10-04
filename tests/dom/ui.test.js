import test from 'node:test';
import assert from 'node:assert/strict';
import {pathToFileURL} from 'node:url';
import {readFileSync} from 'node:fs';
import {spawnSync} from 'node:child_process';
import {DEFAULT_JSON, parseState, serializeState, DEFAULT_STATE, PRESETS, VIEW_IDS, PART_IDS, migratePartState} from '../../web/state.js';
let JSDOM;
try { ({JSDOM} = await import(process.env.H3_JSDOM_PATH ? pathToFileURL(process.env.H3_JSDOM_PATH).href : 'jsdom')); } catch {}
const domTest = (name, fn) => test(name, {skip: !JSDOM && 'Optional jsdom is unavailable; set H3_JSDOM_PATH to its api.js or install jsdom for DOM tests.'}, fn);
let installDesigner, createExtension;
if (JSDOM) ({installDesigner, createExtension} = await import('../../web/integration.js'));
const tick = () => new Promise(resolve => setImmediate(resolve));
function choose(select, value) { select.value = value; select.dispatchEvent(new Event('change', {bubbles: true})); }
function customHeight(root) { choose(root.querySelector('[data-height-presets]'), 'custom'); return root.querySelector('[data-field="body_height"]'); }
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
  function node(raw = DEFAULT_JSON, prefixWidget = false, size = [300, 100]) {
    const element = document.createElement('textarea'); element.value = raw;
    const original = {name: 'state_json', type: 'customtext', value: raw, options: {}, element, onRemove() { registry.delete(original); element.remove(); }};
    const item = {type: 'H3CharacterSheetDesigner', comfyClass: 'H3CharacterSheetDesigner', size, widgets: prefixWidget ? [{name: 'other', value: 'kept'}, original] : [original], graph, onConfigure() { return 'configure-original'; }, onRemoved() { return 'remove-original'; }, onAdded() { registry.add(original); return 'add-original'; },
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
  const h = setup(); t.after(h.cleanup); const {record} = h.node(); const input = customHeight(record.ui.root);
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
  assert.equal(record.ui.root.querySelector('.h3-json-editor textarea').value, bad);
  record.ui.root.querySelector('.h3-json-editor textarea').value = DEFAULT_JSON; record.ui.root.querySelector('.h3-apply').click(); assert.equal(record.widget.value, DEFAULT_JSON); assert.equal(h.transactions.length, 2);
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
  const h = setup(); t.after(h.cleanup); const {record} = h.node(); const input = customHeight(record.ui.root);
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


domTest('new nodes match the supplied 870×930 size and never shrink a larger node', t => {
  const h = setup(); t.after(h.cleanup); const {item, record} = h.node();
  assert.deepEqual(item.size, [870, 930]);
  assert.equal(record.widget.options.getMinHeight(), 760);
  assert.equal(record.widget.options.getHeight(), 840);
  const larger = h.node(DEFAULT_JSON, false, [1100, 1200]);
  assert.deepEqual(larger.item.size, [1100, 1200]);
});

domTest('both dropdowns are full controls; height shows its selected value and every preset commits once', t => {
  const h = setup(); t.after(h.cleanup); const {record} = h.node(); const root = record.ui.root;
  const selects = [...root.querySelectorAll('select')]; assert.equal(selects.length, 3);
  for (const select of selects) {
    assert.ok(select.classList.contains('h3-select'));
    assert.equal(root.querySelector(`label[for="${select.id}"]`)?.control, select);
    assert.equal(select.multiple, false);
  }
  const height = root.querySelector('[data-height-presets]'), input = root.querySelector('[data-field="body_height"]');
  assert.equal(height.value, '1120'); assert.equal(input.hidden, true); assert.equal(input.disabled, true);
  assert.deepEqual([...height.options].map(option => option.value), ['672', '896', '1120', '1344', '1792', 'custom']);
  for (const value of ['672', '896', '1120', '1344', '1792']) {
    const count = h.transactions.length; choose(height, value);
    assert.equal(record.controller.state.size.body_height, Number(value));
    assert.equal(height.value, value); assert.equal(input.hidden, true);
    assert.equal(h.transactions.length, count + 2);
  }
  const count = h.transactions.length; choose(height, '1792'); assert.equal(h.transactions.length, count);
});

domTest('custom height is explicit, focuses its editor, and Escape cancels without saving', t => {
  const h = setup(); t.after(h.cleanup); const {record} = h.node(); const root = record.ui.root;
  const input = customHeight(root), height = root.querySelector('[data-height-presets]');
  assert.equal(input.hidden, false); assert.equal(input.disabled, false); assert.equal(document.activeElement, input);
  assert.equal(record.controller.raw, DEFAULT_JSON); assert.equal(h.transactions.length, 0);
  input.value = '999'; input.dispatchEvent(new Event('input', {bubbles: true}));
  input.dispatchEvent(new KeyboardEvent('keydown', {key: 'Escape', bubbles: true}));
  assert.equal(record.controller.raw, DEFAULT_JSON); assert.equal(h.transactions.length, 0);
  assert.equal(height.value, '1120'); assert.equal(input.hidden, true); assert.equal(document.activeElement, height);
});

domTest('custom heights survive save/restore and are not replaced by the nearest dropdown preset', t => {
  const h = setup(); t.after(h.cleanup); const {record} = h.node(); const root = record.ui.root;
  const input = customHeight(root); input.value = '1024'; input.dispatchEvent(new Event('input', {bubbles: true}));
  input.dispatchEvent(new KeyboardEvent('keydown', {key: 'Enter', bubbles: true}));
  assert.equal(record.controller.state.size.body_height, 1024); assert.equal(h.transactions.length, 2);
  const saved = record.widget.value; record.widget.value = saved;
  assert.equal(root.querySelector('[data-height-presets]').value, 'custom'); assert.equal(input.hidden, false); assert.equal(input.value, '1024');
  record.widget.value = DEFAULT_JSON; assert.equal(input.hidden, true); assert.equal(root.querySelector('[data-height-presets]').value, '1120');
});

domTest('choosing a preset discards an invalid custom draft and restores normal validation state', t => {
  const h = setup(); t.after(h.cleanup); const {record} = h.node(); const root = record.ui.root;
  const input = customHeight(root); input.value = '673'; input.dispatchEvent(new Event('input', {bubbles: true})); input.dispatchEvent(new Event('blur'));
  assert.equal(input.getAttribute('aria-invalid'), 'true');
  choose(root.querySelector('[data-height-presets]'), '672');
  assert.equal(input.hidden, true); assert.equal(input.getAttribute('aria-invalid'), 'false');
  assert.equal(root.querySelector('.h3-draft-note').textContent, ''); assert.equal(record.controller.state.size.body_height, 672);
});

domTest('every view preset selects its documented views and Manual dimensions survive', async t => {
  const h = setup(); t.after(h.cleanup); const {record} = h.node(); const root = record.ui.root;
  h.resolve(); await tick(); root.querySelector('[data-mode="manual"]').click();
  const size = {...record.controller.state.size};
  for (const [name, expected] of Object.entries(PRESETS)) {
    choose(root.querySelector('#' + root.dataset.instance + '-preset'), name);
    assert.deepEqual(record.controller.state.views, expected); assert.deepEqual(record.controller.state.size, size);
    assert.equal(root.querySelector('select.h3-select').value, name);
  }
  assert.equal(root.querySelector('[data-height-presets]').disabled, true);
  root.querySelector('.h3-link-button').click(); assert.equal(record.controller.state.size.mode, 'auto');
  assert.equal(root.querySelector('[data-height-presets]').disabled, false);
});

domTest('all seven view buttons stay selectable, update Custom, and protect the final view', t => {
  const h = setup(); t.after(h.cleanup); const {record} = h.node(); const root = record.ui.root;
  choose(root.querySelector('select.h3-select'), 'detail');
  const cards = [...root.querySelectorAll('.h3-card')]; assert.equal(cards.length, VIEW_IDS.length);
  for (const card of cards.slice(0, -1)) { card.click(); assert.equal(card.getAttribute('aria-pressed'), 'false'); }
  const last = cards.at(-1); last.click(); assert.equal(last.getAttribute('aria-pressed'), 'true');
  assert.equal(record.controller.state.views.length, 1); assert.equal(root.querySelector('select.h3-select').value, 'custom');
  assert.equal(root.querySelector('select.h3-select option[value="custom"]').disabled, true);
});

domTest('locale updates both dropdown labels without losing a custom draft or adding history', t => {
  const h = setup(); t.after(h.cleanup); const {record} = h.node(); const root = record.ui.root;
  const input = customHeight(root); input.value = '1024'; input.dispatchEvent(new Event('input', {bubbles: true})); h.locale('ja');
  const height = root.querySelector('[data-height-presets]');
  assert.equal(height.value, 'custom'); assert.equal(height.selectedOptions[0].textContent, '手入力…');
  assert.equal(input.getAttribute('aria-label'), '基準高を手入力'); assert.equal(input.value, '1024'); assert.equal(h.transactions.length, 0);
});

domTest('invalid saved state disables every selection control; disposed controls cannot commit', t => {
  const h = setup(); t.after(h.cleanup); const {record, item} = h.node('{broken'); const root = record.ui.root;
  for (const control of root.querySelectorAll('.h3-card, .h3-mode, select')) assert.equal(control.disabled, true);
  record.widget.value = DEFAULT_JSON; const select = root.querySelector('[data-height-presets]'); item.onRemoved();
  choose(select, '672'); assert.equal(record.widget.value, DEFAULT_JSON); assert.equal(h.transactions.length, 0);
});

domTest('CSS contract keeps dropdowns full-width and key text readable (not a layout test)', t => {
  const h = setup(); t.after(h.cleanup);
  const style = document.createElement('style'); style.textContent = readFileSync(new URL('../../web/style.css', import.meta.url), 'utf8'); document.head.append(style);
  const {record} = h.node(); const root = record.ui.root;
  assert.equal(window.getComputedStyle(root).fontSize, '18px');
  assert.equal(window.getComputedStyle(root.querySelector('.h3-card-label')).fontSize, '16px');
  assert.equal(window.getComputedStyle(root.querySelector('.h3-number-field label')).fontSize, '16px');
  for (const select of root.querySelectorAll('select')) {
    const css = window.getComputedStyle(select); assert.equal(css.width, '100%'); assert.equal(css.height, '40px'); assert.equal(css.appearance, 'auto');
  }
});

domTest('every footwear selection reaches saved input, Python layout, prompt, and node STRING output', t => {
  const h = setup(); t.after(h.cleanup); const {record, item} = h.node();
  const root = record.ui.root, saved = [];
  for (let bits = 1; bits < 1 << VIEW_IDS.length; bits++) {
    const target = VIEW_IDS.filter((_, i) => bits & (1 << i));
    const state = structuredClone(DEFAULT_STATE);
    // Arrive at every target through a real button click, with preview pending.
    const onlyFeet = target.length === 1 && target[0] === 'feet';
    state.views = onlyFeet ? ['hands', 'feet'] : target.includes('feet') ? target.filter(v => v !== 'feet') : [...target, 'feet'];
    record.widget.value = serializeState(state);
    root.querySelector(`[data-view="${onlyFeet ? 'hands' : 'feet'}"]`).click();
    const raw = item.widgets.find(w => w.name === 'state_json').value;
    assert.deepEqual(parseState(raw).views, target);
    assert.equal(JSON.parse(h.requests.at(-1).opts.body).state_json, raw);
    assert.equal(root.querySelector('[data-view="feet"]').getAttribute('aria-pressed'), String(target.includes('feet')));
    saved.push(raw);
  }
  const script = `import sys,json,types
sys.modules['nodes'] = types.SimpleNamespace(MAX_RESOLUTION=16384)
from h3_character_sheet.compiler import compile_state
from h3_character_sheet.node import H3CharacterSheetDesigner
result=[]
for raw in json.load(sys.stdin):
    compiled=compile_state(raw)
    prompt,width,height=H3CharacterSheetDesigner().compile(raw)
    assert (prompt,width,height)==(compiled['prompt'],compiled['width'],compiled['height'])
    result.append({'views':[p['id'] for p in compiled['layout']['panels']],'prompt':prompt})
json.dump(result,sys.stdout)`;
  const run = spawnSync(process.env.PYTHON ?? 'python', ['-c', script], {cwd: new URL('../..', import.meta.url), input: JSON.stringify(saved), encoding: 'utf8', maxBuffer: 4 * 1024 * 1024});
  assert.equal(run.status, 0, run.stderr || run.error?.message);
  const outputs = JSON.parse(run.stdout);
  assert.equal(outputs.length, 127);
  outputs.forEach((out, i) => {
    const views = parseState(saved[i]).views;
    assert.deepEqual(out.views, views);
    assert.equal(out.prompt.includes('"id":"feet"'), views.includes('feet'));
    assert.equal(out.prompt.includes('required separate panel'), views.includes('feet'));
  });
});

domTest('profile is optional, saved immediately, restored with Manual dimensions, and localized', async t => {
  const h = setup(); t.after(h.cleanup); const {record} = h.node(); const root = record.ui.root;
  const card = root.querySelector('[data-view="face_left"]');
  assert.equal(card.getAttribute('aria-pressed'), 'false');
  assert.match(card.title, /anatomical left/);
  assert.equal(root.querySelector('.h3-count').textContent, '4 / 7 selected');
  card.click(); const raw = record.widget.value;
  assert.deepEqual(parseState(raw).views, ['face_front', 'face_left', 'body_front', 'body_left', 'body_back']);
  h.resolve(undefined, 2816, 1280); await tick();
  assert(root.querySelector('[data-panel="face_left"] [data-artwork="face_left"]'));
  root.querySelector('[data-mode="manual"]').click();
  const manual = record.widget.value;
  assert.deepEqual(parseState(manual).size, {...DEFAULT_STATE.size, mode: 'manual', manual_width: 2816});
  record.widget.value = DEFAULT_JSON; record.widget.value = manual;
  const transactions = h.transactions.length;
  h.locale('ja'); assert.equal(card.querySelector('.h3-card-label').textContent, '横顔・左');
  assert.match(card.title, /解剖学的左側/); assert.equal(record.widget.value, manual);
  h.locale('en'); assert.equal(card.querySelector('.h3-card-label').textContent, 'Left portrait');
  assert.equal(h.transactions.length, transactions);
  card.click(); assert.equal(parseState(record.widget.value).size.manual_width, 2816);
});


function partEditor(record, part = 'footwear') {
  const root = record.ui.root; root.querySelector('[data-tab="parts"]').click();
  choose(root.querySelector('[data-part-select]'), part); return root.querySelector('[data-part-prompt]');
}
function typePart(input, text) { input.value = text; input.dispatchEvent(new Event('input', {bubbles: true})); }

domTest('part tab has only eight-part dropdown and one free prompt, and reuses the preview area', t => {
  const h = setup(); t.after(h.cleanup); const {record} = h.node(); const root = record.ui.root;
  const original = record.widget.value, editor = partEditor(record);
  assert.equal(root.querySelectorAll('.h3-part-panel select').length, 1);
  assert.equal(root.querySelectorAll('.h3-part-panel textarea').length, 1);
  assert.equal(root.querySelectorAll('.h3-part-panel input, .h3-part-panel button').length, 0);
  assert.deepEqual([...root.querySelector('[data-part-select]').options].map(o => o.value), PART_IDS);
  assert.equal(editor.maxLength, 1000); assert.equal(root.querySelector('.h3-stage').hidden, true);
  assert.equal(root.querySelector('.h3-part-panel').hidden, false);
  assert.equal(record.widget.value, original); assert.equal(h.transactions.length, 0);
  root.querySelector('[data-tab="layout"]').click();
  assert.equal(root.querySelector('.h3-stage').hidden, false); assert.equal(root.querySelector('.h3-part-panel').hidden, true);
  assert.equal(record.widget.value, original);
});

domTest('part typing is saved before immediate Queue, with no blur/Enter duplicate transaction', t => {
  const h = setup(); t.after(h.cleanup); const {record} = h.node(); const input = partEditor(record);
  typePart(input, '黒いロングブーツ');
  assert.equal(JSON.parse(record.widget.value).part_prompts.footwear, '黒いロングブーツ');
  assert.equal(h.transactions.length, 2); assert.equal(record.controller.pending, true);
  const enter = new KeyboardEvent('keydown', {key: 'Enter', bubbles: true, cancelable: true}); input.dispatchEvent(enter);
  assert.equal(enter.defaultPrevented, false); assert.equal(h.transactions.length, 2);
  input.dispatchEvent(new Event('blur')); assert.equal(h.transactions.length, 2);
  assert.match(record.ui.root.querySelector('[data-tab="parts"]').textContent, /1/);
  assert.match(record.ui.root.querySelector('[data-part-select] option[value="footwear"]').textContent, /●/);
});

domTest('IME composing Enter and multiline text preserve input, caret and literal punctuation', t => {
  const h = setup(); t.after(h.cleanup); const {record} = h.node(); const input = partEditor(record, 'back_clothing');
  input.focus(); input.dispatchEvent(new Event('compositionstart'));
  typePart(input, '背面の花'); input.setSelectionRange(3, 3);
  const event = new KeyboardEvent('keydown', {key: 'Enter', isComposing: true, bubbles: true, cancelable: true}); input.dispatchEvent(event);
  assert.equal(event.defaultPrevented, false); assert.equal(input.selectionStart, 3);
  const text = '背面に"FLOWER"\n{赤|青}の花柄 C:\\pattern 🌸';
  typePart(input, text); input.dispatchEvent(new Event('compositionend'));
  assert.equal(record.controller.state.part_prompts.back_clothing, text); assert.equal(input.value, text);
  const before = h.transactions.length; input.dispatchEvent(new Event('blur')); assert.equal(h.transactions.length, before);
});

domTest('part text survives part/tab/preset/view/locale switches and clearing affects only one part', t => {
  const h = setup(); t.after(h.cleanup); const {record} = h.node(); const root = record.ui.root;
  const input = partEditor(record, 'lower_body'); typePart(input, '黒いロングパンツ');
  choose(root.querySelector('[data-part-select]'), 'footwear'); assert.equal(input.value, ''); typePart(input, '黒いブーツ');
  choose(root.querySelector('[data-part-select]'), 'lower_body'); assert.equal(input.value, '黒いロングパンツ');
  root.querySelector('[data-tab="layout"]').click(); choose(root.querySelector('select.h3-select'), 'detail');
  root.querySelector('[data-view="feet"]').click(); root.querySelector('[data-tab="parts"]').click();
  const saved = record.widget.value, count = h.transactions.length; h.locale('ja');
  assert.equal(input.value, '黒いロングパンツ'); assert.equal(record.widget.value, saved); assert.equal(h.transactions.length, count);
  assert.match(root.querySelector('[data-tab="parts"]').textContent, /部位指定/);
  assert.match(root.querySelector('[data-part-select] option[value="other"]').textContent, /全体・その他/);
  typePart(input, ''); assert.deepEqual(record.controller.state.part_prompts, {footwear: '黒いブーツ'});
  assert.equal(record.controller.state.views.includes('feet'), false);
});

domTest('part saved-state restore/Undo/Redo and duplicate are independent of editor drafts', t => {
  const h = setup(); t.after(h.cleanup); const {record} = h.node(); const input = partEditor(record, 'face');
  typePart(input, 'サングラス'); const saved = record.widget.value, second = h.node(saved);
  typePart(input, '丸いサングラス'); assert.equal(second.record.controller.state.part_prompts.face, 'サングラス');
  const count = h.transactions.length;
  record.widget.value = DEFAULT_JSON; assert.equal(input.value, ''); assert.equal(record.controller.state.schema_version, 1);
  record.widget.value = saved; assert.equal(input.value, 'サングラス'); assert.equal(h.transactions.length, count);
  const restored = h.node(record.widget.value); assert.equal(partEditor(restored.record, 'face').value, 'サングラス');
});

domTest('part limits retain the saved value and visible bad draft until corrected or restored', t => {
  const h = setup(); t.after(h.cleanup); const {record} = h.node(); const input = partEditor(record);
  typePart(input, '白い靴'); const saved = record.widget.value;
  typePart(input, 'x'.repeat(1001)); assert.equal(record.widget.value, saved); assert.equal(input.value.length, 1001); assert.equal(input.getAttribute('aria-invalid'), 'true');
  choose(record.ui.root.querySelector('[data-part-select]'), 'face'); choose(record.ui.root.querySelector('[data-part-select]'), 'footwear');
  assert.equal(input.value.length, 1001); assert.equal(record.widget.value, saved);
  record.widget.value = saved; assert.equal(input.value, '白い靴'); assert.equal(input.getAttribute('aria-invalid'), 'false');
  typePart(input, '  '); assert.equal(input.value, '  '); assert.deepEqual(record.controller.state.part_prompts, {});
  typePart(input, '  白い靴  '); assert.equal(record.controller.state.part_prompts.footwear, '  白い靴  ');
});

domTest('tabs and part editor expose accessible labels and keyboard navigation without saving', t => {
  const h = setup(); t.after(h.cleanup); const {record} = h.node(); const root = record.ui.root;
  const layout = root.querySelector('[data-tab="layout"]'), parts = root.querySelector('[data-tab="parts"]');
  assert.equal(layout.getAttribute('aria-selected'), 'true'); assert.equal(parts.tabIndex, -1);
  layout.dispatchEvent(new KeyboardEvent('keydown', {key: 'ArrowRight', bubbles: true}));
  assert.equal(parts.getAttribute('aria-selected'), 'true'); assert.equal(document.activeElement, parts);
  assert.equal(root.querySelector('#' + parts.getAttribute('aria-controls')).hidden, false);
  for (const control of root.querySelectorAll('.h3-part-panel select, .h3-part-panel textarea')) assert.equal(root.querySelector(`label[for="${control.id}"]`).control, control);
  parts.dispatchEvent(new KeyboardEvent('keydown', {key: 'Home', bubbles: true})); assert.equal(document.activeElement, layout);
  assert.equal(h.transactions.length, 0);
});

domTest('malformed or unknown v2 state stays intact, disables editor, and requires explicit repair', t => {
  const h = setup(); t.after(h.cleanup);
  const v2 = {...migratePartState(DEFAULT_STATE), schema_version: 999}; const raw = JSON.stringify(v2); const {record} = h.node(raw);
  const input = partEditor(record); assert.equal(input.disabled, true); assert.equal(record.widget.value, raw); assert.equal(h.requests.length, 0);
  assert.equal(record.ui.root.querySelector('.h3-json-editor').hidden, false);
  record.widget.value = JSON.stringify({...migratePartState(DEFAULT_STATE), part_prompts: {footwear: '白い靴'}});
  assert.equal(input.disabled, false); assert.equal(input.value, '白い靴'); assert.equal(h.transactions.length, 0);
});


domTest('opening, blur, part switch and IME end do not rewrite restored CRLF or pretty v2', t => {
  const h = setup(); t.after(h.cleanup);
  const raw = JSON.stringify({...migratePartState(DEFAULT_STATE), part_prompts: {head_hair: 'red\r\nhair'}}, null, 2);
  const {record} = h.node(raw), input = partEditor(record, 'head_hair');
  assert.equal(input.value, 'red\nhair');
  input.dispatchEvent(new Event('blur')); input.dispatchEvent(new Event('compositionend'));
  choose(record.ui.root.querySelector('[data-part-select]'), 'face');
  record.controller.setPartPrompt('head_hair', 'red\r\nhair');
  assert.equal(record.widget.value, raw); assert.equal(h.transactions.length, 0);
});


domTest('part editor cannot flex-shrink below its contents (static CSS contract)', t => {
  const h = setup(); t.after(h.cleanup);
  const style = document.createElement('style'); style.textContent = readFileSync(new URL('../../web/style.css', import.meta.url), 'utf8'); document.head.append(style);
  const {record} = h.node(); partEditor(record);
  const css = window.getComputedStyle(record.ui.root.querySelector('.h3-part-panel'));
  assert.equal(css.flexShrink, '0'); assert.equal(css.minHeight, 'min-content');
});

domTest('free instructions pass from actual editor through saved Queue input into native-node outputs', t => {
  const h = setup(); t.after(h.cleanup); const {record} = h.node(); const saved = [];
  const cases = [
    {lower_body: '黒いロングパンツ', footwear: '黒いブーツ'},
    {hands: '白い手袋'},
    {back_clothing: '背中に花柄と"FLOWER"の文字'},
    {face: 'サングラス', other: '模様は{赤|青}。C:\\literal\n日本語 🌸'},
  ];
  for (const instructions of cases) {
    record.widget.value = DEFAULT_JSON;
    for (const [part, text] of Object.entries(instructions)) typePart(partEditor(record, part), text);
    // Capture immediately with all preview requests still pending.
    saved.push(record.widget.value); assert.equal(record.controller.pending, true);
    assert.deepEqual(parseState(record.widget.value).part_prompts, instructions);
  }
  const script = `import json,sys,types
sys.modules['nodes']=types.SimpleNamespace(MAX_RESOLUTION=16384)
from h3_character_sheet.compiler import compile_state
from h3_character_sheet.node import H3CharacterSheetDesigner
results=[]
for raw in json.load(sys.stdin):
    value=compile_state(raw)
    assert H3CharacterSheetDesigner().compile(raw)==(value['prompt'],value['width'],value['height'])
    results.append({'prompt':value['prompt'],'panels':value['layout']['panels'],'size':[value['width'],value['height']]})
json.dump(results,sys.stdout)`;
  const run = spawnSync(process.env.PYTHON ?? 'python', ['-c', script], {cwd: new URL('../..', import.meta.url), input: JSON.stringify(saved), encoding: 'utf8', maxBuffer: 4 * 1024 * 1024});
  assert.equal(run.status, 0, run.stderr || run.error?.message); const outputs = JSON.parse(run.stdout);
  outputs.forEach((output, i) => {
    assert.deepEqual(output.size, [2208, 1280]);
    for (const text of Object.values(cases[i])) assert.ok(output.prompt.includes(text));
  });
  const boots = outputs[0].panels; assert.equal(boots.some(p => p.id === 'feet'), false);
  for (const view of ['body_front', 'body_left', 'body_back']) assert.ok(boots.find(p => p.id === view).content.includes('黒いブーツ'));
  const back = outputs[2].panels;
  for (const view of ['face_front', 'body_front']) assert.equal(back.find(p => p.id === view).content.includes('FLOWER'), false);
  assert.ok(back.find(p => p.id === 'body_back').content.includes('FLOWER'));
});
