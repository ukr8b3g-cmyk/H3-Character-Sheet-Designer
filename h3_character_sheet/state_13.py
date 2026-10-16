"""Independent Reference13 state; existing local Multi Reference v3 stays separate."""
from .compiler import (
    DEFAULT_MAX_RESOLUTION, PART_IDS, PART_PROMPT_MAX_UNITS, PART_RULES,
    StateValidationError, _BLANK_CHARACTERS, _check_max_resolution, _exact_keys,
    _size_value, decode_json, parse_state, serialize_state,
)
from .view_catalog_13 import BODY_IDS, CLOTHING_IDS, LEGACY_VIEW_IDS, PORTRAIT_IDS, PRESETS, VIEW_IDS

SETTINGS = {
    'hand_state': ('reference', 'bare', 'gloved'),
    'clothing_mode': ('worn', 'garment'),
    'clothing_type': ('reference', 'pants', 'skirt_robe'),
    'footwear_state': ('reference', 'shod', 'unshod'),
}
DEFAULTS = {field: values[0] for field, values in SETTINGS.items()}
DEFAULT_STATE = {
    'schema_version': 3, 'views': list(PRESETS['five']),
    'size': {'mode': 'auto', 'body_height': 1120, 'manual_width': 2208, 'manual_height': 1280},
    'part_prompts': {}, **DEFAULTS,
}
DEFAULT_STATE_JSON = serialize_state(DEFAULT_STATE)


def parse_reference13_state(raw, *, max_resolution=DEFAULT_MAX_RESOLUTION):
    _check_max_resolution(max_resolution)
    state = decode_json(raw)
    if type(state) is not dict:
        raise StateValidationError('state must be an object.', 'invalid_type')
    version = state.get('schema_version')
    if type(version) is int and version in (1, 2):
        legacy = parse_state(raw, max_resolution=max_resolution)
        return {**legacy, 'part_prompts': legacy.get('part_prompts', {}), **DEFAULTS}
    if type(version) is not int or version != 3:
        raise StateValidationError('Reference13 supports schema_version 1, 2 or 3.', 'unsupported_schema')
    _exact_keys(state, ('schema_version', 'views', 'size', 'part_prompts', *SETTINGS), 'state')
    for field, values in SETTINGS.items():
        if type(state[field]) is not str or state[field] not in values:
            raise StateValidationError(f'Invalid {field}.', 'invalid_setting')
    views = state['views']
    if type(views) is not list or any(type(view) is not str for view in views):
        raise StateValidationError('views must be an array of view IDs.', 'invalid_type')
    if not views or set(views) - set(VIEW_IDS):
        raise StateValidationError('Select known Reference13 views.', 'unknown_view' if views else 'empty_views')
    size = state['size']
    _exact_keys(size, ('mode', 'body_height', 'manual_width', 'manual_height'), 'size')
    if type(size['mode']) is not str or size['mode'] not in ('auto', 'manual'):
        raise StateValidationError('size.mode must be auto or manual.', 'invalid_mode')
    normalized_size = {'mode': size['mode'], **{field: _size_value(size[field], f'size.{field}', max_resolution)
                       for field in ('body_height', 'manual_width', 'manual_height')}}
    prompts = state['part_prompts']
    if type(prompts) is not dict:
        raise StateValidationError('part_prompts must be an object.', 'invalid_type')
    if prompts.keys() - set(PART_IDS):
        raise StateValidationError('Unknown part IDs.', 'unknown_part')
    normalized_prompts = {}
    for part in PART_IDS:
        if part not in prompts:
            continue
        text = prompts[part]
        if type(text) is not str:
            raise StateValidationError('Part prompts must be strings.', 'invalid_type')
        if len(text.encode('utf-16-le')) // 2 > PART_PROMPT_MAX_UNITS:
            raise StateValidationError('Part prompt exceeds 1000 UTF-16 code units.', 'part_prompt_too_long')
        if text.strip(_BLANK_CHARACTERS):
            normalized_prompts[part] = text
    return {'schema_version': 3, 'views': [view for view in VIEW_IDS if view in views],
            'size': normalized_size, 'part_prompts': normalized_prompts,
            **{field: state[field] for field in SETTINGS}}


def legacy_state(state):
    version = state['schema_version'] if state['schema_version'] < 3 else 2
    result = {key: state[key] for key in ('views', 'size')}
    result = {'schema_version': version, **result}
    if version == 2:
        result['part_prompts'] = state['part_prompts']
    return result


def serialize_reference13_state(state):
    return serialize_state(legacy_state(state) if state['schema_version'] < 3 else state)


def part_views(state, part):
    extra = {
        'head_hair': PORTRAIT_IDS[2:], 'face': PORTRAIT_IDS[2:-1],
        'upper_clothing': (*PORTRAIT_IDS[2:], *CLOTHING_IDS),
        'back_clothing': ('face_back', 'clothing_back'), 'lower_body': CLOTHING_IDS,
        'hands': CLOTHING_IDS if state['clothing_mode'] == 'worn' else (),
        'footwear': (), 'other': VIEW_IDS,
    }
    eligible = (*PART_RULES[part]['views'], *extra[part])
    if state['clothing_mode'] == 'garment' and part in ('head_hair', 'face', 'hands', 'footwear'):
        eligible = tuple(view for view in eligible if view not in CLOTHING_IDS)
    return tuple(view for view in state['views'] if view in eligible)


def applicable_settings(state):
    worn = CLOTHING_IDS if state['clothing_mode'] == 'worn' else ()
    scopes = {'hand_state': (*BODY_IDS, 'hands', *worn),
              'footwear_state': (*BODY_IDS, 'feet'),
              'clothing_type': (*BODY_IDS, *CLOTHING_IDS), 'clothing_mode': CLOTHING_IDS}
    return {field: tuple(view for view in state['views'] if view in scopes[field])
            for field in SETTINGS if state[field] != DEFAULTS[field]
            and any(view in scopes[field] for view in state['views'])}


def uses_legacy_path(state):
    return set(state['views']).issubset(LEGACY_VIEW_IDS) and not applicable_settings(state)
