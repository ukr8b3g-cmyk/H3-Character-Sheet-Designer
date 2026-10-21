/** Reference13 has its own v3 contract. Loading legacy JSON never rewrites it. */
import {
  DesignerController, StateError, normalizeState, parseJSONStrict, validateSize,
  validatePartPrompt, PART_IDS, VIEW_IDS as LEGACY_VIEWS,
} from './state.js';
export {PART_IDS, PART_PROMPT_MAX_LENGTH, StateError} from './state.js';
export const MULTI_VIEW_IDS = Object.freeze(['face_front', 'face_left', 'face_right', 'face_3q_left', 'face_3q_right', 'face_back', 'body_front', 'body_left', 'body_back', 'clothing_front', 'clothing_back', 'hands', 'feet']);
export const VIEW_IDS = MULTI_VIEW_IDS;
export const MULTI_PRESETS = Object.freeze({five: ['face_front', 'face_left', 'body_front', 'body_left', 'body_back'], basic: ['face_front', 'body_front', 'body_left', 'body_back'], turnaround: ['body_front', 'body_left', 'body_back'], single: ['body_front'], head: MULTI_VIEW_IDS.slice(0, 6), clothing: ['clothing_front', 'clothing_back'], detail: [...MULTI_VIEW_IDS]});
export const PRESETS = MULTI_PRESETS;
export const REFERENCE_INPUTS = ['reference_image_1', 'reference_image_2', 'reference_image_3'];
export const REFERENCE_ROLES = ['same_character', 'face', 'head', 'clothing', 'clothing_front', 'clothing_back', 'hands', 'footwear'];
export const SETTINGS = Object.freeze({hand_state: ['reference', 'bare', 'gloved'], clothing_mode: ['worn', 'garment'], clothing_type: ['reference', 'pants', 'skirt_robe'], footwear_state: ['reference', 'shod', 'unshod']});
export const DEFAULTS = Object.freeze(Object.fromEntries(Object.entries(SETTINGS).map(([field, values]) => [field, values[0]])));
export const HAND_STATES = SETTINGS.hand_state;
export const CLOTHING_MODES = SETTINGS.clothing_mode;
export const CLOTHING_TYPES = SETTINGS.clothing_type;
export const FOOTWEAR_STATES = SETTINGS.footwear_state;
export const MULTI_MIRRORED_VIEWS = Object.freeze([]);
export const DEFAULT_JSON = JSON.stringify({schema_version: 3, views: PRESETS.five, size: {mode: 'auto', body_height: 1120, manual_width: 2208, manual_height: 1280}, part_prompts: {}, ...DEFAULTS});
const fail = (code, detail = '') => { throw new StateError(code, detail); };
function keys(value, expected, path) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) fail('object', path);
  const actual = Object.keys(value);
  if (actual.length !== expected.length || actual.some(key => !expected.includes(key))) fail('keys', path);
}
export function normalizeReference13State(state, max = Infinity) {
  if (!state || typeof state !== 'object' || Array.isArray(state)) fail('object', 'state');
  if ([1, 2].includes(state.schema_version)) return normalizeState(state, max);
  if (state.schema_version !== 3) fail('version');
  keys(state, ['schema_version', 'views', 'size', 'part_prompts', ...Object.keys(SETTINGS), ...(Object.hasOwn(state, 'reference_roles') ? ['reference_roles'] : [])], 'state');
  if (Object.hasOwn(state, 'reference_roles')) {
    keys(state.reference_roles, REFERENCE_INPUTS, 'reference_roles');
    if (Object.values(state.reference_roles).some(role => !REFERENCE_ROLES.includes(role))) fail('setting', 'reference_roles');
  }
  for (const [field, values] of Object.entries(SETTINGS)) if (!values.includes(state[field])) fail('setting', field);
  if (!Array.isArray(state.views) || !state.views.length || state.views.some(view => !VIEW_IDS.includes(view))) fail('views');
  keys(state.size, ['mode', 'body_height', 'manual_width', 'manual_height'], 'size');
  if (!['auto', 'manual'].includes(state.size.mode)) fail('mode');
  const size = {mode: state.size.mode};
  for (const field of ['body_height', 'manual_width', 'manual_height']) size[field] = validateSize(state.size[field], field, max);
  if (!state.part_prompts || typeof state.part_prompts !== 'object' || Array.isArray(state.part_prompts)) fail('object', 'part_prompts');
  if (Object.keys(state.part_prompts).some(part => !PART_IDS.includes(part))) fail('parts');
  const parts = {};
  for (const part of PART_IDS) if (Object.hasOwn(state.part_prompts, part)) {
    const text = validatePartPrompt(state.part_prompts[part]);
    if (text.trim()) parts[part] = text;
  }
  return {schema_version: 3, views: VIEW_IDS.filter(view => state.views.includes(view)), size, part_prompts: parts, ...(Object.hasOwn(state, 'reference_roles') ? {reference_roles: {...state.reference_roles}} : {}), ...Object.fromEntries(Object.keys(SETTINGS).map(field => [field, state[field]]))};
}
export const parseReference13State = (raw, max) => normalizeReference13State(parseJSONStrict(raw), max);
export const serializeReference13State = (state, max) => JSON.stringify(normalizeReference13State(state, max));
export const presetOf = state => Object.entries(PRESETS).find(([, views]) => views.join() === state?.views.join())?.[0] ?? 'custom';
function promote(state) { return {...structuredClone(state), schema_version: 3, part_prompts: structuredClone(state.part_prompts ?? {}), ...DEFAULTS}; }
export class Reference13Controller extends DesignerController {
  constructor(options) {
    super({...options, adapter: {parse: parseReference13State, serialize: serializeReference13State, migrate: state => structuredClone(state), viewIds: VIEW_IDS, presets: PRESETS}});
  }
  commit(next) {
    if (next.schema_version < 3 && next.views.some(view => !LEGACY_VIEWS.includes(view))) next = promote(next);
    return super.commit(next);
  }
  setChoice(field, value) {
    if (!SETTINGS[field]?.includes(value)) fail('setting', field);
    this.syncFromSource();
    if (!this.state || (this.state[field] ?? DEFAULTS[field]) === value) return false;
    const next = this.state.schema_version < 3 ? promote(this.state) : structuredClone(this.state);
    next[field] = value; return this.commit(next);
  }
  setReferenceRole(input, role) {
    if (!REFERENCE_INPUTS.includes(input) || !REFERENCE_ROLES.includes(role)) fail('setting', 'reference_roles');
    this.syncFromSource();
    if (!this.state || (this.state.reference_roles?.[input] ?? 'same_character') === role) return false;
    const next = this.state.schema_version < 3 ? promote(this.state) : structuredClone(this.state);
    next.reference_roles ??= Object.fromEntries(REFERENCE_INPUTS.map(key => [key, 'same_character']));
    next.reference_roles[input] = role;
    return this.commit(next);
  }
  setHandState(value) { return this.setChoice('hand_state', value); }
  setClothingMode(value) { return this.setChoice('clothing_mode', value); }
  setPartPrompt(part, text) {
    this.syncFromSource();
    if (!PART_IDS.includes(part)) fail('parts');
    validatePartPrompt(text);
    if (!this.state || text === this.state.part_prompts?.[part] || (!text.trim() && !this.state.part_prompts?.[part])) return false;
    const next = structuredClone(this.state);
    if (next.schema_version === 1) { next.schema_version = 2; next.part_prompts = {}; }
    if (text.trim()) next.part_prompts[part] = text; else delete next.part_prompts[part];
    return this.commit(next);
  }
}
