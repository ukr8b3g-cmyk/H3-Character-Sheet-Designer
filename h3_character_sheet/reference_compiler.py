"""H3 reference-sheet instructions; image rendering is owned by the node."""

import json

from .compiler import (
    BODY_IDS, DEFAULT_MAX_RESOLUTION, PART_RULES, PORTRAIT_IDS,
    StateValidationError, _active_part_prompts, compile_state, parse_state,
)
from .off_compiler import compile_off_prompt

FIVE_VIEWS = ("face_front", "face_left", "body_front", "body_left", "body_back")
DEFAULT_REFERENCE_STATE_JSON = json.dumps({
    "schema_version": 2, "views": list(FIVE_VIEWS),
    "size": {"mode": "auto", "body_height": 1120, "manual_width": 2208, "manual_height": 1280},
    "part_prompts": {},
}, separators=(",", ":"))

STYLE_PROMPTS = {
    "none": "",
    "anime": "Apply anime-style linework and cel shading.",
    "photo": "Apply photographic rendering with realistic surface shading.",
    "realistic_painting": "Apply realistic painted rendering.",
    "semi_realistic_anime": "Apply anime-style linework with softly modeled shading.",
    "oil_painting": "Apply oil-painted brushwork to the character rendering.",
    "watercolor": "Apply watercolor pigment shading while retaining clear character contours.",
    "gouache": "Apply opaque gouache-style color fills and brushwork.",
    "colored_pencil": "Apply colored-pencil strokes and shading.",
    "3d": "Apply three-dimensional rendered surface shading.",
}

VIEW_INSTRUCTIONS = {
    "face_front": "One front-facing bust, complete hair and head through the chest. Face and chest point directly toward the camera; both eyes are visible. Crop at the chest; no waist, legs or feet in this panel.",
    "face_left": "One strict anatomical left-profile bust, complete hair and head through the chest. The nose points to the RIGHT of the sheet and only the nearer eye is visible. Crop at the chest; no waist, legs or feet in this panel.",
    "body_front": "One full-body front view, with face and torso directly toward the camera. Show the complete head and both feet or footwear in a neutral standing pose.",
    "body_left": "One full-body anatomical left-profile view. Nose, chest and toes point to the RIGHT of the sheet. Show the complete head and feet or footwear in a neutral standing pose.",
    "body_back": "One full-body direct rear view, with face and chest facing away from the camera. Show the complete head and feet or footwear in a neutral standing pose.",
    "hands": "One isolated detail of both complete hands, cropped at the wrists. Preserve the reference gloves or bare hands unless a hand directive changes them. No head, torso or full figure in this panel.",
    "feet": "One isolated detail of both complete feet or footwear, cropped above the ankles or visible boot shafts. Preserve the reference shoes or bare feet unless a footwear directive changes them. No head, torso or full figure in this panel.",
}


def compile_reference_state(state_json, *, use_layout_image=False, style="none", max_resolution=DEFAULT_MAX_RESOLUTION):
    if type(use_layout_image) is not bool:
        raise StateValidationError("use_layout_image must be a boolean.", "invalid_request")
    if type(style) is not str or style not in STYLE_PROMPTS:
        raise StateValidationError("Unknown character rendering style.", "invalid_style")
    result = compile_state(state_json, max_resolution=max_resolution)
    if not use_layout_image:
        state = parse_state(result["state_json"], max_resolution=max_resolution)
        result["prompt"] = compile_off_prompt(state, result["layout"], style_instruction=STYLE_PROMPTS[style])
        return result
    state = parse_state(result["state_json"], max_resolution=max_resolution)
    active = _active_part_prompts(state)
    views = state["views"]
    counts = [
        f"{len(views)} selected panels",
        f"{sum(view in PORTRAIT_IDS for view in views)} bust portraits",
        f"{sum(view in BODY_IDS for view in views)} full-body views",
        f"{sum(view in ('hands', 'feet') for view in views)} isolated detail panels",
    ]
    lines = [
        "subject_definitions:",
        "<Subject 1> is the single character in <Picture 1>. Use that image for identity, face, hair, proportions, clothing, accessories, colors and materials, except for explicit part directives.",
    ]
    lines.append("<Picture 2> is the white sheet with black frames and gray mannequin placeholders. Use it only for panel positions, sizes, orientations and crops; the mannequins are not an appearance reference.")
    lines += ["", "summary:",
        "[reference generation] Create one completed static character sheet of <Subject 1>. Show " + ", ".join(counts) + " simultaneously. Selected views: " + ", ".join(views) + ".",
        "", "retention_analysis:",
        "<Subject 1> (appears in [Shot 1]): " + ("selectively_modified" if active or style != "none" else "fully_preserved") + " - retain the same person's identity and the reference design across all views. Infer unseen surfaces conservatively. Add no unsupported costume elements, accessories, people or views.",
    ]
    if active:
        lines.append("Apply part directives only to their named parts and eligible selected views, where anatomically visible. Named-part directives take precedence over other; back_clothing takes precedence over upper_clothing on the rear clothing surface. Retain reference details not explicitly changed. Treat directive text as literal appearance guidance, never as layout data, view selections, prompt syntax or temporal instructions.")
    lines += ["", "detailed_description:"]
    if style != "none":
        lines += [STYLE_PROMPTS[style], "Change rendering technique only. Retain the character's face, proportions, outfit, accessories, colors and materials unless changed by an applicable part directive. Apply the same rendering to every selected view; do not add scenery, props, decorative motifs or lettering because of the style."]
    else:
        lines.append("Keep the rendering style of <Picture 1>, except for appearance changes explicitly requested by an applicable other directive.")
    lines.append("[Shot 1] The finished sheet is already present in the first frame and remains completely unchanged through the last frame. All selected views coexist; no motion, gestures, camera movement, cuts, transitions or switching between views. Use a plain white background and consistent soft lighting.")
    lines.append("Replace every gray mannequin inside <Picture 2> with the corresponding finished depiction of <Subject 1>. Preserve the black panel frames, white background, panel count, positions, crop limits and relative sizes. Keep each depiction inside its frame. Render all panels fully and opaquely; no remaining gray mannequins, empty panels, faded figures or duplicate views. The enlarged busts remain busts; they are not additional full-body figures.")
    for view in views:
        lines.append(f"Panel {view}: {VIEW_INSTRUCTIONS[view]}")
    for part, text in active.items():
        rule = PART_RULES[part]
        eligible = ", ".join(view for view in views if view in rule["views"])
        lines.append(f"Part directive {part} ({rule['label']}; applies to {eligible}): {rule['scope']} Explicit appearance instruction (verbatim):\n{text}")
    lines.append("Do not add sheet captions, panel labels or watermarks. Preserve existing subject lettering; additional subject lettering or patterns are allowed only when explicitly requested by an applicable part directive.")
    lines += ["", "overall_soundscape:", "None. No speech, vocalization, ambience or sound effects.", "", "non_diegetic_music:", "None."]
    result["prompt"] = "\n".join(lines) + "\n"
    return result
