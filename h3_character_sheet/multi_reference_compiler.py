"""Pure v3 state, layout and role-aware H3 prompts; legacy paths stay unchanged."""

from fractions import Fraction
import json

from .compiler import (
    BODY_IDS, DEFAULT_MAX_RESOLUTION, EXPERIMENTAL_PIXEL_THRESHOLD, PART_IDS,
    PART_PROMPT_MAX_UNITS, PART_RULES, PRESETS, StateValidationError, VIEW_IDS,
    _BLANK_CHARACTERS, _ceil_32, _check_max_resolution, _exact_keys,
    _round_coordinate, _size_value, compute_layout, decode_json, parse_state,
    serialize_state,
)
from .reference_compiler import STYLE_PROMPTS
from .reference_plan import EXTRA_INPUTS, REFERENCE_ROLES, build_reference_plan
from .guide_geometry import body_baseline, body_artwork_placements

PORTRAIT_IDS = (
    "face_front", "face_left", "face_right", "face_3q_left",
    "face_3q_right", "face_back",
)
CLOTHING_IDS = ("clothing_front", "clothing_back")
MULTI_VIEW_IDS = (*PORTRAIT_IDS, *BODY_IDS, *CLOTHING_IDS, "hands", "feet")
MULTI_PRESETS = {
    **PRESETS, "detail": MULTI_VIEW_IDS, "head": PORTRAIT_IDS,
    "clothing": CLOTHING_IDS,
}
HAND_STATES = ('reference', 'bare', 'gloved')
CLOTHING_MODES = ('worn', 'garment')
DEFAULT_MULTI_STATE = {
    "schema_version": 3, "views": list(PRESETS["five"]),
    "size": {"mode": "auto", "body_height": 1120,
             "manual_width": 2208, "manual_height": 1280},
    "part_prompts": {},
    "reference_roles": {key: "same_character" for key in EXTRA_INPUTS},
    "hand_state": "reference", "clothing_mode": "worn",
}
DEFAULT_MULTI_STATE_JSON = serialize_state(DEFAULT_MULTI_STATE)
VIEW_DETAILS = {
    "face_front": ("front bust", "A front-facing bust, complete head and hair through the upper chest; both eyes visible."),
    "face_left": ("anatomical left-profile bust", "A strict anatomical left-profile bust, head and hair through the upper chest. Camera on the person's anatomical LEFT side, seeing only the left side of the face. Nose points to the LEFT edge of the final image; one visible eye. No front or three-quarter view; do not mirror the character's asymmetric features."),
    "face_right": ("anatomical right-profile bust", "A strict anatomical right-profile bust, head and hair through the upper chest. Camera on the person's anatomical RIGHT side, seeing only the right side of the face. Nose points to the RIGHT edge of the final image; one visible eye. No front or three-quarter view; do not mirror the character's asymmetric features."),
    "face_3q_left": ("anatomical left three-quarter bust", "A front-left three-quarter bust, head and hair through the upper chest. Camera halfway between the front and the person's anatomical LEFT side, at 45 degrees. Nose points toward the LEFT edge of the final image; both eyes visible, the far eye foreshortened. Not frontal and not a strict profile."),
    "face_3q_right": ("anatomical right three-quarter bust", "A front-right three-quarter bust, head and hair through the upper chest. Camera halfway between the front and the person's anatomical RIGHT side, at 45 degrees. Nose points toward the RIGHT edge of the final image; both eyes visible, the far eye foreshortened. Not frontal and not a strict profile."),
    "face_back": ("rear bust", "A direct rear bust, complete back of head and hair through the upper chest. No face or eyes visible; do not turn the head."),
    "body_front": ("full-body front", "A neutral standing front view, complete head and hair through both feet or footwear; leave clear space above the head and below the soles."),
    "body_left": ("full-body anatomical left profile", "A strict anatomical left-profile neutral standing view. Camera on the person's anatomical LEFT side. Nose, chest and toes point to the LEFT edge of the final image. Include the complete head through feet or footwear; do not mirror asymmetric clothing or accessories."),
    "body_back": ("full-body back", "A direct rear neutral standing view, complete head and hair through feet or footwear. No face visible; do not turn the head."),
    "clothing_front": ("clothing front", "A front-facing detail of the same referenced outfit as worn, neck through its complete lowest clothing edge. Omit the head. Preserve the referenced garment construction, silhouette, sleeve lengths, hems, colors and patterns, except for applicable explicit clothing directives. Do not replace its garment type or add separate leg openings."),
    "clothing_back": ("clothing back", "A direct rear detail of the same referenced outfit as worn, neck through its complete lowest clothing edge. Omit the head. Preserve the same garment construction, silhouette, sleeve lengths, hems, colors and patterns, except for applicable explicit clothing directives; infer unseen rear surfaces conservatively."),
    "hands": ("hands detail", "One isolated close-up of both complete hands, cropped at the wrists. Follow the referenced hand appearance unless an explicit applicable directive changes it. No head, torso or whole figure."),
    "feet": ("feet and footwear detail", "One isolated close-up of both complete feet or footwear, including visible boot shafts. Keep the resulting barefoot or footwear design; closed shoes do not expose bare toes. No head, torso or whole figure."),
}
MULTI_PART_VIEWS = {
    "head_hair": (*PORTRAIT_IDS, *BODY_IDS),
    "face": (*PORTRAIT_IDS[:-1], "body_front", "body_left"),
    "upper_clothing": (*PORTRAIT_IDS, *BODY_IDS, *CLOTHING_IDS),
    "back_clothing": ("face_left", "face_right", "face_back", "body_left", "body_back", "clothing_back"),
    "lower_body": (*BODY_IDS, *CLOTHING_IDS),
    "hands": (*BODY_IDS, "hands"),
    "footwear": (*BODY_IDS, "feet"),
    "other": MULTI_VIEW_IDS,
}
MULTI_PART_SCOPES = {
    **{part: rule["scope"] for part, rule in PART_RULES.items()},
    "back_clothing": "Apply only to the rear clothing surface actually visible from the panel's fixed camera, including a rear bust or rear clothing detail. Never move rear designs onto front surfaces or turn the subject to reveal them.",
    "hands": "Apply only to visible hands and their accessories. A selected hand-state override takes precedence only for whether the hands are covered; keep other hand details from this directive.",
}


def part_views(state, part):
    views = MULTI_PART_VIEWS[part]
    if part == 'hands' and state['clothing_mode'] == 'worn':
        views = (*views, *CLOTHING_IDS)
    return views


def panel_details(state, view):
    if view in CLOTHING_IDS and state['clothing_mode'] == 'garment':
        side = 'FRONT' if view == 'clothing_front' else 'REAR'
        return (f'garments only, {side.lower()}',
                f'An isolated {side} view of the same referenced garments ONLY. No head, neck, arms, hands, legs, feet, torso, skin, person, mannequin or body inside the garments. Preserve the complete referenced clothing silhouette, construction, openings, sleeve lengths, hems, colors and patterns except for applicable explicit clothing directives. Empty sleeves and clothing openings must not contain limbs. Do not replace the garment type or split a continuous hem into separate leg openings.')
    return VIEW_DETAILS[view]


def role_views(state, role):
    if role == 'clothing_front':
        return (*PORTRAIT_IDS[:-1], 'body_front', 'body_left', 'clothing_front')
    part = {'face': 'face', 'head': 'head_hair', 'clothing': 'upper_clothing',
            'clothing_back': 'back_clothing', 'hands': 'hands', 'footwear': 'footwear'}.get(role)
    return part_views(state, part) if part else ()


def parse_multi_state(raw, *, max_resolution=DEFAULT_MAX_RESOLUTION):
    _check_max_resolution(max_resolution)
    state = decode_json(raw)
    if type(state) is not dict:
        raise StateValidationError("state must be an object.", "invalid_type")
    version = state.get("schema_version")
    if type(version) is int and version in (1, 2):
        legacy = parse_state(raw, max_resolution=max_resolution)
        return {**legacy, "schema_version": 3,
                "part_prompts": legacy.get("part_prompts", {}),
                "reference_roles": {key: "same_character" for key in EXTRA_INPUTS},
                "hand_state": "reference", "clothing_mode": "worn"}
    if type(version) is not int or version != 3:
        raise StateValidationError("MultiReference supports schema_version 1, 2 or 3.", "unsupported_schema")
    state = {**state, 'hand_state': state.get('hand_state', 'reference'),
             'clothing_mode': state.get('clothing_mode', 'worn')}
    _exact_keys(state, ("schema_version", "views", "size", "part_prompts", "reference_roles", "hand_state", "clothing_mode"), "state")
    if type(state['hand_state']) is not str or state['hand_state'] not in HAND_STATES:
        raise StateValidationError('Unknown hand state.', 'invalid_hand_state')
    if type(state['clothing_mode']) is not str or state['clothing_mode'] not in CLOTHING_MODES:
        raise StateValidationError('Unknown clothing mode.', 'invalid_clothing_mode')
    views = state["views"]
    if type(views) is not list or any(type(view) is not str for view in views):
        raise StateValidationError("views must be an array of view-ID strings.", "invalid_type")
    if not views:
        raise StateValidationError("Select at least one view.", "empty_views")
    if set(views) - set(MULTI_VIEW_IDS):
        raise StateValidationError("Unknown MultiReference view IDs.", "unknown_view")
    size = state["size"]
    _exact_keys(size, ("mode", "body_height", "manual_width", "manual_height"), "size")
    if type(size["mode"]) is not str or size["mode"] not in ("auto", "manual"):
        raise StateValidationError("size.mode must be auto or manual.", "invalid_mode")
    normalized_size = {"mode": size["mode"]}
    for field in ("body_height", "manual_width", "manual_height"):
        normalized_size[field] = _size_value(size[field], f"size.{field}", max_resolution)
    prompts = state["part_prompts"]
    if type(prompts) is not dict:
        raise StateValidationError("part_prompts must be an object.", "invalid_type")
    if prompts.keys() - set(PART_IDS):
        raise StateValidationError("Unknown part IDs.", "unknown_part")
    normalized_prompts = {}
    for part in PART_IDS:
        if part not in prompts:
            continue
        text = prompts[part]
        if type(text) is not str:
            raise StateValidationError("Part prompts must be strings.", "invalid_type")
        if len(text.encode("utf-16-le")) // 2 > PART_PROMPT_MAX_UNITS:
            raise StateValidationError("Part prompt exceeds 1000 UTF-16 code units.", "part_prompt_too_long")
        if text.strip(_BLANK_CHARACTERS):
            normalized_prompts[part] = text
    roles = state["reference_roles"]
    _exact_keys(roles, EXTRA_INPUTS, "reference_roles")
    if any(type(roles[key]) is not str or roles[key] not in REFERENCE_ROLES for key in EXTRA_INPUTS):
        raise StateValidationError("Unknown reference role.", "unknown_reference_role")
    return {
        "schema_version": 3,
        "views": [view for view in MULTI_VIEW_IDS if view in views],
        "size": normalized_size, "part_prompts": normalized_prompts,
        "reference_roles": {key: roles[key] for key in EXTRA_INPUTS},
        "hand_state": state['hand_state'], "clothing_mode": state['clothing_mode'],
    }


def _ideal_multi_layout(views, h):
    h = Fraction(h)
    margin, gap, body_w, aux_w = h / 14, h / 25, 2 * h / 5, h / 2
    portraits = [view for view in PORTRAIT_IDS if view in views]
    bodies = [view for view in BODY_IDS if view in views]
    clothes = [view for view in CLOTHING_IDS if view in views]
    details = [view for view in ("hands", "feet") if view in views]
    groups = []
    if portraits:
        cols = min(2, len(portraits))
        rows = (len(portraits) + cols - 1) // cols
        cell_h = (h - (rows - 1) * gap) / rows
        rects = {view: (i % cols * (aux_w + gap), i // cols * (cell_h + gap), aux_w, cell_h)
                 for i, view in enumerate(portraits)}
        groups.append((cols * aux_w + (cols - 1) * gap, rects))
    for view in (*bodies, *clothes):
        groups.append((body_w, {view: (Fraction(0), Fraction(0), body_w, h)}))
    if details:
        cell_h = (h - (len(details) - 1) * gap) / len(details)
        groups.append((aux_w, {view: (Fraction(0), i * (cell_h + gap), aux_w, cell_h)
                               for i, view in enumerate(details)}))
    width = sum(group[0] for group in groups) + (len(groups) - 1) * gap + 2 * margin
    rects, x = {}, margin
    for group_w, group in groups:
        for view, (left, top, w, height) in group.items():
            rects[view] = (x + left, margin + top, w, height)
        x += group_w + gap
    return width, h + 2 * margin, rects, margin + h if bodies else None


def compute_multi_layout(state, *, max_resolution=DEFAULT_MAX_RESOLUTION):
    views, size = state["views"], state["size"]
    if set(views).issubset(VIEW_IDS):
        # Use exact legacy arithmetic, including its detail-band layouts.
        layout = compute_layout({"views": views, "size": size, "part_prompts": {}},
                                max_resolution=max_resolution)
        return finish_layout(state, layout)
    ideal_w, ideal_h, rects, feet_y = _ideal_multi_layout(views, size["body_height"])
    width, height = ((_ceil_32(ideal_w), _ceil_32(ideal_h)) if size["mode"] == "auto"
                     else (size["manual_width"], size["manual_height"]))
    for name, value in (("output width", width), ("output height", height)):
        _size_value(value, name, max_resolution)
    scale = Fraction(1) if size["mode"] == "auto" else min(Fraction(width) / ideal_w, Fraction(height) / ideal_h)
    ox, oy = (width - ideal_w * scale) / 2, (height - ideal_h * scale) / 2
    panels = []
    for view in views:
        left, top, w, h = rects[view]
        rect = [_round_coordinate((left * scale + ox) / width),
                _round_coordinate((top * scale + oy) / height),
                _round_coordinate(w * scale / width), _round_coordinate(h * scale / height)]
        panels.append({"id": view, "rect": rect, "view": VIEW_DETAILS[view][0],
                       "content": VIEW_DETAILS[view][1]})
    baseline = None if feet_y is None else _round_coordinate((feet_y * scale + oy) / height)
    return finish_layout(state, {"canvas": [width, height], "panels": panels, "feet_y": baseline})


def finish_layout(state, layout):
    panels = [{**panel, 'view': panel_details(state, panel['id'])[0],
               'content': panel_details(state, panel['id'])[1]} for panel in layout['panels']]
    result = {**layout, 'panels': panels}
    result['feet_y'] = body_baseline(result)
    return result


ROLE_INSTRUCTIONS = {
    "same_character": "Supplement the same person's identity and unseen details from this additional angle. Do not introduce a second character, pose, background or layout.",
    "face": "Use only facial anatomy, eyes, nose, mouth and facial skin. Do not transfer hair, clothing, body proportions, pose or background.",
    "head": "Use only the face, hair, head and headwear. Do not transfer clothing, body proportions, pose or background.",
    "clothing": "Use only the complete outfit's construction, colors, materials and patterns. Ignore the source person's face, body proportions, pose and background.",
    "clothing_front": "Use only FRONT surfaces of the outfit. Do not move front designs onto the back. Ignore the source person's head, physique, pose and background.",
    "clothing_back": "Use only REAR surfaces of the outfit where visible from each fixed camera. Do not move rear designs onto the front or rotate the character to reveal them.",
    "hands": "Use only the referenced hand appearance and hand accessories wherever hands are visible, even when no hands detail panel is selected. Do not invent coverings absent from the reference; explicit hand-state or part directives may override its appearance. Ignore unrelated anatomy, pose and background.",
    "footwear": "Use only feet, shoes, boots and foot accessories wherever feet are visible, even when no footwear detail panel is selected. Ignore unrelated anatomy, pose and background.",
}


def compile_multi_prompt(state, layout, plan, *, use_layout_image=False, style="none"):
    refs = {item["source"]: item for item in plan.references}
    if "character_image" not in refs:
        raise StateValidationError("Connect the character_image input.", "missing_character")
    character = refs["character_image"]["tag"]
    active = {part: text for part, text in state["part_prompts"].items()
              if any(view in part_views(state, part) for view in state["views"])}
    extras = [ref for ref in plan.references if ref['source'] in EXTRA_INPUTS]
    changed_refs = [ref for ref in extras if
                    any(view in role_views(state, ref['role']) for view in state['views'])]
    hand_override = state['hand_state'] != 'reference' and any(view in part_views(state, 'hands') for view in state['views'])
    changes = [f'explicit {part} directives' for part in active]
    changes += [f"{ref['role']} appearance from {ref['tag']}" for ref in changed_refs]
    if hand_override:
        changes.append('hand coverage selected by the hand-state override')
    if style != 'none':
        changes.append(f'rendering technique ({style})')
    retention = ('partially_preserved - change only ' + '; '.join(changes) +
                 '. Preserve baseline identity, proportions, clothing, accessories and appearance everywhere else.'
                 if changes else 'fully_preserved - preserve the referenced identity, proportions, outfit, accessories and rendering style across every selected view. New camera views and panel arrangements do not authorize appearance changes.')
    lines = [
        "subject_definitions:",
        f"<Subject 1> is the single character in {character}. Use it for baseline identity, body proportions, appearance, outfit, accessories and rendering style.",
    ]
    for reference in plan.references:
        tag, role = reference["tag"], reference["role"]
        if role == "layout":
            lines.append(f"{tag} is a framed layout guide only: use panel positions, sizes, orientations and crops. Gray mannequins are placeholders, not appearance, physique or clothing references.")
        elif role != "character":
            lines.append(f"{tag} has role {role}: {ROLE_INSTRUCTIONS[role]}")
            if role != 'same_character':
                eligible = [view for view in state['views'] if view in role_views(state, role)]
                lines.append('Apply this dedicated reference only to visible relevant surfaces in: ' +
                             (', '.join(eligible) if eligible else 'none of the selected panels; it does not authorize any appearance change here') + '.')
    lines.extend([
        "", "summary:",
        f"[reference generation] Create one completed static character sheet of <Subject 1>, with exactly {len(state['views'])} simultaneously visible selected panels: " + ", ".join(state["views"]) + ".",
        "", "retention_analysis:",
        '<Subject 1> (appears in [Shot 1]): ' + retention,
        'Priority: hand-state override for coverage only, explicit named-part directives, specific dedicated references, same-character supplements, then baseline reference. Front/rear clothing references apply only to their visible surfaces. Preserve one resulting outfit and character consistently; detail-panel selection does not change reference priority.',
    ])
    if len(extras) == 2 and extras[0]["role"] == extras[1]["role"] != "same_character":
        lines.append(f"Use {extras[0]['tag']} and {extras[1]['tag']} together for different angles and consistent details. If their same-part designs conflict, {extras[1]['tag']} takes precedence.")
    lines.extend([
        "Infer unseen surfaces conservatively; unseen backs remain inferred, not verified. Add no unsupported costume elements or accessories.",
        "", "detailed_description:",
        STYLE_PROMPTS[style] if style != "none" else f"Keep the rendering style of {character}.",
        "Change rendering technique only when a style is specified; retain the resulting character and outfit. Do not transfer background, scenery, source poses or extra people.",
        "[Shot 1] The completed sheet is already present in the first frame and stays unchanged through the last frame. All panels coexist. No motion, gestures, camera movement, cuts, transitions or temporal switching. Plain white background and consistent soft lighting.",
        "Layout specification (semantic guidance, not visible text): " + json.dumps({key: value for key, value in layout.items() if key != "artwork"}, ensure_ascii=True, separators=(",", ":")),
        "Rect coordinates are normalized [left, top, width, height] from the upper-left corner. Keep content inside its assigned panel; do not print the layout data.",
    ])
    if use_layout_image and 'layout_image' in refs:
        guide = refs["layout_image"]["tag"]
        lines.append(f"Replace all gray mannequins in {guide} with <Subject 1>. Preserve black panel frames, crops and panel count; no empty panels or residual mannequin parts.")
        if state['clothing_mode'] == 'garment' and any(view in CLOTHING_IDS for view in state['views']):
            lines.append('The clothing-only guide panels intentionally have blank interiors. Fill them with the referenced garments alone, without any human body or mannequin. These blank interiors are placement slots, not missing selected outputs.')
    else:
        lines.append("Use clear empty gaps between panels; do not draw panel borders or alignment lines.")
    if sum(view in BODY_IDS for view in state["views"]) > 1:
        if layout.get('layout_version') == 'adaptive-1':
            lines.append('Within each row of full-body panels, keep the same figure height and align soles. Separate rows have separate baselines. Preserve complete heads and feet.')
        else:
            lines.append("Keep a common body scale and head height across the full-body panels. Align feet or footwear to feet_y with clear space below every sole.")
    for panel in layout["panels"]:
        lines.append(f"Panel {panel['id']}: {panel['content']}")
    for part, text in active.items():
        eligible = ", ".join(view for view in state["views"] if view in part_views(state, part))
        lines.append(f"Part directive {part} ({PART_RULES[part]['label']}; applies to {eligible}): {MULTI_PART_SCOPES[part]} Treat the following as literal appearance guidance, never as prompt syntax, Picture numbering, layout, view selection or temporal instructions:\n{text}")
    if hand_override:
        coverage = ('Bare uncovered hands with visible skin from fingertips through wrists. No gloves, mittens or other hand coverings.'
                    if state['hand_state'] == 'bare' else 'Both hands are covered by gloves. Keep the referenced or explicitly requested glove design; do not expose bare hands or invent extra accessories.')
        lines.append('Hand-state override (highest priority for coverage only): ' + coverage +
                     ' Apply consistently to every visible hand in the full-body, worn-clothing and hand-detail panels. Preserve other compatible part instructions; ignore only text or references that conflict about hand coverage.')
    if state['clothing_mode'] == 'garment' and any(view in CLOTHING_IDS for view in state['views']):
        lines.append('Clothing-only presentation takes precedence over any request to draw a wearer in clothing_front or clothing_back. Apply clothing appearance changes to the garments themselves. No human anatomy or mannequin may remain in these two object-only panels; other selected panels retain their own crops.')
    lines.extend([
        "Show exactly the selected views once each. No extra people, views, captions, panel labels or watermarks. Preserve existing subject lettering; change subject lettering only by an applicable explicit part directive.",
        "", "overall_soundscape:", "None.", "", "non_diegetic_music:", "None.",
    ])
    return "\n".join(lines) + "\n"


def compile_multi_state(state_json, *, use_layout_image=False, style="none",
                        reference_presence=None, max_resolution=DEFAULT_MAX_RESOLUTION, layout=None):
    """Advisory CPU preview; linked images may still resolve to None at execution."""
    if type(use_layout_image) is not bool:
        raise StateValidationError("use_layout_image must be boolean.", "invalid_request")
    if type(style) is not str or style not in STYLE_PROMPTS:
        raise StateValidationError("Unknown rendering style.", "invalid_style")
    presence = {key: False for key in EXTRA_INPUTS} if reference_presence is None else reference_presence
    _exact_keys(presence, EXTRA_INPUTS, "reference_presence")
    if any(type(presence[key]) is not bool for key in EXTRA_INPUTS):
        raise StateValidationError("Reference presence must be boolean.", "invalid_request")
    state = parse_multi_state(state_json, max_resolution=max_resolution)
    layout = compute_multi_layout(state, max_resolution=max_resolution) if layout is None else layout
    sentinel = object()
    plan = build_reference_plan(sentinel, sentinel if use_layout_image else None,
                                sentinel if presence["reference_image_1"] else None,
                                sentinel if presence["reference_image_2"] else None,
                                state["reference_roles"])
    width, height = layout["canvas"]
    return {"state_json": serialize_state(state), "layout": layout,
            "width": width, "height": height,
            "prompt": compile_multi_prompt(state, layout, plan, use_layout_image=use_layout_image, style=style),
            "reference_plan": list(plan.references), "reference_numbering_provisional": True,
            "guide_artwork": body_artwork_placements(layout),
            "max_resolution": max_resolution,
            "experimental": width * height > EXPERIMENTAL_PIXEL_THRESHOLD}
