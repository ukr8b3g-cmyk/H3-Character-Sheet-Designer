import test from 'node:test';
import assert from 'node:assert/strict';
import {pathToFileURL} from 'node:url';
import {DesignerController, DEFAULT_JSON} from '../../web/state.js';
import {Reference13Controller, DEFAULT_JSON as REFERENCE13_JSON} from '../../web/reference13_state.js';
import {createDesignerUI} from '../../web/ui.js';
import {createDesignerUI as createReference13UI} from '../../web/reference13_ui.js';

let JSDOM;
try { ({JSDOM} = await import(process.env.H3_JSDOM_PATH ? pathToFileURL(process.env.H3_JSDOM_PATH).href : 'jsdom')); } catch {}
const domTest = (name, fn) => test(name, {skip: !JSDOM && 'Set H3_JSDOM_PATH to the declared jsdom dependency.'}, fn);
const choose = (select, value) => { select.value = value; select.dispatchEvent(new Event('change', {bubbles: true})); };

function setup({Controller, createUI, initial, reference}, raw = initial) {
  const dom = new JSDOM('<!doctype html><html><head></head><body></body></html>');
  const names = ['window', 'document', 'AbortController', 'Event', 'HTMLElement'];
  const saved = Object.fromEntries(names.map(name => [name, globalThis[name]]));
  for (const name of names) globalThis[name] = dom.window[name];
  let canonical = raw;
  const commits = [];
  const controller = new Controller({raw, readRaw: () => canonical, writeRaw: value => { canonical = value; },
    requestPreview: () => new Promise(() => {}), onCommit: (next, previous) => commits.push({next, previous})});
  const ui = createUI({controller, reference, multiReference: reference});
  controller.onChange = (_, reason) => ui.render(reason);
  document.body.append(ui.root); ui.render();
  const root = ui.root, part = root.querySelector('[data-part-prompt]');
  const number = root.querySelector('[data-field="body_height"]');
  const rawInput = root.querySelector('textarea[aria-label="state_json"]');
  const editPart = (id, text) => {
    choose(root.querySelector('[data-part-select]'), id); part.value = text;
    part.dispatchEvent(new Event('input', {bubbles: true}));
  };
  const editNumber = text => {
    choose(root.querySelector('[data-height-presets]'), 'custom'); number.value = text;
    number.dispatchEvent(new Event('input', {bubbles: true}));
  };
  const apply = text => {
    controller.previewError = new Error('preview unavailable'); ui.render();
    assert.equal(root.querySelector('.h3-json-editor').hidden, false);
    rawInput.value = text; root.querySelector('.h3-apply').click();
  };
  return {controller, ui, root, part, number, rawInput, commits, editPart, editNumber, apply,
    saved: () => canonical,
    cleanup() {
      controller.dispose(); ui.dispose(); dom.window.close();
      for (const name of names) {
        if (saved[name] === undefined) delete globalThis[name]; else globalThis[name] = saved[name];
      }
    }};
}

for (const config of [
  {name: 'standard', Controller: DesignerController, createUI: createDesignerUI, initial: DEFAULT_JSON, reference: false},
  {name: 'Reference13', Controller: Reference13Controller, createUI: createReference13UI, initial: REFERENCE13_JSON, reference: true},
]) {
  domTest(`${config.name}: Apply JSON replaces active and inactive part drafts and numeric drafts`, t => {
    const h = setup(config); t.after(h.cleanup);
    h.editPart('head_hair', 'old hair'); h.editPart('hands', 'old gloves'); h.editNumber('999');
    const next = structuredClone(h.controller.state);
    next.part_prompts = {head_hair: 'new hair', hands: 'new bare hands'}; next.size.body_height = 1024;
    const count = h.commits.length; h.apply(JSON.stringify(next));
    assert.equal(h.commits.length, count + 1);
    assert.equal(h.part.value, 'new bare hands'); assert.equal(h.number.value, '1024');
    choose(h.root.querySelector('[data-part-select]'), 'head_hair'); assert.equal(h.part.value, 'new hair');
    assert.deepEqual(JSON.parse(h.saved()).part_prompts, next.part_prompts);
    const saved = h.saved(); h.ui.flushDrafts?.(); assert.equal(h.saved(), saved);
    h.controller.restore(saved); assert.equal(h.part.value, 'new hair'); assert.equal(h.number.value, '1024');
  });

  domTest(`${config.name}: a valid unchanged JSON discards invalid drafts without an Undo entry`, t => {
    const h = setup(config); t.after(h.cleanup);
    h.editPart('hands', 'saved hands'); const saved = h.saved();
    h.editPart('hands', 'x'.repeat(1001)); h.editNumber('673');
    h.number.dispatchEvent(new Event('blur')); assert.equal(h.part.getAttribute('aria-invalid'), 'true');
    assert.equal(h.number.getAttribute('aria-invalid'), 'true');
    const count = h.commits.length; h.apply(saved);
    assert.equal(h.saved(), saved); assert.equal(h.commits.length, count);
    assert.equal(h.part.value, 'saved hands'); assert.equal(h.number.value, '1120');
    assert.equal(h.part.getAttribute('aria-invalid'), 'false'); assert.equal(h.number.getAttribute('aria-invalid'), 'false');
    assert.doesNotThrow(() => h.ui.flushDrafts?.());
  });

  for (const invalid of ['syntax', 'schema']) domTest(`${config.name}: invalid ${invalid} JSON preserves drafts and canonical state`, t => {
    const h = setup(config); t.after(h.cleanup);
    h.editPart('hands', 'saved hands'); const saved = h.saved();
    const draft = 'x'.repeat(1001); h.editPart('hands', draft); h.editNumber('673');
    h.number.dispatchEvent(new Event('blur'));
    const count = h.commits.length;
    const next = JSON.parse(saved); next.views = ['not_a_view'];
    const raw = invalid === 'syntax' ? '{broken JSON' : JSON.stringify(next); h.apply(raw);
    assert.equal(h.saved(), saved); assert.equal(h.commits.length, count);
    assert.equal(h.part.value, draft); assert.equal(h.number.value, '673'); assert.equal(h.rawInput.value, raw);
    assert.equal(h.part.getAttribute('aria-invalid'), 'true'); assert.equal(h.number.getAttribute('aria-invalid'), 'true');
  });

  domTest(`${config.name}: applying defaults removes old prompts without changing the input schema`, t => {
    const h = setup(config); t.after(h.cleanup);
    h.editPart('head_hair', 'old hair'); h.editPart('hands', 'old gloves');
    h.apply(config.initial);
    for (const id of ['hands', 'head_hair']) {
      choose(h.root.querySelector('[data-part-select]'), id); assert.equal(h.part.value, '');
    }
    assert.equal(JSON.parse(h.saved()).schema_version, JSON.parse(config.initial).schema_version);
    assert.deepEqual(JSON.parse(h.saved()), JSON.parse(config.initial));
  });

  domTest(`${config.name}: ordinary edits preserve invalid drafts and IME caret without rewriting text`, t => {
    const h = setup(config); t.after(h.cleanup);
    h.root.querySelector('[data-tab="parts"]').click(); h.editPart('hands', '日本語入力');
    h.part.focus(); h.part.setSelectionRange(2, 2);
    const descriptor = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value');
    let writes = 0;
    Object.defineProperty(h.part, 'value', {configurable: true, get() { return descriptor.get.call(this); },
      set(value) { writes++; descriptor.set.call(this, value); }});
    h.part.dispatchEvent(new window.InputEvent('input', {bubbles: true, isComposing: true}));
    h.ui.setLocale('ja'); h.controller.toggle('feet');
    assert.equal(writes, 0); assert.equal(h.part.selectionStart, 2); assert.equal(h.part.value, '日本語入力');
    h.editPart('hands', 'x'.repeat(1001)); h.editNumber('673'); h.ui.setLocale('en'); h.controller.toggle('hands');
    assert.equal(h.part.value, 'x'.repeat(1001)); assert.equal(h.number.value, '673');
    assert.equal(h.part.getAttribute('aria-invalid'), 'true');
  });

  domTest(`${config.name}: Apply JSON and external Undo/Redo restoration keep fields and saved values aligned`, t => {
    const h = setup(config); t.after(h.cleanup);
    h.editPart('hands', 'before'); const before = h.saved();
    const next = JSON.parse(before); next.part_prompts.hands = 'after'; h.apply(JSON.stringify(next)); const after = h.saved();
    const count = h.commits.length;
    h.controller.restore(before); assert.equal(h.part.value, 'before'); assert.equal(h.saved(), before);
    h.controller.restore(after); assert.equal(h.part.value, 'after'); assert.equal(h.saved(), after);
    assert.equal(h.commits.length, count);
  });
}
