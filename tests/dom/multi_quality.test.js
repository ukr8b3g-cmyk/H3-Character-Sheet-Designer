import test from 'node:test';
import assert from 'node:assert/strict';
import {pathToFileURL} from 'node:url';
import {DEFAULT_JSON, DesignerController} from '../../web/state.js';
import {DEFAULT_MULTI_JSON, MultiReferenceController, MULTI_VIEW_IDS} from '../../web/multi_state.js';
import {createDesignerUI} from '../../web/ui.js';
let JSDOM;
try { ({JSDOM} = await import(process.env.H3_JSDOM_PATH ? pathToFileURL(process.env.H3_JSDOM_PATH).href : 'jsdom')); } catch {}
const domTest = (name, fn) => test(name, {skip: !JSDOM && 'jsdom unavailable'}, fn);
function setup(multi = true) {
  const dom = new JSDOM('<!doctype html><html><head></head><body></body></html>');
  const names = ['window', 'document', 'AbortController', 'Event', 'HTMLElement'];
  const saved = Object.fromEntries(names.map(n => [n, globalThis[n]]));
  for (const n of names) globalThis[n] = dom.window[n];
  const C = multi ? MultiReferenceController : DesignerController;
  const controller = new C({raw: multi ? DEFAULT_MULTI_JSON : DEFAULT_JSON, requestPreview: () => new Promise(() => {})});
  const ui = createDesignerUI({controller, reference: multi, multiReference: multi});
  controller.onChange = (_, reason) => ui.render(reason);
  document.body.append(ui.root); ui.render();
  return {controller, ui, cleanup() { controller.dispose(); ui.dispose(); dom.window.close(); for (const n of names) { if (saved[n] === undefined) delete globalThis[n]; else globalThis[n] = saved[n]; } }};
}
domTest('13 cards, eight roles, appearance controls and save/restore in both locales', t => {
  const h = setup(); t.after(h.cleanup); const root = h.ui.root;
  assert.equal(root.querySelectorAll('[data-view]').length, 13);
  const roles = root.querySelectorAll('[data-reference-role]'); assert.equal(roles.length, 2);
  for (const select of roles) assert.equal(select.options.length, 8);
  const hand = root.querySelector('[data-appearance-choice="hand_state"]');
  const clothes = root.querySelector('[data-appearance-choice="clothing_mode"]');
  assert.equal(hand.value, 'reference'); assert.equal(clothes.value, 'worn');
  hand.value = 'bare'; hand.dispatchEvent(new Event('change'));
  clothes.value = 'garment'; clothes.dispatchEvent(new Event('change'));
  const saved = h.controller.raw; h.controller.restore(saved);
  assert.equal(hand.value, 'bare'); assert.equal(clothes.value, 'garment');
  h.ui.setLocale('ja'); assert.equal(hand.options[1].textContent, '素手');
  assert.match(root.querySelector('[data-view="body_left"]').title, /画面の左/);
  assert.equal(h.controller.raw, saved);
});
domTest('new preview shares tight crop positions, mirrors and blank garment slots', t => {
  const h = setup(); t.after(h.cleanup);
  h.controller.state.views = [...MULTI_VIEW_IDS]; h.controller.state.clothing_mode = 'garment';
  h.controller.preview = {width: 100, height: 100, layout: {canvas: [100, 100], panels: [
    {id: 'body_left', rect: [0, 0, .4, 1]}, {id: 'clothing_front', rect: [.5, 0, .4, 1]}], feet_y: .9},
    guide_artwork: {body_left: {crop: [1033, 48, 109, 588], rect: [10, 20, 15, 71]}}};
  h.ui.render();
  const body = h.ui.root.querySelector('[data-panel="body_left"]');
  assert.equal(body.firstElementChild.style.top, '20%');
  assert.equal(body.querySelector('svg').getAttribute('viewBox'), '1033 48 109 588');
  assert.equal(body.querySelector('[data-artwork]').style.transform, 'scaleX(-1)');
  assert.equal(h.ui.root.querySelector('[data-panel="clothing_front"]').children.length, 0);
});
domTest('legacy designer has seven cards, original art and no appearance controls', t => {
  const h = setup(false); t.after(h.cleanup);
  assert.equal(h.ui.root.querySelectorAll('[data-view]').length, 7);
  assert.equal(h.ui.root.querySelectorAll('[data-appearance-choice]').length, 0);
  assert.equal(h.ui.root.querySelector('[data-view="body_left"] [data-artwork]').style.transform, '');
});
