"""Deterministic panel packing and artwork placement; plain CPU metadata only."""
from itertools import product
import math

FAMILIES = (
    ('face_front', 'face_left', 'face_right', 'face_3q_left', 'face_3q_right', 'face_back'),
    ('body_front', 'body_left', 'body_back'),
    ('clothing_front', 'clothing_back'),
    ('hands', 'feet'),
)
PROFILES = {view: shape for group, shape in zip(FAMILIES, ((70, 70), (55, 100), (55, 90), (60, 45))) for view in group}
ART_SIZES = {
    'face_front': (470, 560), 'face_left': (140, 205), 'face_right': (325, 487),
    'face_3q_left': (398, 490), 'face_3q_right': (406, 490), 'face_back': (461, 483),
    'body_front': (315, 597), 'body_left': (109, 588), 'body_back': (317, 580),
    'clothing_front': (329, 499), 'clothing_back': (334, 500),
    'hands': (445, 400), 'feet': (380, 340),
}
ART_CROPS = {
    'face_front': (0, 75, 470, 560), 'face_left': (1010, 35, 140, 205),
    'body_front': (514, 40, 315, 597), 'body_left': (1033, 48, 109, 588),
    'body_back': (71, 648, 317, 580), 'hands': (415, 755, 445, 400),
    'feet': (860, 820, 380, 340),
}
AUTO_SIZES = {
    'qwen': ((1024, 1024), (768, 1344), (768, 1344), (1184, 864)),
    'h3': ((768, 768), (768, 1344), (768, 1344), (1024, 768)),
}


def auto_view_size(view, body_height, model):
    group = next(i for i, family in enumerate(FAMILIES) if view in family)
    return tuple(max(32, ((size * body_height + 17920) // 35840) * 32)
                 for size in AUTO_SIZES[model][group])


def _balanced_rows(views, count):
    base, extra = divmod(len(views), count)
    rows, offset = [], 0
    for index in range(count):
        length = base + (index < extra)
        rows.append(tuple(views[offset:offset + length]))
        offset += length
    return tuple(rows)


def _candidates(views):
    candidates = {_balanced_rows(views, count) for count in range(1, len(views) + 1)}
    groups = [tuple(view for view in family if view in views) for family in FAMILIES]
    groups = [group for group in groups if group]
    for counts in product(*(range(1, len(group) + 1) for group in groups)):
        candidates.add(tuple(row for group, count in zip(groups, counts)
                             for row in _balanced_rows(group, count)))
    return sorted(candidates)


def _apportion(total, weights):
    remaining = total - len(weights)
    weight_sum = sum(weights)
    exact = [remaining * weight / weight_sum for weight in weights]
    values = [1 + math.floor(value) for value in exact]
    for index in sorted(range(len(weights)), key=lambda i: (-(exact[i] - math.floor(exact[i])), i))[:total - sum(values)]:
        values[index] += 1
    return values


def _pack(rows, width, height, margin, gap, transpose):
    axis_w, axis_h = (height, width) if transpose else (width, height)
    row_space = axis_h - 2 * margin - (len(rows) - 1) * gap
    if row_space < len(rows):
        return None
    sizes = {view: PROFILES[view][::-1] if transpose else PROFILES[view] for row in rows for view in row}
    ideal_heights = []
    for row in rows:
        available = axis_w - 2 * margin - (len(row) - 1) * gap
        if available < len(row):
            return None
        ideal_heights.append(available * max(sizes[view][1] for view in row) / sum(sizes[view][0] for view in row))
    heights = _apportion(row_space, ideal_heights)
    bounds, y = {}, margin
    for row, row_h in zip(rows, heights):
        available = axis_w - 2 * margin - (len(row) - 1) * gap
        widths = _apportion(available, [sizes[view][0] for view in row])
        x = margin
        for view, panel_w in zip(row, widths):
            bounds[view] = (y, x, row_h, panel_w) if transpose else (x, y, panel_w, row_h)
            x += panel_w + gap
        y += row_h + gap
    scales, occupied = [], 0.0
    for view, (_, _, w, h) in bounds.items():
        natural_w, natural_h = PROFILES[view]
        scale = min(w / natural_w, h / natural_h)
        scales.append(scale)
        occupied += natural_w * natural_h * scale * scale
    mixed = sum(len({next(i for i, group in enumerate(FAMILIES) if view in group) for view in row}) - 1 for row in rows)
    score = (round(min(scales), 8), round(occupied / (width * height), 8), -mixed, -len(rows), -int(transpose))
    return score, bounds


def artwork_placements(bounds):
    inner = {}
    for view, (x, y, w, h) in bounds.items():
        inset = min(max(1, math.floor(min(w, h) * .03 + .5)), (min(w, h) - 1) // 2)
        inner[view] = (x + inset, y + inset, w - 2 * inset, h - 2 * inset)
    body_groups = {}
    for view in FAMILIES[1]:
        if view in bounds:
            _, y, _, h = bounds[view]
            body_groups.setdefault((y, h), []).append(view)
    body_heights = {}
    for views in body_groups.values():
        common = min(min(inner[view][3], math.floor(inner[view][2] * ART_SIZES[view][1] / ART_SIZES[view][0])) for view in views)
        for view in views:
            body_heights[view] = max(1, common)
    result = {}
    for view, (x, y, w, h) in inner.items():
        source_w, source_h = ART_SIZES[view]
        if view in body_heights:
            art_h = body_heights[view]
            art_w = min(w, max(1, math.floor(art_h * source_w / source_h + .5)))
            top = y + h - art_h
        else:
            scale = min(w / source_w, h / source_h)
            art_w = min(w, max(1, math.floor(source_w * scale + .5)))
            art_h = min(h, max(1, math.floor(source_h * scale + .5)))
            top = y + (h - art_h) // 2
        spec = {'rect': [x + (w - art_w) // 2, top, art_w, art_h]}
        if view in ART_CROPS:
            spec['crop'] = list(ART_CROPS[view])
        result[view] = spec
    return result


def compute_adaptive_layout(views, width, height):
    views = tuple(views)
    short = min(width, height)
    margin = max(1, math.floor(short * .02 + .5))
    gap = max(1, math.floor(short * .01 + .5))
    candidates = []
    for rows in _candidates(views):
        for transpose in (False, True):
            candidate = _pack(rows, width, height, margin, gap, transpose)
            if candidate is not None:
                candidates.append(candidate)
    largest_minimum = max(item[0][0] for item in candidates)
    eligible = [item for item in candidates if item[0][0] >= largest_minimum * .9]
    best = max(eligible, key=lambda item: (item[0][2], item[0][1], item[0][0], *item[0][3:]))
    _, bounds = best
    panels = [{'id': view, 'rect': [round(x / width, 6), round(y / height, 6), round(w / width, 6), round(h / height, 6)]}
              for view in views for x, y, w, h in (bounds[view],)]
    return {'canvas': [width, height], 'panels': panels, 'feet_y': None,
            'layout_version': 'adaptive-1', 'artwork': artwork_placements(bounds)}
