"""Shared Reference13 compile entry; only ON derives guide geometry."""
from .compiler import DEFAULT_MAX_RESOLUTION, EXPERIMENTAL_PIXEL_THRESHOLD, StateValidationError
from .guide_13 import derive_guide_geometry, tighten_guide_layout, fit_auto_body_height, _contained_size
from .layout_13 import compute_semantic_layout
from .off_compiler_13 import compile_extended_prompt, compile_off_prompt_13
from .reference_compiler import STYLE_PROMPTS
from .state_13 import parse_reference13_state, serialize_reference13_state
from .multi_reference_compiler import ROLE_INSTRUCTIONS
from .appearance_policy_13 import build_appearance_policy
EXTRA_INPUTS = ('reference_image_1', 'reference_image_2', 'reference_image_3')


def compile_reference13_state(state_json, *, use_layout_image=False, style='none', max_resolution=DEFAULT_MAX_RESOLUTION,
                              reference_presence=None, optimize_outfit=False):
    if type(use_layout_image) is not bool:
        raise StateValidationError('use_layout_image must be boolean.', 'invalid_request')
    if type(style) is not str or style not in STYLE_PROMPTS:
        raise StateValidationError('Unknown rendering style.', 'invalid_style')
    if reference_presence is None:
        reference_presence = {}
    if (type(reference_presence) is not dict or set(reference_presence) - set(EXTRA_INPUTS)
            or any(type(value) is not bool for value in reference_presence.values())):
        raise StateValidationError('Invalid reference presence.', 'invalid_request')
    state = parse_reference13_state(state_json, max_resolution=max_resolution)
    if optimize_outfit:
        state["clothing_mode"] = "garment"
    seven = {'face_front', 'face_left', 'body_front', 'body_left', 'body_back', 'hands', 'feet'}
    layout = compute_semantic_layout(state, max_resolution=max_resolution,
                                     separate_details=optimize_outfit and set(state['views']) == seven)
    if optimize_outfit:
        layout = tighten_guide_layout(layout)
        if state["size"]["mode"] == "auto":
            layout = fit_auto_body_height(layout, state["size"]["body_height"])
            if layout["canvas"][0] > max_resolution:
                raise StateValidationError("Output width exceeds the ComfyUI resolution limit.", "size_limit")
    geometry = derive_guide_geometry(layout, state, compact=optimize_outfit) if (use_layout_image or optimize_outfit) else None
    if optimize_outfit and geometry:
        for panel in geometry["panels"]:
            if panel["id"].startswith("clothing_"):
                panel.update(blank=False, source=panel["id"] + "_garment.png", crop=[0, 0, 320, 500])
                left, top, right, bottom = panel["bounds"]
                w, h = _contained_size((320, 500), (right-left-2, bottom-top-2))
                panel["rect"] = [left+(right-left-w)//2, top+(bottom-top-h)//2, w, h]
    # Fixed Core wires, with packed Picture numbering that skips absent images.
    # Keep this independent from the legacy four-wire plan used by older nodes.
    ordered = [('character_image', 'character', True), ('layout_image', 'layout', use_layout_image)]
    ordered += [(name, state.get('reference_roles', {}).get(name, 'same_character'), reference_presence.get(name, False)) for name in EXTRA_INPUTS]
    references = []
    for slot, (source, role, present) in enumerate(ordered):
        if present:
            number = len(references) + 1
            references.append({'source': source, 'role': role, 'picture_number': number,
                               'tag': f'<Picture {number}>', 'core_input': f'ref_images.ref_image_{slot}'})
    appearance_policy = build_appearance_policy(state, references)
    if not use_layout_image:
        prompt = compile_off_prompt_13(state, layout, style=style, appearance_policy=appearance_policy, optimize_outfit=optimize_outfit)
    else:
        prompt = compile_extended_prompt(state, layout, style=style, guide_geometry=geometry, appearance_policy=appearance_policy, optimize_outfit=optimize_outfit)
    eligible_sources = {item['source'] for item in appearance_policy}
    extras = [item for item in references if item['source'] in EXTRA_INPUTS]
    if extras:
        instructions = '\n'.join(
            (f"{item['tag']} has role {item['role']}, but no eligible part is visible in the selected views. Ignore it for appearance changes."
             if item['role'] != 'same_character' and item['source'] not in eligible_sources else
             f"{item['tag']} has role {item['role']}: {ROLE_INSTRUCTIONS[item['role']]} "
             'Apply only to relevant visible parts of the same character. Explicit part instructions and appearance choices take precedence, then dedicated references, then same-character supplements and Picture 1. '
             'Do not transfer source identity, pose, background or layout outside the assigned role. '
             'If dedicated references for the same role conflict, the later connected reference takes precedence. '
             if item['role'] != 'same_character' else
            (f"{item['tag']} supplements the source outfit in <Picture 1>. "
             'Use it for garment construction, materials, colors, patterns and unseen garment surfaces. '
             'Explicit clothing choices and part directives take precedence. Keep <Picture 1> as the baseline where references conflict.'
             if optimize_outfit and set(state['views']).issubset(('clothing_front', 'clothing_back')) else
             f"{item['tag']} is an additional reference of <Subject 1>, the same person as <Picture 1>. "
             'Use it to supplement consistent identity and unseen appearance details. '
             'Do not introduce another person, transfer its pose, background or layout, or override '
             'explicit clothing, hand, footwear or part instructions. '
             'Keep <Picture 1> as the baseline where references conflict.')) for item in extras)
        marker = '\n\nsummary:'
        if marker in prompt:
            prompt = prompt.replace(marker, '\n' + instructions + marker, 1)
        else:
            prompt += '\nAdditional character references:\n' + instructions + '\n'
    width, height = layout['canvas']
    return {'state_json': serialize_reference13_state(state), 'state': state,
            'width': width, 'height': height, 'semantic_layout': layout, 'layout': layout,
            'prompt': prompt, 'guide_enabled': use_layout_image, 'guide_geometry': geometry,
            'reference_plan': references, 'reference_numbering_provisional': True,
            'pixel_count': width*height, 'megapixels': width*height/1_000_000,
            'experimental': width*height > EXPERIMENTAL_PIXEL_THRESHOLD, 'max_resolution': max_resolution}
