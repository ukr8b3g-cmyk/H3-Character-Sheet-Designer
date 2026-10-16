"""Guide-only geometry. Nothing here feeds the semantic layout back upstream."""
from PIL import Image, ImageDraw, ImageOps, UnidentifiedImageError

from .compiler import StateValidationError
from .guide_geometry import BODY_CROPS, body_artwork_placements, body_baseline
from .layout_image import ATLAS_CROPS, ATLAS_PATH, render_layout_image
from .view_catalog_13 import CLOTHING_IDS, LEGACY_VIEW_IDS

EXTRA_SIZES = {'face_right': (325, 487), 'face_3q_left': (398, 490),
               'face_3q_right': (406, 490), 'face_back': (461, 483),
               'clothing_front': (329, 499), 'clothing_back': (334, 500)}


def _contained_size(source, bounds):
    width, height = source
    limit_w, limit_h = bounds
    if width / height > limit_w / limit_h:
        return max(1, limit_w), max(1, round(height * limit_w / width))
    return max(1, round(width * limit_h / height)), max(1, limit_h)


def derive_guide_geometry(layout, state):
    width, height = layout['canvas']
    legacy = set(state['views']).issubset(LEGACY_VIEW_IDS)
    guide_layout = {**layout, 'feet_y': body_baseline(layout)}
    bodies = {} if legacy else body_artwork_placements(guide_layout)
    panels = []
    for panel in layout['panels']:
        view = panel['id']
        x, y, w, h = panel['rect']
        left, top = round(x * width), round(y * height)
        right, bottom = round((x + w) * width), round((y + h) * height)
        blank = view in CLOTHING_IDS and state['clothing_mode'] == 'garment'
        crop = list(bodies[view]['crop']) if view in bodies else list(ATLAS_CROPS.get(view, (0, 0, *EXTRA_SIZES.get(view, (1, 1)))))
        source = view + '.png' if view in EXTRA_SIZES else 'mannequin-atlas.png'
        if view in bodies:
            rect = list(bodies[view]['rect'])
        else:
            aw, ah = _contained_size(crop[2:], (max(1, right-left), max(1, bottom-top)))
            rect = [left + (right-left-aw)//2, top + (bottom-top-ah)//2, aw, ah]
        panels.append({'id': view, 'bounds': [left, top, right, bottom], 'source': source,
                       'crop': crop, 'rect': rect, 'mirror': False, 'blank': blank})
    return {'canvas': [width, height], 'frame_width': max(1, (min(width, height)+128)//256),
            'legacy': legacy, 'panels': panels}


def render_reference13_guide(geometry, layout):
    if geometry['legacy']:
        try:
            return render_layout_image(layout)
        except (OSError, UnidentifiedImageError) as exc:
            raise StateValidationError(f'Cannot read guide asset: {ATLAS_PATH}', 'guide_asset') from exc
    canvas = Image.new('RGB', tuple(geometry['canvas']), 'white')
    draw = ImageDraw.Draw(canvas)
    for panel in geometry['panels']:
        if not panel['blank']:
            path = ATLAS_PATH.parent / panel['source']
            try:
                with Image.open(path) as source:
                    artwork = source.convert('RGBA')
            except (OSError, UnidentifiedImageError) as exc:
                raise StateValidationError(f'Cannot read guide asset: {path}', 'guide_asset') from exc
            x, y, w, h = panel['crop']
            artwork = artwork.crop((x, y, x+w, y+h))
            if panel['mirror']:
                artwork = ImageOps.mirror(artwork)
            x, y, w, h = panel['rect']
            artwork = artwork.resize((w, h), Image.Resampling.LANCZOS)
            canvas.paste(artwork, (x, y), artwork)
        left, top, right, bottom = panel['bounds']
        draw.rectangle((left, top, max(left, right-1), max(top, bottom-1)), outline='black', width=geometry['frame_width'])
    return canvas
