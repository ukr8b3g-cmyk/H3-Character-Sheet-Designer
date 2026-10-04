"""Deterministic, standard-library-only H3 character-sheet compiler.

All layout arithmetic is rational. Only the final normalized coordinates are
rounded, using round-half-up to six places. This module has no ComfyUI imports,
network requests, model execution, or filesystem side effects.
"""

from __future__ import annotations

import json
from fractions import Fraction
from typing import Any

STATE_MAX_BYTES = 16 * 1024
DEFAULT_MAX_RESOLUTION = 16384  # Standalone compiler default; node uses Core at runtime.
EXPERIMENTAL_PIXEL_THRESHOLD = 1_032_192
VIEW_IDS = ("face_front", "body_front", "body_left", "body_back", "hands", "feet")
BODY_IDS = ("body_front", "body_left", "body_back")
AUXILIARY_IDS = ("face_front", "hands", "feet")
PRESETS = {
    "basic": VIEW_IDS[:4],
    "detail": VIEW_IDS,
    "turnaround": BODY_IDS,
    "single": ("body_front",),
}
DEFAULT_STATE = {
    "schema_version": 1,
    "views": list(PRESETS["basic"]),
    "size": {
        "mode": "auto",
        "body_height": 1120,
        "manual_width": 2240,
        "manual_height": 1280,
    },
}
DEFAULT_STATE_JSON = json.dumps(DEFAULT_STATE, separators=(",", ":"))

VIEW_DETAILS = {
    "face_front": (
        "front portrait",
        "Show <Subject 1> directly from the front, from the face through the chest; retain the complete hairstyle and visible upper clothing.",
    ),
    "body_front": (
        "full-body front",
        "Show <Subject 1> directly from the front in a neutral standing pose, entirely visible from the top of the head to the soles of the footwear.",
    ),
    "body_left": (
        "full-body anatomical left profile",
        "Show <Subject 1> in a strict left-profile neutral standing pose, camera looking directly at the subject's anatomical left side, entirely visible from the top of the head to the soles of the footwear.",
    ),
    "body_back": (
        "full-body back",
        "Show <Subject 1> directly from behind in a neutral standing pose, entirely visible from the top of the head to the soles of the footwear.",
    ),
    "hands": (
        "left and right hand details",
        "Show close details of both of <Subject 1>'s hands with their reference-consistent accessories; keep any gloves from the reference rather than replacing them with bare hands.",
    ),
    "feet": (
        "left and right foot and footwear details",
        "Show close details of both of <Subject 1>'s feet and footwear; preserve any reference shoes, boots, and boot shafts rather than replacing them with bare feet.",
    ),
}


class StateValidationError(ValueError):
    """An invalid saved state; callers must retain the original input unchanged."""

    def __init__(self, message: str, code: str = "invalid_state") -> None:
        super().__init__(message)
        self.code = code


def _object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise StateValidationError(f"Duplicate JSON key: {key}.", "duplicate_key")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise StateValidationError(f"Non-finite JSON number is not allowed: {value}.", "non_finite")


def decode_json(text: str, *, byte_limit: int = STATE_MAX_BYTES) -> Any:
    """Parse bounded strict JSON, rejecting duplicate keys and non-finite numbers."""
    if not isinstance(text, str):
        raise StateValidationError("state_json must be a JSON string.", "invalid_type")
    if len(text) > byte_limit:
        raise StateValidationError(f"JSON exceeds the {byte_limit}-byte limit.", "state_too_large")
    try:
        size = len(text.encode("utf-8"))
    except UnicodeEncodeError as exc:
        raise StateValidationError("JSON must be valid UTF-8.", "invalid_utf8") from exc
    if size > byte_limit:
        raise StateValidationError(f"JSON exceeds the {byte_limit}-byte limit.", "state_too_large")
    try:
        return json.loads(text, object_pairs_hook=_object_pairs, parse_constant=_reject_constant)
    except StateValidationError:
        raise
    except (ValueError, RecursionError) as exc:
        raise StateValidationError("Invalid JSON: a valid finite JSON document is required.", "invalid_json") from exc


def _exact_keys(value: Any, keys: tuple[str, ...], path: str) -> None:
    if type(value) is not dict:
        raise StateValidationError(f"{path} must be an object.", "invalid_type")
    missing = set(keys) - value.keys()
    unknown = value.keys() - set(keys)
    if missing:
        raise StateValidationError(f"{path} is missing required keys: {', '.join(sorted(missing))}.", "missing_key")
    if unknown:
        raise StateValidationError(f"{path} contains unknown keys: {', '.join(sorted(unknown))}.", "unknown_key")


def _check_max_resolution(max_resolution: int) -> None:
    if type(max_resolution) is not int or max_resolution < 32:
        raise ValueError("max_resolution must be an integer of at least 32.")


def _size_value(value: Any, field: str, max_resolution: int) -> int:
    if type(value) is not int:
        raise StateValidationError(f"{field} must be an integer (not a boolean, decimal, or numeric string).", "invalid_integer")
    if value < 32 or value % 32 != 0:
        raise StateValidationError(f"{field} must be at least 32 and a multiple of 32.", "invalid_size")
    if value > max_resolution:
        raise StateValidationError(f"{field} exceeds Core MAX_RESOLUTION ({max_resolution}).", "size_limit")
    return value


def parse_state(state_json: str, *, max_resolution: int = DEFAULT_MAX_RESOLUTION) -> dict[str, Any]:
    """Validate all fields and return a fresh, canonically ordered semantic state."""
    _check_max_resolution(max_resolution)
    state = decode_json(state_json)
    _exact_keys(state, ("schema_version", "views", "size"), "state")
    version = state["schema_version"]
    if type(version) is not int or version != 1:
        raise StateValidationError("schema_version must be the integer 1; no automatic migration is performed.", "unsupported_schema")
    views = state["views"]
    if type(views) is not list or any(type(view) is not str for view in views):
        raise StateValidationError("views must be an array of view-ID strings.", "invalid_type")
    if not views:
        raise StateValidationError("Select at least one view.", "empty_views")
    unknown = set(views) - set(VIEW_IDS)
    if unknown:
        raise StateValidationError(f"Unknown view IDs: {', '.join(sorted(unknown))}.", "unknown_view")
    size = state["size"]
    _exact_keys(size, ("mode", "body_height", "manual_width", "manual_height"), "size")
    if type(size["mode"]) is not str or size["mode"] not in ("auto", "manual"):
        raise StateValidationError("size.mode must be auto or manual.", "invalid_mode")
    normalized_size = {"mode": size["mode"]}
    for key in ("body_height", "manual_width", "manual_height"):
        normalized_size[key] = _size_value(size[key], f"size.{key}", max_resolution)
    return {"schema_version": 1, "views": [view for view in VIEW_IDS if view in views], "size": normalized_size}


def serialize_state(state: dict[str, Any]) -> str:
    """Serialize a state already returned by parse_state in the schema key order."""
    return json.dumps(state, ensure_ascii=True, separators=(",", ":"), allow_nan=False)


def _ceil_32(value: Fraction) -> int:
    return ((value.numerator + 32 * value.denominator - 1) // (32 * value.denominator)) * 32


def _round_coordinate(value: Fraction) -> float:
    # Integer arithmetic gives exact round-half-up, independent of decimal context.
    numerator = value.numerator * 1_000_000
    rounded = (2 * numerator + value.denominator) // (2 * value.denominator)
    return rounded / 1_000_000 if rounded else 0.0


def _ideal_layout(views: list[str], h: int) -> tuple[Fraction, Fraction, dict[str, tuple[Fraction, ...]], Fraction | None]:
    height = Fraction(h)
    margin, gap, body_width, aux_width = height / 14, height / 25, 2 * height / 5, height / 2
    auxiliaries = [view for view in AUXILIARY_IDS if view in views]
    bodies = [view for view in BODY_IDS if view in views]
    columns = len(bodies) + bool(auxiliaries)
    width = len(bodies) * body_width + bool(auxiliaries) * aux_width + (columns - 1) * gap + 2 * margin
    canvas_height = height + 2 * margin
    rects: dict[str, tuple[Fraction, ...]] = {}
    x, y = margin, margin
    if auxiliaries:
        if "face_front" in auxiliaries and len(auxiliaries) > 1:
            portrait_height = 31 * height / 50
            rects["face_front"] = (x, y, aux_width, portrait_height)
            detail_y = y + portrait_height + gap
            detail_height = height - portrait_height - gap
            details = [view for view in ("hands", "feet") if view in auxiliaries]
            detail_width = (aux_width - gap) / 2 if len(details) == 2 else aux_width
            for index, view in enumerate(details):
                rects[view] = (x + index * (detail_width + gap), detail_y, detail_width, detail_height)
        elif len(auxiliaries) == 2:  # hands + feet, without portrait
            detail_height = (height - gap) / 2
            for index, view in enumerate(auxiliaries):
                rects[view] = (x, y + index * (detail_height + gap), aux_width, detail_height)
        else:
            rects[auxiliaries[0]] = (x, y, aux_width, height)
        x += aux_width + gap
    for view in bodies:
        rects[view] = (x, y, body_width, height)
        x += body_width + gap
    return width, canvas_height, rects, margin + height if bodies else None


def compute_layout(state: dict[str, Any], *, max_resolution: int = DEFAULT_MAX_RESOLUTION) -> dict[str, Any]:
    """Lay out a validated state; inputs must come from parse_state."""
    size = state["size"]
    ideal_width, ideal_height, raw_rects, feet_y = _ideal_layout(state["views"], size["body_height"])
    if size["mode"] == "auto":
        width, height = _ceil_32(ideal_width), _ceil_32(ideal_height)
        scale = Fraction(1)
    else:
        width, height = size["manual_width"], size["manual_height"]
        scale = min(Fraction(width) / ideal_width, Fraction(height) / ideal_height)
    for axis, value in (("output width", width), ("output height", height)):
        _size_value(value, axis, max_resolution)
    offset_x, offset_y = (width - ideal_width * scale) / 2, (height - ideal_height * scale) / 2
    panels = []
    for view in state["views"]:
        left, top, panel_width, panel_height = raw_rects[view]
        rect = [
            _round_coordinate((left * scale + offset_x) / width),
            _round_coordinate((top * scale + offset_y) / height),
            _round_coordinate(panel_width * scale / width),
            _round_coordinate(panel_height * scale / height),
        ]
        label, content = VIEW_DETAILS[view]
        panels.append({"id": view, "rect": rect, "view": label, "content": content})
    baseline = None if feet_y is None else _round_coordinate((feet_y * scale + offset_y) / height)
    return {"canvas": [width, height], "panels": panels, "feet_y": baseline}


def _coordinate_text(value: float) -> str:
    return f"{value:.6f}"  # Fixed six-place notation, never scientific notation.


def layout_json(layout: dict[str, Any]) -> str:
    """Stable compact JSON with fixed six-decimal normalized coordinate tokens."""
    panels = []
    for panel in layout["panels"]:
        panels.append(
            '{"id":' + json.dumps(panel["id"])
            + ',"rect":[' + ",".join(_coordinate_text(value) for value in panel["rect"]) + "]"
            + ',"view":' + json.dumps(panel["view"], ensure_ascii=True)
            + ',"content":' + json.dumps(panel["content"], ensure_ascii=True) + "}"
        )
    baseline = "null" if layout["feet_y"] is None else _coordinate_text(layout["feet_y"])
    return '{"canvas":[' + ",".join(str(value) for value in layout["canvas"]) + '],"panels":[' + ",".join(panels) + '],"feet_y":' + baseline + "}"


def _layout_prose(state: dict[str, Any], layout: dict[str, Any]) -> list[str]:
    views = state["views"]
    auxiliaries = [view for view in AUXILIARY_IDS if view in views]
    bodies = [view for view in BODY_IDS if view in views]
    lines = []
    if auxiliaries:
        lines.append("Place the selected portrait and/or detail views in the leftmost auxiliary column.")
        if "face_front" in auxiliaries and len(auxiliaries) > 1:
            lines.append("Place the front portrait above the detail band, with clear empty space between them.")
            if "hands" in auxiliaries and "feet" in auxiliaries:
                lines.append("In that lower detail band, place the hands on the left and the feet/footwear on the right, separated by empty space.")
        elif len(auxiliaries) == 2:
            lines.append("Stack the hand details above the feet/footwear details, with clear empty space between them.")
        else:
            lines.append("The single selected auxiliary view uses the full height of its column.")
    if bodies:
        ordered = ", then ".join(VIEW_DETAILS[view][0] for view in bodies)
        lines.append(f"Arrange the full-body columns from left to right as {ordered}" + (", to the right of the auxiliary column." if auxiliaries else "."))
        lines.append("Keep a common subject scale and identical panel top and bottom limits across the full-body views, with the footwear soles aligned to the shared feet_y baseline. Leave room for the complete head and footwear without cropping.")
    for panel in layout["panels"]:
        coordinates = ", ".join(_coordinate_text(value) for value in panel["rect"])
        lines.append(f"Panel {panel['id']} occupies [left, top, width, height] = [{coordinates}]. {panel['content']}")
    return lines


def compile_prompt(state: dict[str, Any], layout: dict[str, Any]) -> str:
    """The version-1 English template: LF-only, fixed sections, one trailing LF."""
    labels = "; ".join(VIEW_DETAILS[view][0] for view in state["views"])
    lines = [
        "subject_definitions:",
        "<Subject 1> is the person in <Picture 1>, which is the identity, appearance, clothing, accessories, and visual-style reference for every selected view.",
        "",
        "summary:",
        f"[reference generation] Create one completed, static character sheet of <Subject 1> showing only these selected views simultaneously: {labels}. Every panel depicts the same person from <Picture 1>.",
        "",
        "retention_analysis:",
        "<Subject 1> (appears in [Shot 1]): fully_preserved - retain the reference person's face, hair, physique, skin appearance, visual style, clothing, and accessories consistently wherever visible in the selected crops. Preserve reference gloves and footwear; do not substitute bare hands or bare feet for them. Infer any unseen surfaces conservatively, without inventing new costume elements or unsupported details.",
        "",
        "detailed_description:",
        "Keep the rendering style of <Picture 1>, with consistent soft lighting and a plain, unobtrusive background across the sheet.",
        "[Shot 1] The finished sheet is already present in the first frame and remains completely unchanged through the last frame. The selected views coexist as separate, clearly spaced depictions of <Subject 1>; they are alternate views of one identity, not additional people. Keep all content within its assigned region, with uncluttered outer margins and empty gaps.",
        "Layout specification (semantic guidance, not visible text): " + layout_json(layout),
        "Read rect coordinates as normalized [left, top, width, height], measured from the upper-left corner of the canvas. The canvas dimensions are in pixels. Use the specified placement and proportions without drawing the layout data into the image.",
    ]
    lines.extend(_layout_prose(state, layout))
    lines.extend([
        "Show exactly the selected views and preserve the same identity, colors, materials, and reference-consistent asymmetries throughout. Do not add unselected views or extra people. Do not add captions, labels, lettering, watermarks, panel borders, or drawn alignment lines. Keep the subject and camera still: no gestures, movement, camera motion, cuts, transitions, or temporal switching between views. The sheet is silent.",
        "",
        "overall_soundscape:",
        "None. No speech, vocalization, ambience, or sound effects.",
        "",
        "non_diegetic_music:",
        "None.",
    ])
    return "\n".join(lines) + "\n"


def compile_state(state_json: str, *, max_resolution: int = DEFAULT_MAX_RESOLUTION) -> dict[str, Any]:
    """Compile API/GUI state through the same validation, layout, and prompt path."""
    state = parse_state(state_json, max_resolution=max_resolution)
    layout = compute_layout(state, max_resolution=max_resolution)
    width, height = layout["canvas"]
    pixels = width * height
    return {
        "state_json": serialize_state(state),
        "width": width,
        "height": height,
        "layout": layout,
        "prompt": compile_prompt(state, layout),
        "pixel_count": pixels,
        "megapixels": pixels / 1_000_000,
        "experimental": pixels > EXPERIMENTAL_PIXEL_THRESHOLD,
        "max_resolution": max_resolution,
    }
