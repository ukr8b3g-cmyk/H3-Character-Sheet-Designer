/** v3 adapter; legacy controllers keep their seven-view contract. */
import {
  DesignerController, normalizeState, parseJSONStrict, StateError,
  validateSize, validatePartPrompt, PART_IDS, PRESETS,
} from './state.js';

export const MULTI_VIEW_IDS = Object.freeze([
  'face_front', 'face_left', 'face_right', 'face_3q_left', 'face_3q_right', 'face_back',
  'body_front', 'body_left', 'body_back', 'clothing_front', 'clothing_back', 'hands', 'feet',
]);
export const REFERENCE_INPUTS = Object.freeze(['reference_image_1', 'reference_image_2']);
export const HAND_STATES = Object.freeze(['reference', 'bare', 'gloved']);
export const CLOTHING_MODES = Object.freeze(['worn', 'garment']);
export const MULTI_MIRRORED_VIEWS = Object.freeze(['face_left', 'face_right', 'face_3q_left', 'face_3q_right', 'body_left']);
export const REFERENCE_ROLES = Object.freeze([
  'same_character', 'face', 'head', 'clothing', 'clothing_front', 'clothing_back', 'hands', 'footwear',
]);
export const MULTI_PRESETS = Object.freeze({
  ...PRESETS, detail: [...MULTI_VIEW_IDS], head: MULTI_VIEW_IDS.slice(0, 6),
  clothing: ['clothing_front', 'clothing_back'],
});
export const DEFAULT_MULTI_JSON = JSON.stringify({
  schema_version: 3, views: PRESETS.five,
  size: {mode: 'auto', body_height: 1120, manual_width: 2208, manual_height: 1280},
  part_prompts: {}, reference_roles: {reference_image_1: 'same_character', reference_image_2: 'same_character'},
  hand_state: 'reference', clothing_mode: 'worn',
});
const fail = (code, detail = '') => { throw new StateError(code, detail); };
function keys(value, expected, path) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) fail('object', path);
  const actual = Object.keys(value);
  if (actual.length !== expected.length || actual.some(key => !expected.includes(key))) fail('keys', path);
}
export function normalizeMultiState(state, maxResolution = Infinity) {
  if (!state || typeof state !== 'object' || Array.isArray(state)) fail('object', 'state');
  if ([1, 2].includes(state.schema_version)) return normalizeState(state, maxResolution);
  if (state.schema_version !== 3) fail('version');
  state = {...state, hand_state: Object.hasOwn(state, 'hand_state') ? state.hand_state : 'reference',
    clothing_mode: Object.hasOwn(state, 'clothing_mode') ? state.clothing_mode : 'worn'};
  keys(state, ['schema_version', 'views', 'size', 'part_prompts', 'reference_roles', 'hand_state', 'clothing_mode'], 'state');
  if (!HAND_STATES.includes(state.hand_state)) fail('handState');
  if (!CLOTHING_MODES.includes(state.clothing_mode)) fail('clothingMode');
  if (!Array.isArray(state.views) || !state.views.length || state.views.some(view => !MULTI_VIEW_IDS.includes(view))) fail('views');
  keys(state.size, ['mode', 'body_height', 'manual_width', 'manual_height'], 'size');
  if (!['auto', 'manual'].includes(state.size.mode)) fail('mode');
  const normalized = {
    schema_version: 3, views: MULTI_VIEW_IDS.filter(view => state.views.includes(view)),
    size: {mode: state.size.mode,
      body_height: validateSize(state.size.body_height, 'body_height', maxResolution),
      manual_width: validateSize(state.size.manual_width, 'manual_width', maxResolution),
      manual_height: validateSize(state.size.manual_height, 'manual_height', maxResolution)},
    part_prompts: {},
  };
  const prompts = state.part_prompts;
  if (!prompts || typeof prompts !== 'object' || Array.isArray(prompts)) fail('object', 'part_prompts');
  if (Object.keys(prompts).some(part => !PART_IDS.includes(part))) fail('parts');
  for (const part of PART_IDS) if (Object.hasOwn(prompts, part)) {
    const text = validatePartPrompt(prompts[part]);
    if (text.trim()) normalized.part_prompts[part] = text;
  }
  keys(state.reference_roles, REFERENCE_INPUTS, 'reference_roles');
  normalized.reference_roles = {};
  for (const input of REFERENCE_INPUTS) {
    const role = state.reference_roles[input];
    if (!REFERENCE_ROLES.includes(role)) fail('roles', input);
    normalized.reference_roles[input] = role;
  }
  normalized.hand_state = state.hand_state;
  normalized.clothing_mode = state.clothing_mode;
  return normalized;
}
export function migrateMultiState(state) {
  const next = normalizeMultiState(state);
  if (next.schema_version < 3) return {
    ...next, schema_version: 3, part_prompts: next.part_prompts ?? {},
    reference_roles: {reference_image_1: 'same_character', reference_image_2: 'same_character'},
    hand_state: 'reference', clothing_mode: 'worn',
  };
  return next;
}
export const parseMultiState = (raw, max) => normalizeMultiState(parseJSONStrict(raw), max);
export const serializeMultiState = (state, max) => JSON.stringify(normalizeMultiState(state, max));
export class MultiReferenceController extends DesignerController {
  constructor(options) {
    super({...options, adapter: {
      parse: parseMultiState, serialize: serializeMultiState, migrate: migrateMultiState,
      viewIds: MULTI_VIEW_IDS, presets: MULTI_PRESETS,
    }});
  }
  setMode(mode, output = null) {
    if (mode !== 'manual' || !output) return super.setMode(mode);
    this.syncFromSource();
    if (mode === this.state?.size.mode) return false;
    if (!this.isCurrentPreview) fail('updating');
    validateSize(output.width, 'manual_width', this.maxResolution);
    validateSize(output.height, 'manual_height', this.maxResolution);
    return this.change(next => { next.size.mode = 'manual'; next.size.manual_width = output.width; next.size.manual_height = output.height; });
  }
  setReferenceRole(input, role) {
    if (!REFERENCE_INPUTS.includes(input) || !REFERENCE_ROLES.includes(role)) fail('roles');
    return this.change(next => { next.reference_roles[input] = role; });
  }
  setHandState(value) {
    if (!HAND_STATES.includes(value)) fail('handState');
    return this.change(next => { next.hand_state = value; });
  }
  setClothingMode(value) {
    if (!CLOTHING_MODES.includes(value)) fail('clothingMode');
    return this.change(next => { next.clothing_mode = value; });
  }
}
