import test from 'node:test';
import assert from 'node:assert/strict';
import {DEFAULT_JSON, Reference13Controller, parseReference13State, MULTI_VIEW_IDS} from '../../web/reference13_state.js';
import {DEFAULT_JSON as OLD_JSON} from '../../web/state.js';
import {previewRequester} from '../../web/reference13_integration.js';
test('reference preview reads current connections on every request and forwards cancellation', async () => {
  const calls = [], abort = new AbortController();
  let presence = {reference_image_1: false, reference_image_2: true, reference_image_3: false}, enabled = false;
  const request = previewRequester({fetchApi: async (path, options) => {
    calls.push({path, options, body: JSON.parse(options.body)});
    return {ok: true, json: async () => ({prompt: 'preview'})};
  }}, () => enabled, () => 'none', () => presence);
  await request(DEFAULT_JSON, abort.signal);
  enabled = true; presence = {reference_image_1: true, reference_image_2: false, reference_image_3: true};
  await request(DEFAULT_JSON, abort.signal);
  assert.deepEqual(calls[0].body.reference_presence, {reference_image_1: false, reference_image_2: true, reference_image_3: false});
  assert.deepEqual(calls[1].body.reference_presence, presence);
  assert.equal(calls[1].body.use_layout_image, true);
  assert.equal(calls[0].options.signal, abort.signal);
});
const options = raw => ({raw, requestPreview: () => new Promise(() => {})});
test('Reference13 defaults and strict independent schema', () => {
  const state = parseReference13State(DEFAULT_JSON);
  assert.equal(state.clothing_type, 'reference');
  assert.equal(state.footwear_state, 'reference');
  assert.throws(() => parseReference13State(JSON.stringify({...state, reference_roles: {}})));
  assert.throws(() => parseReference13State(DEFAULT_JSON.replace('1120', 'true')));
  assert.throws(() => parseReference13State(DEFAULT_JSON.replace('1120', '1120.0')));
});
test('legacy restore and existing view edits keep schema; new choices promote explicitly', t => {
  const c = new Reference13Controller(options(OLD_JSON)); t.after(() => c.dispose());
  assert.equal(c.raw, OLD_JSON); assert.equal(c.state.schema_version, 1);
  c.toggle('hands'); assert.equal(c.state.schema_version, 1);
  c.setChoice('clothing_type', 'pants'); assert.equal(c.state.schema_version, 3);
  c.setChoice('footwear_state', 'unshod'); assert.equal(c.state.footwear_state, 'unshod');
  c.restore(OLD_JSON); assert.equal(c.raw, OLD_JSON); assert.equal(c.state.schema_version, 1);
  c.toggle('face_right'); assert.equal(c.state.schema_version, 3);
});
test('legacy part edit uses schema2; new node saves all four choices', t => {
  const c = new Reference13Controller(options(OLD_JSON)); t.after(() => c.dispose());
  c.setPartPrompt('upper_clothing', '青い絹 {red|blue}'); assert.equal(c.state.schema_version, 2);
  c.setChoice('hand_state', 'gloved'); c.setChoice('clothing_mode', 'garment');
  const restored = parseReference13State(c.raw);
  assert.equal(restored.hand_state, 'gloved'); assert.equal(restored.clothing_mode, 'garment');
  assert.equal(restored.part_prompts.upper_clothing, '青い絹 {red|blue}');
});
test('all8191 selections normalize to fixed order', () => {
  const base = JSON.parse(DEFAULT_JSON);
  for (let mask=1; mask<8192; mask++) {
    const views = MULTI_VIEW_IDS.filter((_, i) => mask & (1<<i));
    assert.deepEqual(parseReference13State(JSON.stringify({...base, views: [...views].reverse()})).views, views);
  }
});
test('invalid dimension does not replace saved state', t => {
  const c = new Reference13Controller(options(DEFAULT_JSON)); t.after(() => c.dispose());
  assert.throws(() => c.setSize('body_height', '1119')); assert.equal(c.raw, DEFAULT_JSON);
  c.state.views = ['body_front']; assert.throws(() => c.toggle('body_front'));
});
test('out-of-order preview cannot restore older choices or unlock stale Manual dimensions', async t => {
  const calls=[];
  const c=new Reference13Controller({raw:DEFAULT_JSON, requestPreview:raw=>new Promise(resolve=>calls.push({raw,resolve}))});
  t.after(()=>c.dispose());
  const preview=(raw,width)=>{const s=parseReference13State(raw);return {width,height:1280,max_resolution:16384,layout:{canvas:[width,1280],panels:s.views.map((id,i)=>({id,rect:[i/s.views.length,0,1/s.views.length,1]})),feet_y:0.9}};};
  c.setChoice('clothing_type','pants');
  calls[1].resolve(preview(calls[1].raw,2816));
  await new Promise(resolve=>setImmediate(resolve));
  calls[0].resolve(preview(calls[0].raw,2208));
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(c.state.clothing_type,'pants'); assert.equal(c.preview.width,2816);
  c.setChoice('footwear_state','unshod'); assert.throws(()=>c.setMode('manual'));
  calls[2].resolve(preview(calls[2].raw,2816)); await new Promise(resolve=>setImmediate(resolve));
  c.setMode('manual'); assert.equal(c.state.size.manual_width,2816);
});
