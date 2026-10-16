"""Pixel geometry shared by the Multi Reference guide and its UI preview."""
import math

BODY_CROPS = {
    'body_front': (514, 40, 315, 597),
    'body_left': (1033, 48, 109, 588),
    'body_back': (71, 648, 317, 580),
}
MIRRORED_VIEWS = ('face_left', 'face_right', 'face_3q_left', 'face_3q_right', 'body_left')


def frame_width(layout):
    return max(1, (min(layout['canvas']) + 128) // 256)


def panel_bounds(layout, panel):
    width, height = layout['canvas']
    x, y, w, h = panel['rect']
    return (round(x * width), round(y * height),
            round((x + w) * width), round((y + h) * height))


def body_inset(layout, bounds):
    return min(frame_width(layout) + 1,
               max(0, (min(right - left for left, _, right, _ in bounds) - 1) // 2),
               max(0, (min(bottom - top for _, top, _, bottom in bounds) - 1) // 2))


def body_baseline(layout):
    if layout.get('layout_version') == 'adaptive-1':
        return None
    bounds = [panel_bounds(layout, panel) for panel in layout['panels'] if panel['id'] in BODY_CROPS]
    return (min(bottom for _, _, _, bottom in bounds) - body_inset(layout, bounds) - 1) / layout['canvas'][1] if bounds else None


def body_artwork_placements(layout):
    if layout.get('layout_version') == 'adaptive-1':
        return layout['artwork']
    bodies = [panel for panel in layout['panels'] if panel['id'] in BODY_CROPS]
    if not bodies:
        return {}
    bounds = {panel['id']: panel_bounds(layout, panel) for panel in bodies}
    inset = body_inset(layout, list(bounds.values()))
    baseline = round(layout['feet_y'] * layout['canvas'][1])
    widest_ratio = max(w / h for _, _, w, h in BODY_CROPS.values())
    common_height = min(
        min(baseline + 1 - (top + inset) for _, top, _, _ in bounds.values()),
        math.floor(min(right - left - 2 * inset for left, _, right, _ in bounds.values()) / widest_ratio),
    )
    common_height = max(1, common_height)
    result = {}
    for view, (left, top, right, bottom) in bounds.items():
        crop = BODY_CROPS[view]
        width = max(1, round(common_height * crop[2] / crop[3]))
        result[view] = {'crop': list(crop), 'rect': [left + (right - left - width) // 2,
                       baseline + 1 - common_height, width, common_height]}
    return result
