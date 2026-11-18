"""Shared layout and prose for a sheet containing all six portrait views."""
from .appearance_policy_13 import ROLE_NAMES, build_appearance_policy, unused_reference_instructions
from .guide_13 import derive_guide_geometry
from .reference_compiler import STYLE_PROMPTS
from .state_13 import part_views
from .view_catalog_13 import NATURAL_SURFACE

HEAD_SIX_PANELS = (
    ('face_front', 'upper-left', 'a front-facing portrait'),
    ('face_right', 'upper-center', 'a strict side profile with the face pointing toward the left edge of that panel'),
    ('face_3q_right', 'upper-right', 'a three-quarter portrait angled toward the left edge of that panel'),
    ('face_left', 'lower-left', 'a strict side profile with the face pointing toward the right edge of that panel'),
    ('face_3q_left', 'lower-center', 'a three-quarter portrait angled toward the right edge of that panel'),
    ('face_back', 'lower-right', 'the head viewed directly from behind'),
)
HEAD_SIX_FRAMING = ('Show the complete head and upper shoulders in every portrait at matching scale, '
                    'with a small white margin above the highest points of the silhouette and plain white space between the portraits.')


def _head_six_guide(layout, state, *, use_layout_image):
    rects = {}
    for index, (view, _, _) in enumerate(HEAD_SIX_PANELS):
        row, column = divmod(index, 3)
        rects[view] = [(column + .045) / 3, (row + .065) / 2, .91 / 3, .89 / 2]
    for panel in layout['panels']:
        panel['rect'] = rects[panel['id']]
    geometry = derive_guide_geometry(layout, state, compact=True)
    geometry['frame_width'] = 0
    if state['clothing_type'] == 'none':
        geometry['panel_fill'] = '#f2f2f2'
    elif use_layout_image:
        upper_views = {view for view, _, _ in HEAD_SIX_PANELS[:3]}
        for panel in geometry['panels']:
            if panel['id'] in upper_views and not panel['blank']:
                _, top, _, bottom = panel['bounds']
                x, y, width, height = panel['rect']
                inset = min(height - 1, round((bottom - top) * 0.18))
                new_height = height - inset
                new_width = max(1, round(width * new_height / height))
                panel['rect'] = [x + (width - new_width) // 2, y + inset, new_width, new_height]
    return geometry


def apply_head_six(result, state, defaults, *, style):
    layout = result['semantic_layout']
    guided = result['guide_enabled']
    result['guide_geometry'] = _head_six_guide(layout, state, use_layout_image=guided)
    refs = result['reference_plan']
    natural = state['clothing_type'] == 'none'
    style_instruction = STYLE_PROMPTS[style]
    design = 'character design' if style_instruction else 'character design and rendering style'
    lines = ['Create one character reference sheet from <Picture 1>.',
             f'Preserve the same {design} across all views.',
             'White background. Each requested view appears once.']
    if natural:
        lines.append(NATURAL_SURFACE)
    for ref in refs:
        if ref['role'] == 'layout':
            details = 'natural body surface, hair, markings' if natural else 'skin, hair, clothing'
            details += ', and colors' if style_instruction else ', colors, and illustration style'
            placement = (
                f"Use the six pale areas in {ref['tag']} to place the portraits in two rows and three columns."
                if natural else
                f"{ref['tag']} supplies the positions and viewing angles in two rows and three columns."
            )
            lines.append(f"Use <Picture 1> as the appearance reference for the character's {details} "
                         f"in all six portraits. {placement} {HEAD_SIX_FRAMING} "
                         "A narrow band of plain white space runs across the top of the sheet. "
                         "The entire outline of each upper-row head, including any horn tips, ears, "
                         "or headwear, fits below this space.")
        elif ref['role'] == 'same_character':
            lines.append(f"{ref['tag']} supplements the same character's appearance.")
    appearance = build_appearance_policy(state, refs)
    lines.extend(unused_reference_instructions(refs, appearance).values())
    if any(ref['source'].startswith('reference_image_') for ref in refs):
        lines.append('Follow selected settings first, then compatible part instructions, then dedicated references. '
                     'If dedicated references for the same role conflict, prefer the later input.')
    if not guided:
        lines.append(f'Arrange six portraits in two rows and three columns. {HEAD_SIX_FRAMING}')

    defaults = {**defaults, **{view: f'Show {description}.' for view, _, description in HEAD_SIX_PANELS}}
    overrides = state.get('view_prompts', {})
    view_text = {}
    for view, position, _ in HEAD_SIX_PANELS:
        extras = [f"Use {ref['tag']} for {ROLE_NAMES[ref['role']]}." for ref in appearance
                  if any(view in views for views in ref['parts'].values())]
        extras += [value for part, value in state['part_prompts'].items()
                   if value and view in part_views(state, part)]
        text = ' '.join([overrides.get(view, defaults[view]), *extras]).strip()
        view_text[view] = text
        if view in overrides:
            lines.append(f"The {position} panel. {text or 'One reserved view area.'}")
        else:
            lines.append(f"In the {position} panel, show {text.removeprefix('Show ')}")
    if style_instruction:
        lines.append(style_instruction)
    panels = sorted(layout['panels'], key=lambda panel: tuple(panel['rect'][:2]))
    records = [f"{panel['id']}: {view_text[panel['id']]}" for panel in panels]
    result.update(prompt='\n'.join(lines), default_view_prompts=defaults, view_prompts=records)
    return result
