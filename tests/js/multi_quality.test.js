import test from 'node:test';
import assert from 'node:assert/strict';
import {DEFAULT_JSON} from '../../web/state.js';
import {DEFAULT_MULTI_JSON, parseMultiState, migrateMultiState, serializeMultiState, MultiReferenceController} from '../../web/multi_state.js';

test('missing new fields and legacy states migrate with compatible defaults', () => {
  const old3 = JSON.parse(DEFAULT_MULTI_JSON); delete old3.hand_state; delete old3.clothing_mode;
  for (const raw of [DEFAULT_JSON, JSON.stringify(old3)]) {
    const result = migrateMultiState(parseMultiState(raw));
    assert.equal(result.hand_state, 'reference'); assert.equal(result.clothing_mode, 'worn');
    assert.deepEqual(parseMultiState(serializeMultiState(result)), result);
  }
});
test('new selectors serialize, restore and retain literal part text', () => {
  const text = '  silver ring; gloves\n星 {red|blue} ';
  const initial = JSON.parse(DEFAULT_MULTI_JSON); initial.part_prompts = {hands: text};
  const c = new MultiReferenceController({raw: JSON.stringify(initial), requestPreview: async () => { throw Error('not used'); }});
  for (const value of ['reference', 'bare', 'gloved']) { c.setHandState(value); assert.equal(parseMultiState(c.raw).hand_state, value); }
  c.setClothingMode('garment'); const saved = c.raw; c.restore(saved);
  assert.equal(c.state.clothing_mode, 'garment'); assert.equal(c.state.part_prompts.hands, text);
  c.dispose();
});
test('invalid appearance values and unknown fields cannot reset state silently', () => {
  for (const field of ['hand_state', 'clothing_mode']) for (const value of [null, 1, true, [], {}, 'bad']) {
    assert.throws(() => parseMultiState(JSON.stringify({...JSON.parse(DEFAULT_MULTI_JSON), [field]: value})));
  }
  assert.throws(() => parseMultiState(JSON.stringify({...JSON.parse(DEFAULT_MULTI_JSON), unknown: true})));
});
