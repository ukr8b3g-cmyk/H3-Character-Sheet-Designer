"""Semantic panel allocation, independent of PNGs and guide drawing geometry."""
from fractions import Fraction

from .compiler import DEFAULT_MAX_RESOLUTION, _ceil_32, _round_coordinate, _size_value, compute_layout
from .state_13 import legacy_state
from .view_catalog_13 import BODY_IDS, CLOTHING_IDS, LEGACY_VIEW_IDS, PORTRAIT_IDS, VIEW_DETAILS


def compute_semantic_layout(state, *, max_resolution=DEFAULT_MAX_RESOLUTION):
    views, size = state['views'], state['size']
    if set(views).issubset(LEGACY_VIEW_IDS):
        return compute_layout(legacy_state(state), max_resolution=max_resolution)
    h = Fraction(size['body_height'])
    margin, gap, body_w, aux_w = h / 14, h / 25, 2 * h / 5, h / 2
    portraits = [view for view in PORTRAIT_IDS if view in views]
    bodies = [view for view in BODY_IDS if view in views]
    clothes = [view for view in CLOTHING_IDS if view in views]
    details = [view for view in ('hands', 'feet') if view in views]
    groups = []
    if portraits:
        cols = min(2, len(portraits))
        rows = (len(portraits) + cols - 1) // cols
        cell_h = (h - (rows - 1) * gap) / rows
        groups.append((cols * aux_w + (cols - 1) * gap,
                       {view: (i % cols * (aux_w + gap), i // cols * (cell_h + gap), aux_w, cell_h)
                        for i, view in enumerate(portraits)}))
    for view in (*bodies, *clothes):
        groups.append((body_w, {view: (Fraction(0), Fraction(0), body_w, h)}))
    if details:
        cell_h = (h - (len(details) - 1) * gap) / len(details)
        groups.append((aux_w, {view: (Fraction(0), i * (cell_h + gap), aux_w, cell_h)
                              for i, view in enumerate(details)}))
    ideal_w = sum(w for w, _ in groups) + (len(groups) - 1) * gap + 2 * margin
    ideal_h = h + 2 * margin
    width, height = ((_ceil_32(ideal_w), _ceil_32(ideal_h)) if size['mode'] == 'auto'
                     else (size['manual_width'], size['manual_height']))
    _size_value(width, 'output width', max_resolution)
    _size_value(height, 'output height', max_resolution)
    scale = Fraction(1) if size['mode'] == 'auto' else min(Fraction(width) / ideal_w, Fraction(height) / ideal_h)
    ox, oy = (width - ideal_w * scale) / 2, (height - ideal_h * scale) / 2
    rects, x = {}, margin
    for group_w, group in groups:
        for view, (left, top, w, ph) in group.items():
            rects[view] = [_round_coordinate((x + left) * scale / width + ox / width),
                           _round_coordinate((margin + top) * scale / height + oy / height),
                           _round_coordinate(w * scale / width), _round_coordinate(ph * scale / height)]
        x += group_w + gap
    return {'canvas': [width, height],
            'panels': [{'id': view, 'rect': rects[view], 'view': VIEW_DETAILS[view][0],
                        'content': VIEW_DETAILS[view][1]} for view in views],
            'feet_y': _round_coordinate(((margin + h) * scale + oy) / height) if bodies else None}
