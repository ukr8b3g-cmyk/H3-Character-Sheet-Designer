"""Static-image prose for MiniMax H3 Image; never changes the P-H3 compiler."""
import json
from math import sqrt

from .compiler import StateValidationError, decode_json
from .guide_13 import derive_guide_geometry
from .state_13 import applicable_settings, part_views, serialize_reference13_state
from .reference_v13_compiler import compile_reference_v13_state
from .reference_compiler import STYLE_PROMPTS
from .appearance_policy_13 import build_appearance_policy
from .view_catalog_13 import BODY_IDS, PRESETS, VIEW_IDS

RESOLUTION_PROFILES = ('current', 'high', 'max_8mp', 'max_16mp')
EIGHT_MP = 8_000_000
MAX_AUTO_PIXELS = 16_000_000


VIEW_PROMPTS = {
    'face_front': 'Front portrait, complete head and shoulders.',
    'face_left': 'Profile portrait facing image-right, complete head and shoulders.',
    'face_right': 'Profile portrait facing image-left, complete head and shoulders.',
    'face_3q_left': 'Three-quarter portrait facing image-right, complete head and shoulders.',
    'face_3q_right': 'Three-quarter portrait facing image-left, complete head and shoulders.',
    'face_back': 'Portrait from behind, complete head and shoulders.',
    'body_front': 'Full body facing forward, standing, complete figure visible.',
    'body_left': 'Full body in profile facing image-right, standing, complete figure visible.',
    'body_back': 'Full body from behind, standing, complete figure visible.',
    'clothing_front': 'Extract the front of the outfit onto a white background. No human. The outfit is flat.',
    'clothing_back': 'Extract the back of the outfit onto a white background. No human. The outfit is flat.',
    'hands': 'Close-up of both hands, including their coverings when present in the reference.',
    'feet': 'Close-up of both feet and their footwear when present in the reference.',
}

SETTINGS = {
    ('hand_state', 'bare'): 'Bare hands.',
    ('hand_state', 'gloved'): 'Gloved hands.',
    ('footwear_state', 'shod'): 'Feet wearing footwear.',
    ('footwear_state', 'unshod'): 'Shoes removed; retain reference socks or tights.',
    ('clothing_type', 'pants'): 'Trousers for the lower garment.',
    ('clothing_type', 'skirt_robe'): 'Skirt or robe for the lower garment.',
}

ROLE_NAMES = {'face': 'facial appearance', 'head': 'head appearance',
              'clothing': 'outfit', 'clothing_front': 'front of the outfit',
              'clothing_back': 'back of the outfit', 'hands': 'hands and gloves',
              'footwear': 'footwear'}


def _arranged_columns(layout):
    columns = {}
    for panel in layout['panels']:
        columns.setdefault(panel['rect'][0], []).append(panel)
    return [sorted(columns[x], key=lambda p: p['rect'][1]) for x in sorted(columns)]


def _standard_five_view_guide(layout, state):
    """Trade a little portrait width for full-body space and leave room above the head."""
    canvas_width, _ = layout['canvas']
    panels = sorted(layout['panels'], key=lambda panel: panel['rect'][0])
    extra = round(min(panel['rect'][2] for panel in panels if panel['id'] in BODY_IDS) * canvas_width * 0.06)
    guide_panels = []
    shift = 0
    for panel in panels:
        x, y, width, height = panel['rect']
        change = extra if panel['id'] in BODY_IDS else -extra * 1.5
        guide_panels.append({**panel, 'rect': [x + shift / canvas_width, y, width + change / canvas_width, height]})
        shift += change
    geometry = derive_guide_geometry({**layout, 'panels': guide_panels}, state, compact=True)
    for panel in geometry['panels']:
        if panel['id'] in BODY_IDS:
            left, top, right, bottom = panel['bounds']
            _, _, width, height = panel['rect']
            panel_height = bottom - top
            y = top + round(panel_height * 0.105)
            fit_height = min(height, bottom - round(panel_height * 0.035) - y)
            fit_width = round(width * fit_height / height)
            panel['rect'] = [(left + right - fit_width) // 2, y, fit_width, fit_height]
    return geometry


def _all_view_layout(descriptions):
    return [
        'Arrange four blocks side by side across the canvas, from left to right.',
        'Far left: six portraits in a two-column, three-row grid. Read each row from left to right.',
        f"Top row: {descriptions['face_front']} {descriptions['face_left']}",
        f"Middle row: {descriptions['face_right']} {descriptions['face_3q_left']}",
        f"Bottom row: {descriptions['face_3q_right']} {descriptions['face_back']}",
        'Center: three full-body figures side by side, equally tall, with a small margin above and below.',
        f"From left to right: {descriptions['body_front']} {descriptions['body_left']} {descriptions['body_back']}",
        'To their right: two flat outfit views side by side, front on the left and back on the right.',
        f"{descriptions['clothing_front']} {descriptions['clothing_back']}",
        f"Far right: hands above footwear. Top: {descriptions['hands']} Bottom: {descriptions['feet']}",
    ]


def _apply_resolution(result, profile):
    if profile == 'current' or result['state']['size']['mode'] != 'auto':
        return

    width, height = result['width'], result['height']
    pixels = width * height
    limit = MAX_AUTO_PIXELS if profile == 'max_16mp' else EIGHT_MP
    target = limit
    if profile == 'high' and pixels < limit:
        target = 2 * pixels if 2 * pixels < limit else (pixels + limit) // 2
    edge_limit = result['max_resolution'] // 32 * 32
    scale = min(sqrt(target / pixels), edge_limit / max(width, height))
    out_width, out_height = (max(32, int(side * scale / 32) * 32) for side in (width, height))
    # The 32 px minimum can overshoot the area for unusually thin canvases.
    if out_width * out_height > limit:
        if out_width > out_height:
            out_width = limit // (out_height * 32) * 32
        else:
            out_height = limit // (out_width * 32) * 32

    canvas = [out_width, out_height]
    result['layout']['canvas'] = result['semantic_layout']['canvas'] = canvas
    geometry = result['guide_geometry']
    geometry['canvas'] = canvas
    sx, sy = out_width / width, out_height / height
    for panel in geometry['panels']:
        left, top, right, bottom = panel['bounds']
        panel['bounds'] = [round(left * sx), round(top * sy), round(right * sx), round(bottom * sy)]
        x, y, w, h = panel['rect']
        left, top, right, bottom = round(x * sx), round(y * sy), round((x + w) * sx), round((y + h) * sy)
        panel['rect'] = [left, top, max(1, right - left), max(1, bottom - top)]

    pixels = out_width * out_height
    result.update(width=out_width, height=out_height, pixel_count=pixels, megapixels=pixels / 1_000_000)


def compile_minimax_image_state(state_json, **kwargs):
    # Only this node accepts the optional setting in its saved state.
    saved = decode_json(state_json)
    profile = None
    if isinstance(saved, dict) and 'resolution_profile' in saved:
        profile = saved.pop('resolution_profile')
        if saved.get('schema_version') != 3 or profile not in RESOLUTION_PROFILES:
            raise StateValidationError('Unknown output resolution profile.', 'invalid_resolution_profile')
        state_json = json.dumps(saved, ensure_ascii=False, separators=(',', ':'))
    # Reuse validation, sizing, guide rendering and persistence, not video prose.
    result = compile_reference_v13_state(state_json, **kwargs)
    state = result['state']
    if result['guide_enabled'] and state['size']['mode'] == 'auto' and set(state['views']) == set(PRESETS['five']):
        result['guide_geometry'] = _standard_five_view_guide(result['semantic_layout'], state)
    if profile is not None:
        state['resolution_profile'] = profile
        result['state_json'] = serialize_reference13_state(state)
        _apply_resolution(result, profile)
    result['experimental'] = result['pixel_count'] > MAX_AUTO_PIXELS
    refs = result['reference_plan']
    slots = ('character_image', 'layout_image', 'reference_image_1',
             'reference_image_2', 'reference_image_3')
    for ref in refs:
        ref['core_input'] = f"images.image_{slots.index(ref['source'])}"
    views = state['views']
    single = len(views) == 1
    all_views = len(views) == len(VIEW_IDS) and not result['guide_enabled']
    hand_foot_pair = set(views) == {'hands', 'feet'} and not result['guide_enabled']
    garment_only = all(v.startswith('clothing_') for v in views)
    subject = 'outfit' if garment_only else 'character'
    if single:
        target = ('detail illustration from <Picture 1>' if views[0] in {'hands', 'feet'}
                  else f'illustration of the {subject} from <Picture 1>')
        lines = [f'Create a single centered {target}.']
    elif hand_foot_pair:
        lines = ['Create exactly two borderless close-up views from <Picture 1>, one above the other on a white canvas. '
                 'Leave a clear band of blank white space between the views.',
                 'Match the rendering style of <Picture 1>.']
    else:
        lines = [f'Create one {subject} reference sheet from <Picture 1>.',
                 f'Preserve the same {subject} design and rendering style across all views.',
                 'White background. Each requested view appears once.']
    for ref in refs:
        if ref['role'] == 'layout':
            if single:
                lines.append(f"Use {ref['tag']} for framing.")
            else:
                lines.append(f"{ref['tag']} supplies the arrangement and viewing directions. "
                             f"Render the finished {subject} from <Picture 1> at a clear, generous scale in each area.")
        elif ref['role'] == 'same_character':
            lines.append(f"{ref['tag']} supplements the same {subject}'s appearance.")
    if any(ref['source'] in slots[2:] for ref in refs):
        lines.append('Follow selected settings first, then compatible part instructions, then dedicated references. '
                     'If dedicated references for the same role conflict, prefer the later input.')
    if not (single or all_views or hand_foot_pair):
        lines.append('Arrange columns from left to right; within a stacked column, read top to bottom:')
    defaults = dict(VIEW_PROMPTS)
    if state['hand_state'] == 'bare':
        defaults['hands'] = 'Close-up of both hands.'
    if state['footwear_state'] == 'unshod':
        defaults['feet'] = 'Close-up of both feet.'
    records = []
    view_text = {}
    scopes = applicable_settings(state)
    appearance = build_appearance_policy(state, refs)
    for column in _arranged_columns(result['semantic_layout']):
        descriptions = []
        for panel in column:
            view = panel['id']
            text = state.get('view_prompts', {}).get(view, defaults[view])
            extras = [SETTINGS[(field, state[field])] for field, views in scopes.items()
                      if view in views and (field, state[field]) in SETTINGS]
            for ref in appearance:
                if any(view in views for views in ref['parts'].values()):
                    extras.append(f"Use {ref['tag']} for {ROLE_NAMES[ref['role']]}.")
            extras += [value for part, value in state['part_prompts'].items()
                       if value and view in part_views(state, part)]
            text = ' '.join([text, *extras]).strip()
            if text or not single:
                descriptions.append(text or 'One reserved view area.')
            if all_views or hand_foot_pair:
                view_text[view] = descriptions[-1]
            records.append(f'{view}: {text}')
        if single:
            lines.extend(descriptions)
        elif not (all_views or hand_foot_pair):
            lines.append(' / '.join(descriptions))
    if all_views:
        lines.extend(_all_view_layout(view_text))
    elif hand_foot_pair:
        lines.extend((f"Upper half: {view_text['hands']}", f"Lower half: {view_text['feet']}"))
    if single:
        lines.extend((f'Preserve the {subject} design and rendering style.', 'Plain white background.'))
        if views[0].startswith('body_') and views[0] not in state.get('view_prompts', {}):
            lines.append('Keep a small margin around the complete figure.')
    style = STYLE_PROMPTS[kwargs.get('style', 'none')]
    if style:
        lines.append(style)
    separator = ' ' if single else '\n'
    result.update(prompt=separator.join(lines), default_view_prompts=defaults, view_prompts=records)
    return result
