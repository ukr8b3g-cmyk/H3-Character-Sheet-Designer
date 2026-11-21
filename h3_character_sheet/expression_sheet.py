"""Shared six-expression layout and per-portrait prompts for the two current designers."""
from .appearance_policy_13 import ROLE_NAMES, build_appearance_policy, unused_reference_instructions
from .head_six import HEAD_SIX_FRAMING, HEAD_SIX_PANELS, _head_six_guide
from .reference_compiler import STYLE_PROMPTS
from .view_catalog_13 import EXPRESSION_CONTENT_ALIASES, EXPRESSION_DESCRIPTIONS


def apply_expression_sheet(result, style):
    state = result['state']
    layout = result['semantic_layout']
    geometry = _head_six_guide(layout, {**state, 'clothing_type': 'none'}, use_layout_image=result['guide_enabled'])
    positions = {view: index for index, (view, _, _) in enumerate(HEAD_SIX_PANELS)}
    for panels in (layout['panels'], geometry['panels']):
        panels.sort(key=lambda panel: positions[panel['id']])
        for panel, view in zip(panels, EXPRESSION_DESCRIPTIONS):
            panel['id'] = view
            if panels is layout['panels']:
                content = EXPRESSION_CONTENT_ALIASES.get(view, view.removeprefix('expression_'))
                panel.update(view='front-facing portrait', content=content)
    style_instruction = STYLE_PROMPTS[style]
    lines = [
        'Create one expression sheet of the same character from <Picture 1>. '
        'Show exactly six front-facing portraits in three columns and two rows.',
        HEAD_SIX_FRAMING,
        'Keep the character’s identity, colors, eye colors where visible, markings, and design details consistent. '
        'Keep the same head orientation, crop, and scale. Express each emotion using the features the character has.',
    ]
    front = {**state, 'views': ['face_front']}
    refs = result['reference_plan']
    policy = build_appearance_policy(front, refs)
    for ref in refs:
        if ref['role'] == 'layout':
            lines.append(f"Use the six pale areas in {ref['tag']} for portrait placement.")
        elif ref['role'] == 'same_character':
            lines.append(f"{ref['tag']} supplements compatible details of the character in <Picture 1>.")
    lines.extend(f"Use {ref['tag']} for {ROLE_NAMES[ref['role']]}." for ref in policy)
    lines.extend(unused_reference_instructions(refs, policy).values())
    records = []
    defaults = {}
    overrides = state.get('view_prompts', {})
    for (_, position, _), (view, description) in zip(HEAD_SIX_PANELS, EXPRESSION_DESCRIPTIONS.items()):
        defaults[view] = f'Show {description}.'
        text = overrides.get(view, defaults[view])
        records.append(f'The {position} portrait. {text}'.rstrip())
    lines.extend(records)
    lines.append('Plain white background and white gaps between portraits. Omit text, symbols, and borders.')
    lines.append(style_instruction or 'Match the rendering style of <Picture 1>.')
    result.update(prompt='\n'.join(lines), guide_geometry=geometry, default_view_prompts=defaults, view_prompts=records)
    return result
